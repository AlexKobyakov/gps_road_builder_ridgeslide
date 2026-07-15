# -*- coding: utf-8 -*-
"""Offline tests for edge attributes (road_class, reconstructed) — WS-G."""

from gps_road_builder.core.graph import attributes
from gps_road_builder.core.graph.to_graph import RoadGraph


def test_class_thresholds_empty():
    assert attributes.class_thresholds([]) == (0.0, 0.0, 0.0)
    assert attributes.class_thresholds([0, 0, 0]) == (0.0, 0.0, 0.0)


def test_classify_by_quantiles():
    t = attributes.class_thresholds([1, 5, 10, 100])
    assert attributes.classify(0, t) == 'winter'
    assert attributes.classify(1, t) == 'winter'      # below q25
    assert attributes.classify(5, t) == 'ordinary'
    assert attributes.classify(10, t) == 'improved'
    assert attributes.classify(100, t) == 'main'


def test_annotate_sets_class_and_reconstructed():
    g = RoadGraph()
    g.edges = [
        {'u': 0, 'v': 1, 'frequency': 0},
        {'u': 1, 'v': 2, 'frequency': 100},
    ]
    attributes.annotate(g)
    assert g.edges[0]['road_class'] == 'winter'
    assert g.edges[0]['reconstructed'] == 1
    assert g.edges[1]['road_class'] == 'main'
    assert g.edges[1]['reconstructed'] == 0


def test_annotate_all_zero_frequency():
    g = RoadGraph()
    g.edges = [{'u': 0, 'v': 1, 'frequency': 0}]
    attributes.annotate(g)
    assert g.edges[0]['road_class'] == 'winter'
    assert g.edges[0]['reconstructed'] == 1
