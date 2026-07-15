# -*- coding: utf-8 -*-
"""
Build a QGIS vector layer from the road graph.
Сборка слоя дорожной сети (LineString, EPSG:4326) из фич графа и стилизация
шириной линии по частоте (тёмнее/толще — популярнее).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import os

import numpy as np

from qgis.PyQt.QtCore import QVariant, Qt
from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsField, QgsProject,
    QgsLineSymbol, QgsSingleSymbolRenderer, QgsProperty, QgsSymbolLayer,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsWkbTypes
)

from ..core.io import features as feat_mod
from ..core.graph.to_graph import RoadGraph


def build_road_layer(graph, name='GPS Road Network', style_by_frequency=True):
    """Собрать memory-слой дорожной сети из графа (координаты в EPSG:4326)."""
    layer = QgsVectorLayer('LineString?crs=EPSG:4326', name, 'memory')
    provider = layer.dataProvider()
    provider.addAttributes([
        QgsField('id', QVariant.Int),
        QgsField('frequency', QVariant.Int),
        QgsField('length', QVariant.Double),
        QgsField('road_class', QVariant.String),
        QgsField('reconstructed', QVariant.Int),
        QgsField('n_devices', QVariant.Int),
    ])
    layer.updateFields()

    qfeatures = []
    for f in feat_mod.road_graph_features(graph):
        qf = QgsFeature()
        pts = [QgsPointXY(float(x), float(y)) for x, y in f['coords_lonlat']]
        qf.setGeometry(QgsGeometry.fromPolylineXY(pts))
        qf.setAttributes([f['id'], f['frequency'], round(f['length'], 3),
                          f.get('road_class', ''), f.get('reconstructed', 0),
                          f.get('n_devices', 0)])
        qfeatures.append(qf)
    provider.addFeatures(qfeatures)
    layer.updateExtents()

    if style_by_frequency:
        _apply_frequency_style(layer)
    return layer


def _apply_frequency_style(layer):
    """Ширина линии растёт с частотой прохождения (data-defined)."""
    symbol = QgsLineSymbol.createSimple({'color': '31,120,200', 'width': '0.4'})
    expr = 'coalesce(0.3 + 0.35 * sqrt(coalesce("frequency", 0)), 0.3)'
    symbol.symbolLayer(0).setDataDefinedProperty(
        QgsSymbolLayer.PropertyStrokeWidth,
        QgsProperty.fromExpression(expr))
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))


def add_to_project(layer):
    """Добавить слой в текущий проект QGIS."""
    QgsProject.instance().addMapLayer(layer)
    return layer


# --- Чтение слоёв для постобработки/AOI (§WS-Post/WS-AOI) ---

def _transform_to_4326(src_crs):
    """Трансформация из CRS слоя в EPSG:4326 (или None, если уже 4326)."""
    dst = QgsCoordinateReferenceSystem('EPSG:4326')
    if not src_crs.isValid() or src_crs == dst:
        return None
    return QgsCoordinateTransform(src_crs, dst, QgsProject.instance())


def graph_from_layer(layer):
    """Собрать граф (lon/lat) из линейного слоя: концы отрезков → узлы.

    Рёбра получают 'coords_lonlat' (EPSG:4326); узлы — координаты lon/lat.
    Совпадающие концы (с округлением) объединяются в один узел.
    """
    tr = _transform_to_4326(layer.crs())
    graph = RoadGraph()
    node_key = {}

    def node_id(x, y):
        k = (round(x, 7), round(y, 7))
        if k not in node_key:
            nid = len(node_key)
            node_key[k] = nid
            graph.nodes[nid] = (float(x), float(y))
        return node_key[k]

    for feat in layer.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue
        g = QgsGeometry(geom)
        if tr is not None:
            g.transform(tr)
        parts = g.asMultiPolyline()
        if not parts:
            line = g.asPolyline()
            parts = [line] if line else []
        for part in parts:
            if len(part) < 2:
                continue
            coords = np.array([(p.x(), p.y()) for p in part], dtype=float)
            u = node_id(coords[0, 0], coords[0, 1])
            v = node_id(coords[-1, 0], coords[-1, 1])
            graph.edges.append({
                'u': u, 'v': v, 'coords_lonlat': coords,
                'coords': coords.copy(), 'length': 0.0, 'frequency': 0})
    return graph


def polygon_rings_from_layer(layer):
    """Извлечь кольца полигонов (lon/lat, EPSG:4326) из полигонального слоя."""
    tr = _transform_to_4326(layer.crs())
    rings = []
    for feat in layer.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue
        g = QgsGeometry(geom)
        if tr is not None:
            g.transform(tr)
        polys = g.asMultiPolygon()
        if not polys:
            single = g.asPolygon()
            polys = [single] if single else []
        for poly in polys:
            for ring in poly:
                rings.append(np.array([(p.x(), p.y()) for p in ring],
                                      dtype=float))
    return rings


def polygon_rings_from_file(path):
    """Загрузить полигон AOI из файла (OGR) → список колец lon/lat."""
    layer = QgsVectorLayer(path, 'aoi', 'ogr')
    if not layer.isValid():
        raise ValueError('Invalid AOI layer: {0}'.format(path))
    return polygon_rings_from_layer(layer)


# --- Вход из векторных слоёв / файлов GPX/KML/SHP (§WS-Input, ADD3 #12) ---

def _attr_time_str(value):
    """Значение атрибута времени → строка для pandas (QDateTime/строка/дата)."""
    if value is None:
        return ''
    if hasattr(value, 'toString'):          # QDateTime
        try:
            return value.toString(Qt.ISODate)
        except Exception:
            return str(value)
    return str(value)


def df_from_layer(layer):
    """Нормализованный df (device/time/lat/lon) из векторного слоя.

    Точечный слой — каждая точка = запись; линейный — вершины линий (каждая линия
    = один «трек»/устройство). Координаты из геометрии (→ EPSG:4326); device/time
    авто-детектятся по именам полей (алиасы schema), иначе синтезируются. Требований
    к колонкам координат нет — их даёт геометрия.
    """
    from ..core.io import vector_input

    tr = _transform_to_4326(layer.crs())
    fields = [f.name() for f in layer.fields()]
    dev_field, time_field = vector_input.detect_device_time_fields(fields)
    is_point = layer.geometryType() == QgsWkbTypes.PointGeometry
    is_line = layer.geometryType() == QgsWkbTypes.LineGeometry
    use_time = is_point and time_field is not None   # время по точкам — только точки

    devices, lats, lons, times = [], [], [], []
    for feat in layer.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue
        g = QgsGeometry(geom)
        if tr is not None:
            g.transform(tr)
        if is_point:
            dev = feat[dev_field] if dev_field else 'points'
            pts = g.asMultiPoint() if g.isMultipart() else [g.asPoint()]
            for p in pts:
                devices.append(str(dev))
                lats.append(p.y())
                lons.append(p.x())
                if use_time:
                    times.append(_attr_time_str(feat[time_field]))
        elif is_line:
            parts = g.asMultiPolyline() if g.isMultipart() else [g.asPolyline()]
            for part in parts:
                for p in part:
                    devices.append('f{0}'.format(feat.id()))
                    lats.append(p.y())
                    lons.append(p.x())
        # полигоны игнорируем
    return vector_input.to_dataframe(
        devices, lats, lons, times=(times if use_time else None))


def df_from_file(path):
    """Загрузить GPX/KML/SHP (и др. OGR) как слой → нормализованный df.

    Для GPX берём подслой точек трека (`track_points`) — там есть время и trackfid.
    """
    ext = os.path.splitext(path)[1].lower()
    layer = None
    if ext == '.gpx':
        layer = QgsVectorLayer(
            path + '|layername=track_points', 'gpx_points', 'ogr')
    if layer is None or not layer.isValid():
        layer = QgsVectorLayer(path, os.path.basename(path), 'ogr')
    if not layer.isValid():
        raise ValueError('Invalid vector file: {0}'.format(path))
    return df_from_layer(layer)
