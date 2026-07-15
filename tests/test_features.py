# -*- coding: utf-8 -*-
"""Offline tests for io.features (graph → feature records) and histogram."""

import numpy as np

from gps_road_builder.core.io import features
from gps_road_builder.core import histogram
from gps_road_builder.core.graph.to_graph import RoadGraph


def _graph():
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (1.0, 1.0)}
    g.edges = [
        {'u': 0, 'v': 1, 'frequency': 5, 'length': 12.0,
         'coords_lonlat': np.array([[134.0, 45.0], [134.001, 45.001]])},
        {'u': 0, 'v': 1, 'frequency': 1, 'length': 3.0},   # no geometry → skip
    ]
    return g


def test_road_graph_features_skips_geometryless():
    feats = features.road_graph_features(_graph())
    assert len(feats) == 1
    assert feats[0]['frequency'] == 5
    assert feats[0]['length'] == 12.0
    assert feats[0]['coords_lonlat'].shape == (2, 2)


def test_features_to_geojson_structure():
    feats = features.road_graph_features(_graph())
    gj = features.features_to_geojson(feats)
    assert gj['type'] == 'FeatureCollection'
    assert len(gj['features']) == 1
    geom = gj['features'][0]['geometry']
    assert geom['type'] == 'LineString'
    assert len(geom['coordinates']) == 2
    assert gj['features'][0]['properties']['frequency'] == 5


def test_frequency_and_length_values():
    feats = features.road_graph_features(_graph())
    assert list(features.frequency_values(feats)) == [5.0]
    assert list(features.length_values(feats)) == [12.0]


def test_histogram_basic():
    counts, edges = histogram.compute_histogram([1, 1, 2, 3, 3, 3], bins=3)
    assert counts.sum() == 6
    assert len(edges) == 4


def test_histogram_empty_and_constant():
    counts, edges = histogram.compute_histogram([])
    assert counts.size == 0 and edges.size == 0
    counts2, edges2 = histogram.compute_histogram([7, 7, 7], bins=4)
    assert counts2.sum() == 3


def test_histogram_summary():
    s = histogram.summary([1, 2, 3, 4])
    assert s['count'] == 4
    assert s['min'] == 1.0 and s['max'] == 4.0
    assert s['median'] == 2.5
