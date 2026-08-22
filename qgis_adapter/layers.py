# -*- coding: utf-8 -*-
"""Shared QGIS feature/layer adapters for GUI and Processing.

All graph and dataframe conversion that needs QGIS belongs here.  Callers that
run through Processing pass ``context.transformContext()``; GUI callers retain
the legacy project-context fallback.
"""

import os

import numpy as np

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeature,
    QgsField, QgsFields, QgsGeometry, QgsLineSymbol, QgsPointXY, QgsProject,
    QgsProperty, QgsSingleSymbolRenderer, QgsVectorLayer, QgsWkbTypes
)

from ..core.graph.to_graph import RoadGraph
from ..core.io import features as feat_mod
from ..qgis_compat import qgis_enum, qt_enum, qvariant_type, symbol_layer_property


OUTPUT_FIELD_NAMES = (
    'id', 'frequency', 'length', 'road_class', 'reconstructed', 'n_devices'
)


def road_graph_fields():
    """Return the stable Processing/GUI output schema."""
    fields = QgsFields()
    for name, kind in (
            ('id', 'Int'), ('frequency', 'Int'), ('length', 'Double'),
            ('road_class', 'String'), ('reconstructed', 'Int'),
            ('n_devices', 'Int')):
        fields.append(QgsField(name, qvariant_type(kind)))
    return fields


def _feature_attributes(record):
    return [record['id'], record['frequency'], round(record['length'], 3),
            record.get('road_class', ''), record.get('reconstructed', 0),
            record.get('n_devices', 0)]


def _feature_from_record(record, fields=None):
    feature = QgsFeature(fields) if fields is not None else QgsFeature()
    points = [QgsPointXY(float(x), float(y)) for x, y in record['coords_lonlat']]
    feature.setGeometry(QgsGeometry.fromPolylineXY(points))
    feature.setAttributes(_feature_attributes(record))
    return feature


def write_graph_to_sink(graph, sink, feedback=None):
    """Write a graph to a standard QGIS feature sink and return feature count."""
    fields = road_graph_fields()
    records = feat_mod.road_graph_features(graph)
    total = len(records)
    for index, record in enumerate(records):
        if feedback is not None and feedback.isCanceled():
            return index
        sink.addFeature(_feature_from_record(record, fields))
        if feedback is not None and total:
            feedback.setProgress(98.0 + 2.0 * (index + 1) / total)
    return total


def build_road_layer(graph, name='GPS Road Network', style_by_frequency=True):
    """Build an EPSG:4326 memory layer from a road graph (legacy GUI API)."""
    layer = QgsVectorLayer('LineString?crs=EPSG:4326', name, 'memory')
    provider = layer.dataProvider()
    fields = road_graph_fields()
    provider.addAttributes(list(fields))
    layer.updateFields()
    provider.addFeatures([
        _feature_from_record(record, layer.fields())
        for record in feat_mod.road_graph_features(graph)
    ])
    layer.updateExtents()
    if style_by_frequency:
        _apply_frequency_style(layer)
    return layer


def _apply_frequency_style(layer):
    """Apply the GUI's data-defined frequency style."""
    symbol = QgsLineSymbol.createSimple({'color': '31,120,200', 'width': '0.4'})
    expr = 'coalesce(0.3 + 0.35 * sqrt(coalesce("frequency", 0)), 0.3)'
    symbol.symbolLayer(0).setDataDefinedProperty(
        symbol_layer_property('PropertyStrokeWidth'),
        QgsProperty.fromExpression(expr))
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))


def add_to_project(layer):
    """Add a GUI result layer to the active project."""
    QgsProject.instance().addMapLayer(layer)
    return layer


def _source_crs(source):
    crs = getattr(source, 'sourceCrs', None)
    return crs() if callable(crs) else source.crs()


def _transform_to_4326(source, transform_context=None):
    """Return an EPSG:4326 transform, using explicit Processing context if set."""
    src_crs = _source_crs(source)
    dst = QgsCoordinateReferenceSystem('EPSG:4326')
    if not src_crs.isValid() or src_crs == dst:
        return None
    context = transform_context if transform_context is not None else QgsProject.instance()
    return QgsCoordinateTransform(src_crs, dst, context)


def graph_from_feature_source(source, transform_context=None):
    """Convert a line feature source into a lon/lat :class:`RoadGraph`."""
    tr = _transform_to_4326(source, transform_context)
    graph = RoadGraph()
    node_key = {}

    def node_id(x, y):
        key = (round(x, 7), round(y, 7))
        if key not in node_key:
            node_key[key] = len(node_key)
            graph.nodes[node_key[key]] = (float(x), float(y))
        return node_key[key]

    for feature in source.getFeatures():
        geometry = feature.geometry()
        if geometry is None or geometry.isEmpty():
            continue
        geometry = QgsGeometry(geometry)
        if tr is not None:
            geometry.transform(tr)
        parts = geometry.asMultiPolyline()
        if not parts:
            line = geometry.asPolyline()
            parts = [line] if line else []
        for part in parts:
            if len(part) < 2:
                continue
            coords = np.array([(point.x(), point.y()) for point in part], dtype=float)
            u = node_id(coords[0, 0], coords[0, 1])
            v = node_id(coords[-1, 0], coords[-1, 1])
            graph.edges.append({
                'u': u, 'v': v, 'coords_lonlat': coords,
                'coords': coords.copy(), 'length': 0.0, 'frequency': 0})
    return graph


def graph_from_layer(layer):
    """Backward-compatible alias for GUI callers."""
    return graph_from_feature_source(layer)


def polygon_rings_from_feature_source(source, transform_context=None):
    """Extract polygon rings in EPSG:4326 from a feature source."""
    tr = _transform_to_4326(source, transform_context)
    rings = []
    for feature in source.getFeatures():
        geometry = feature.geometry()
        if geometry is None or geometry.isEmpty():
            continue
        geometry = QgsGeometry(geometry)
        if tr is not None:
            geometry.transform(tr)
        polygons = geometry.asMultiPolygon()
        if not polygons:
            single = geometry.asPolygon()
            polygons = [single] if single else []
        for polygon in polygons:
            for ring in polygon:
                rings.append(np.array([(point.x(), point.y()) for point in ring], dtype=float))
    return rings


def polygon_rings_from_layer(layer):
    """Backward-compatible alias for GUI callers."""
    return polygon_rings_from_feature_source(layer)


def polygon_rings_from_file(path):
    """Load polygon rings from an OGR file for the GUI."""
    layer = QgsVectorLayer(path, 'aoi', 'ogr')
    if not layer.isValid():
        raise ValueError('Invalid AOI layer: {0}'.format(path))
    return polygon_rings_from_feature_source(layer)


def _attr_time_str(value):
    if value is None:
        return ''
    if hasattr(value, 'toString'):
        try:
            return value.toString(qt_enum('DateFormat', 'ISODate'))
        except Exception:
            return str(value)
    return str(value)


def dataframe_from_feature_source(source, transform_context=None):
    """Normalise point/line feature source geometry into pipeline dataframe."""
    from ..core.io import vector_input

    tr = _transform_to_4326(source, transform_context)
    fields = [field.name() for field in source.fields()]
    dev_field, time_field = vector_input.detect_device_time_fields(fields)
    geometry_type = source.geometryType()
    is_point = geometry_type == qgis_enum(
        'GeometryType', 'Point', QgsWkbTypes, 'PointGeometry')
    is_line = geometry_type == qgis_enum(
        'GeometryType', 'Line', QgsWkbTypes, 'LineGeometry')
    use_time = is_point and time_field is not None
    if not (is_point or is_line):
        raise ValueError('Input must contain point or line features')

    devices, lats, lons, times = [], [], [], []
    for feature in source.getFeatures():
        geometry = feature.geometry()
        if geometry is None or geometry.isEmpty():
            continue
        geometry = QgsGeometry(geometry)
        if tr is not None:
            geometry.transform(tr)
        if is_point:
            device = feature[dev_field] if dev_field else 'points'
            points = geometry.asMultiPoint() if geometry.isMultipart() else [geometry.asPoint()]
            for point in points:
                devices.append(str(device))
                lats.append(point.y())
                lons.append(point.x())
                if use_time:
                    times.append(_attr_time_str(feature[time_field]))
        elif is_line:
            parts = geometry.asMultiPolyline() if geometry.isMultipart() else [geometry.asPolyline()]
            for part in parts:
                for point in part:
                    devices.append('f{0}'.format(feature.id()))
                    lats.append(point.y())
                    lons.append(point.x())
    return vector_input.to_dataframe(
        devices, lats, lons, times=(times if use_time else None))


def df_from_layer(layer):
    """Backward-compatible alias for GUI callers."""
    return dataframe_from_feature_source(layer)


def df_from_file(path):
    """Load a supported OGR vector file as normalised pipeline dataframe."""
    ext = os.path.splitext(path)[1].lower()
    layer = None
    if ext == '.gpx':
        layer = QgsVectorLayer(path + '|layername=track_points', 'gpx_points', 'ogr')
    if layer is None or not layer.isValid():
        layer = QgsVectorLayer(path, os.path.basename(path), 'ogr')
    if not layer.isValid():
        raise ValueError('Invalid vector file: {0}'.format(path))
    return dataframe_from_feature_source(layer)


def metric_graph_from_feature_source(source, transform_context=None):
    """Read a line source and project it to the metric graph used by postops."""
    from ..core.density import projection
    from ..core.graph import simplify as simplify_mod

    graph = graph_from_feature_source(source, transform_context)
    if not graph.nodes:
        return graph, None
    lons = np.array([xy[0] for xy in graph.nodes.values()], dtype=float)
    lats = np.array([xy[1] for xy in graph.nodes.values()], dtype=float)
    projector = projection.Projector.for_data(lons, lats)
    for node_id, (lon, lat) in list(graph.nodes.items()):
        x, y = projector.forward(np.array([lon]), np.array([lat]))
        graph.nodes[node_id] = (float(x[0]), float(y[0]))
    for edge in graph.edges:
        lonlat = edge['coords_lonlat']
        x, y = projector.forward(lonlat[:, 0], lonlat[:, 1])
        edge['coords'] = np.column_stack([x, y])
        edge['length'] = simplify_mod.polyline_length(edge['coords'])
    return graph, projector
