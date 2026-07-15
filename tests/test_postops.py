# -*- coding: utf-8 -*-
"""Offline tests for the post-processing orchestrator (WS-Post)."""

import numpy as np

from gps_road_builder.core.graph import postops, connect
from gps_road_builder.core.graph.to_graph import RoadGraph


def _two_roads_with_gap(gap=2.0):
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (10.0, 0.0),
               2: (10.0 + gap, 0.0), 3: (20.0 + gap, 0.0)}
    g.edges = [
        {'u': 0, 'v': 1, 'coords': np.array([[0.0, 0.0], [10.0, 0.0]]),
         'length': 10.0, 'frequency': 3},
        {'u': 2, 'v': 3, 'coords': np.array([[10.0 + gap, 0.0],
                                             [20.0 + gap, 0.0]]),
         'length': 10.0, 'frequency': 2},
    ]
    return g


def test_apply_bridges_and_annotates():
    g = _two_roads_with_gap(gap=2.0)
    out, stats = postops.apply(g, {'connect_gap_m': 5.0, 'smooth_iters': 1})
    assert stats['bridged'] == 1
    assert len(connect.components(out)) == 1          # connected
    assert 'edges' in stats and 'nodes' in stats
    assert all('road_class' in e and 'reconstructed' in e for e in out.edges)


def test_apply_keep_largest():
    g = _two_roads_with_gap(gap=100.0)                # far apart
    g.edges[1]['length'] = 5.0
    out, _stats = postops.apply(g, {'keep_largest': True})
    assert len(connect.components(out)) == 1
    assert out.edge_count() == 1


def test_apply_noop_defaults_still_annotates():
    g = _two_roads_with_gap(gap=100.0)
    out, stats = postops.apply(g, {})
    assert stats['edges'] == out.edge_count()
    assert all('road_class' in e for e in out.edges)


def _crossing_pair():
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (10.0, 0.0),
               2: (5.0, -5.0), 3: (5.0, 5.0)}
    g.edges = [
        {'u': 0, 'v': 1, 'coords': np.array([[0.0, 0.0], [10.0, 0.0]]),
         'length': 10.0, 'frequency': 4},
        {'u': 2, 'v': 3, 'coords': np.array([[5.0, -5.0], [5.0, 5.0]]),
         'length': 10.0, 'frequency': 2},
    ]
    return g


def test_apply_break_at_crossings():
    g = _crossing_pair()
    out, stats = postops.apply(g, {'break_crossings': True})
    assert stats['broken'] == 1
    assert len(connect.components(out)) == 1          # X now a real junction


def test_apply_junction_consolidation_merges_cluster():
    # Two dead-end nodes 3 m apart (a bushy junction) collapse into one node
    # with a consolidation radius, reconnecting the two roads.
    g = _two_roads_with_gap(gap=3.0)                   # nodes 1 & 2 are 3 m apart
    assert len(connect.components(g)) == 2
    out, stats = postops.apply(g, {'junction_m': 5.0})
    assert stats['junctions_merged'] >= 1
    assert len(connect.components(out)) == 1          # nodes 1 & 2 collapsed
