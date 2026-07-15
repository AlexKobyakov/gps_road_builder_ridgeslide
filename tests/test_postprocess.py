# -*- coding: utf-8 -*-
"""Offline tests for graph post-cleaning (WS-G)."""

from collections import defaultdict

import numpy as np

from gps_road_builder.core.graph import postprocess
from gps_road_builder.core.graph.to_graph import RoadGraph


def _degrees(graph):
    deg = defaultdict(int)
    for e in graph.edges:
        deg[e['u']] += 1
        deg[e['v']] += 1
    return deg


def _chain_graph():
    """0—1—2—3 as three unit edges; nodes 1,2 are pass-through (degree 2)."""
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (1.0, 0.0), 2: (2.0, 0.0), 3: (3.0, 0.0)}
    g.edges = [
        {'u': 0, 'v': 1, 'coords': np.array([[0.0, 0.0], [1.0, 0.0]]),
         'length': 1.0, 'frequency': 3},
        {'u': 1, 'v': 2, 'coords': np.array([[1.0, 0.0], [2.0, 0.0]]),
         'length': 1.0, 'frequency': 5},
        {'u': 2, 'v': 3, 'coords': np.array([[2.0, 0.0], [3.0, 0.0]]),
         'length': 1.0, 'frequency': 4},
    ]
    return g


def test_merge_degree2_collapses_chain():
    g = postprocess.merge_degree2_chains(_chain_graph())
    assert g.edge_count() == 1
    assert g.node_count() == 2
    e = g.edges[0]
    assert {e['u'], e['v']} == {0, 3}
    assert abs(e['length'] - 3.0) < 1e-9
    assert e['frequency'] == 5                       # max along the chain
    # geometry preserved end to end
    assert np.allclose(e['coords'][0], [0.0, 0.0])
    assert np.allclose(e['coords'][-1], [3.0, 0.0])


def test_merge_keeps_junction():
    # A plus/T junction node must stay (degree >= 3, not collapsed).
    g = _chain_graph()
    g.nodes[4] = (2.0, 1.0)
    g.edges.append({'u': 2, 'v': 4, 'coords': np.array([[2.0, 0.0], [2.0, 1.0]]),
                    'length': 1.0, 'frequency': 1})
    out = postprocess.merge_degree2_chains(g)
    deg = _degrees(out)
    assert max(deg.values()) == 3                    # node 2 is a junction
    # chain 0—1—2 collapsed to a single edge, 2—3 and 2—4 stay
    assert out.edge_count() == 3


def _long_road_with_spur(spur_len):
    """Main road 0—1—2 (long edges) with a spur 1—3 of the given length."""
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (5.0, 0.0), 2: (10.0, 0.0), 3: (5.0, 1.0)}
    g.edges = [
        {'u': 0, 'v': 1, 'coords': np.array([[0.0, 0.0], [5.0, 0.0]]),
         'length': 5.0, 'frequency': 4},
        {'u': 1, 'v': 2, 'coords': np.array([[5.0, 0.0], [10.0, 0.0]]),
         'length': 5.0, 'frequency': 4},
        {'u': 1, 'v': 3, 'coords': np.array([[5.0, 0.0], [5.0, spur_len]]),
         'length': spur_len, 'frequency': 1},
    ]
    return g


def test_remove_short_spurs():
    g = _long_road_with_spur(spur_len=0.5)     # short dangling spur at node 3
    _g, removed = postprocess.remove_short_spurs(g, min_len=1.5)
    assert removed == 1
    assert 3 not in g.nodes
    # the long main road is untouched (its dead-ends are long, not spurs)
    assert g.edge_count() == 2


def test_long_spur_is_kept():
    g = _long_road_with_spur(spur_len=50.0)
    _g, removed = postprocess.remove_short_spurs(g, min_len=1.5)
    assert removed == 0
    assert 3 in g.nodes


def test_postprocess_graph_pipeline():
    # Long chain 0—1—2—3 (nodes 1,2 pass-through) with a short spur at node 2.
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (10.0, 0.0), 2: (20.0, 0.0),
               3: (30.0, 0.0), 4: (20.0, 1.0)}
    g.edges = [
        {'u': 0, 'v': 1, 'coords': np.array([[0.0, 0.0], [10.0, 0.0]]),
         'length': 10.0, 'frequency': 4},
        {'u': 1, 'v': 2, 'coords': np.array([[10.0, 0.0], [20.0, 0.0]]),
         'length': 10.0, 'frequency': 5},
        {'u': 2, 'v': 3, 'coords': np.array([[20.0, 0.0], [30.0, 0.0]]),
         'length': 10.0, 'frequency': 4},
        {'u': 2, 'v': 4, 'coords': np.array([[20.0, 0.0], [20.0, 0.5]]),
         'length': 0.5, 'frequency': 1},   # short spur
    ]
    out = postprocess.postprocess_graph(g, spur_min_m=1.5)
    # spur removed, remaining chain 0—1—2—3 fully collapsed to one edge
    assert out.edge_count() == 1
    assert {out.edges[0]['u'], out.edges[0]['v']} == {0, 3}


def test_self_loop_preserved():
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0)}
    g.edges = [{'u': 0, 'v': 0,
                'coords': np.array([[0.0, 0.0], [1.0, 1.0], [0.0, 0.0]]),
                'length': 2.8, 'frequency': 2}]
    out = postprocess.merge_degree2_chains(g)
    assert out.edge_count() == 1
    assert out.edges[0]['u'] == out.edges[0]['v']


def test_empty_graph():
    g = RoadGraph()
    out = postprocess.postprocess_graph(g, spur_min_m=5.0)
    assert out.edge_count() == 0
    assert out.node_count() == 0


def test_remove_small_loops():
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (10.0, 0.0)}
    g.edges = [
        {'u': 0, 'v': 1, 'coords': np.array([[0.0, 0.0], [10.0, 0.0]]),
         'length': 10.0, 'frequency': 2},                    # normal edge
        {'u': 0, 'v': 0, 'coords': np.array([[0.0, 0.0], [1.0, 1.0],
                                             [0.0, 0.0]]),
         'length': 2.0, 'frequency': 1},                     # short self-loop
    ]
    _g, removed = postprocess.remove_small_loops(g, min_len=5.0)
    assert removed == 1
    assert g.edge_count() == 1
    assert {g.edges[0]['u'], g.edges[0]['v']} == {0, 1}
