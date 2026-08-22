# -*- coding: utf-8 -*-
"""Compatibility re-export for legacy GUI imports.

QGIS adapters now live in :mod:`qgis_adapter.layers`, shared with the
Processing provider.  Keep this module while third-party GUI customisations
may still import ``gui.layers``.
"""

from ..qgis_adapter.layers import (
    add_to_project, build_road_layer, dataframe_from_feature_source, df_from_file,
    df_from_layer, graph_from_feature_source, graph_from_layer,
    metric_graph_from_feature_source, polygon_rings_from_feature_source,
    polygon_rings_from_file, polygon_rings_from_layer, road_graph_fields,
    write_graph_to_sink,
)

__all__ = [
    'add_to_project', 'build_road_layer', 'dataframe_from_feature_source',
    'df_from_file', 'df_from_layer', 'graph_from_feature_source',
    'graph_from_layer', 'metric_graph_from_feature_source',
    'polygon_rings_from_feature_source', 'polygon_rings_from_file',
    'polygon_rings_from_layer', 'road_graph_fields', 'write_graph_to_sink',
]
