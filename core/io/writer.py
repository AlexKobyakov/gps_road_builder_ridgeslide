# -*- coding: utf-8 -*-
"""
Export of the road-network graph for GPS Road Builder.
Экспорт результата: GeoJSON и GraphML пишутся чистым Python (тестируется без
QGIS); SHP/GeoPackage — через QgsVectorFileWriter (в среде QGIS).

Координаты — географические (EPSG:4326): рёбра берут edge['coords_lonlat'],
узлы — graph.node_lonlat (если заполнен pipeline) либо метрические координаты.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import json

from . import features as feat_mod


def write_geojson(graph, path):
    """Записать рёбра графа как FeatureCollection (GeoJSON, EPSG:4326)."""
    feats = feat_mod.road_graph_features(graph)
    gj = feat_mod.features_to_geojson(feats)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(gj, fh, ensure_ascii=False, indent=1)
    return path


def _node_positions(graph):
    """Словарь id -> (x, y) для узлов: lon/lat, если доступно, иначе мировые."""
    lonlat = getattr(graph, 'node_lonlat', None)
    if lonlat:
        return {nid: lonlat[nid] for nid in graph.nodes if nid in lonlat}
    return dict(graph.nodes)


def write_graphml(graph, path):
    """Записать граф в GraphML (узлы с координатами, рёбра с freq/length)."""
    positions = _node_positions(graph)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="x" for="node" attr.name="x" attr.type="double"/>',
        '  <key id="y" for="node" attr.name="y" attr.type="double"/>',
        '  <key id="freq" for="edge" attr.name="frequency" attr.type="int"/>',
        '  <key id="len" for="edge" attr.name="length" attr.type="double"/>',
        '  <key id="rclass" for="edge" attr.name="road_class" attr.type="string"/>',
        '  <key id="recon" for="edge" attr.name="reconstructed" attr.type="int"/>',
        '  <key id="ndev" for="edge" attr.name="n_devices" attr.type="int"/>',
        '  <graph edgedefault="undirected">',
    ]
    for nid, (x, y) in positions.items():
        lines.append(
            '    <node id="n{0}"><data key="x">{1}</data>'
            '<data key="y">{2}</data></node>'.format(nid, x, y))
    for edge in graph.edges:
        u, v = edge['u'], edge['v']
        if u not in positions or v not in positions:
            continue
        freq = int(edge.get('frequency', 0))
        length = float(edge.get('length', 0.0))
        rclass = str(edge.get('road_class', ''))
        recon = int(edge.get('reconstructed', 0))
        ndev = int(edge.get('n_devices', 0))
        lines.append(
            '    <edge source="n{0}" target="n{1}">'
            '<data key="freq">{2}</data>'
            '<data key="len">{3}</data>'
            '<data key="rclass">{4}</data>'
            '<data key="recon">{5}</data>'
            '<data key="ndev">{6}</data></edge>'.format(
                u, v, freq, length, rclass, recon, ndev))
    lines.append('  </graph>')
    lines.append('</graphml>')
    # id узлов — целые, ключи фиксированы: спецсимволов нет, экранирование не нужно
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    return path


# --- Форматы через QGIS (SHP / GeoPackage / прочее OGR) ---

DRIVERS = {
    'shp': 'ESRI Shapefile',
    'gpkg': 'GPKG',
    'geojson': 'GeoJSON',
}


def save_vector_layer(layer, path, driver_key='gpkg'):
    """Сохранить QgsVectorLayer в файл через QgsVectorFileWriter.

    Работает только в среде QGIS. driver_key: 'shp' | 'gpkg' | 'geojson'.
    """
    from qgis.core import QgsVectorFileWriter, QgsProject, QgsCoordinateTransformContext

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = DRIVERS.get(driver_key, 'GPKG')
    try:
        context = QgsProject.instance().transformContext()
    except Exception:
        context = QgsCoordinateTransformContext()
    error = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, path, context, options)
    # writeAsVectorFormatV3 возвращает кортеж; первый элемент — код ошибки
    code = error[0] if isinstance(error, (tuple, list)) else error
    if code != QgsVectorFileWriter.NoError:
        raise RuntimeError('Vector export failed: {0}'.format(error))
    return path
