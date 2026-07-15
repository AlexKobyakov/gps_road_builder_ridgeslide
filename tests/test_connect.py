# -*- coding: utf-8 -*-
"""Offline tests for graph connectivity ops (WS-Conn)."""

import numpy as np

from gps_road_builder.core.graph import connect
from gps_road_builder.core.graph.to_graph import RoadGraph


def _two_roads_with_gap(gap=2.0):
    """Two separate roads: 0—1 and 2—3, with a small gap between 1 and 2."""
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


def test_connect_bridges_small_gap():
    g = _two_roads_with_gap(gap=2.0)
    assert len(connect.components(g)) == 2       # disconnected
    g, bridged = connect.connect_dangling_ends(g, radius=5.0)
    assert bridged == 1
    assert len(connect.components(g)) == 1       # now connected
    # the bridge is a straight, zero-frequency edge between nodes 1 and 2
    bridge = [e for e in g.edges if {e['u'], e['v']} == {1, 2}]
    assert len(bridge) == 1
    assert bridge[0]['frequency'] == 0


def test_connect_respects_radius():
    g = _two_roads_with_gap(gap=2.0)
    _g, bridged = connect.connect_dangling_ends(g, radius=1.0)
    assert bridged == 0                          # gap 2 m > radius 1 m


def test_connect_does_not_link_own_neighbor():
    # A single edge: both ends are degree 1 but already neighbours → no bridge.
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (3.0, 0.0)}
    g.edges = [{'u': 0, 'v': 1, 'coords': np.array([[0.0, 0.0], [3.0, 0.0]]),
                'length': 3.0, 'frequency': 1}]
    _g, bridged = connect.connect_dangling_ends(g, radius=10.0)
    assert bridged == 0


def test_largest_component():
    g = _two_roads_with_gap(gap=100.0)           # far apart, stay separate
    g.edges[1]['length'] = 5.0                   # 2—3 shorter than 0—1
    out = connect.largest_component(g)
    assert out.edge_count() == 1
    assert {out.edges[0]['u'], out.edges[0]['v']} == {0, 1}   # kept the longer


def test_remove_small_components():
    g = _two_roads_with_gap(gap=100.0)
    g.edges[1]['length'] = 5.0
    out, dropped = connect.remove_small_components(g, min_length_m=7.0)
    assert dropped == 1
    assert out.edge_count() == 1


def test_components_of_empty_graph():
    assert connect.components(RoadGraph()) == []


def _through_edge_with_stub(stub_y=5.0):
    """Through edge 0—1 (y=0) and a dangling stub 2—3 whose end (node 2) is
    stub_y metres above the MIDDLE of the through edge (a T-gap)."""
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (20.0, 0.0),
               2: (10.0, stub_y), 3: (10.0, stub_y + 10.0)}
    g.edges = [
        {'u': 0, 'v': 1, 'coords': np.array([[0.0, 0.0], [20.0, 0.0]]),
         'length': 20.0, 'frequency': 5},
        {'u': 2, 'v': 3, 'coords': np.array([[10.0, stub_y],
                                             [10.0, stub_y + 10.0]]),
         'length': 10.0, 'frequency': 2},
    ]
    return g


def test_snap_dangling_to_edge_bridges_t_gap():
    # The stub end is 5 m from the middle of the through edge; node-to-node
    # would fail (nearest node is 10 m away at a corner), node-to-edge bridges it.
    g = _through_edge_with_stub(stub_y=5.0)
    assert len(connect.components(g)) == 2
    _n2n, bridged = connect.connect_dangling_ends(_through_edge_with_stub(5.0),
                                                  radius=6.0)
    assert bridged == 0                      # node-to-node can't bridge a T-gap
    out, snapped = connect.snap_dangling_to_edges(g, radius=6.0)
    assert snapped == 1
    assert len(connect.components(out)) == 1   # now connected
    assert out.edge_count() == 4               # through edge split + connector


def test_snap_respects_radius():
    g = _through_edge_with_stub(stub_y=20.0)   # end is 20 m away
    _out, snapped = connect.snap_dangling_to_edges(g, radius=6.0)
    assert snapped == 0


def test_snap_no_edges():
    assert connect.snap_dangling_to_edges(RoadGraph(), 10.0)[1] == 0


def _two_collinear_roads(gap=5.0, perpendicular=False):
    """Road A 0—1 (along +x) and road B 2—3 facing it across a gap."""
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (10.0, 0.0)}
    g.edges = [{'u': 0, 'v': 1, 'coords': np.array([[0.0, 0.0], [10.0, 0.0]]),
                'length': 10.0, 'frequency': 3}]
    if perpendicular:
        g.nodes[2] = (10.0 + gap, 0.0)
        g.nodes[3] = (10.0 + gap, 10.0)
    else:
        g.nodes[2] = (10.0 + gap, 0.0)
        g.nodes[3] = (20.0 + gap, 0.0)
    g.edges.append({'u': 2, 'v': 3,
                    'coords': np.array([g.nodes[2], g.nodes[3]], dtype=float),
                    'length': 10.0, 'frequency': 2})
    return g


def test_bridge_facing_connects_collinear():
    g = _two_collinear_roads(gap=5.0)
    g, faced = connect.bridge_facing_ends(g, max_dist=8.0)
    assert faced == 1
    assert len(connect.components(g)) == 1


def test_bridge_facing_skips_perpendicular():
    g = _two_collinear_roads(gap=5.0, perpendicular=True)
    _g, faced = connect.bridge_facing_ends(g, max_dist=8.0)
    assert faced == 0                        # wide angle → not a continuation


def test_stitch_components_guarantees_connectivity():
    g = _two_roads_with_gap(gap=100.0)       # two components, 100 m apart
    assert len(connect.components(g)) == 2
    g, stitched = connect.stitch_components(g, max_dist=150.0)
    assert stitched == 1
    assert len(connect.components(g)) == 1


def test_stitch_respects_max_dist():
    g = _two_roads_with_gap(gap=100.0)
    _g, stitched = connect.stitch_components(g, max_dist=50.0)
    assert stitched == 0                     # 100 m gap > 50 m limit


def _crossing_pair():
    """Horizontal edge 0—1 and vertical edge 2—3 that cross at (5, 0) with no
    shared node (topologically disconnected X)."""
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


def test_break_at_crossings_makes_junction():
    g = _crossing_pair()
    assert len(connect.components(g)) == 2       # disconnected X
    out, broken = connect.break_at_crossings(g)
    assert broken == 1
    assert out.node_count() == 5                 # a shared node at (5, 0)
    assert out.edge_count() == 4                 # each edge split in two
    assert len(connect.components(out)) == 1     # now connected
    # the new junction node sits at the crossing point
    xy = [c for nid, c in out.nodes.items() if nid not in (0, 1, 2, 3)][0]
    assert abs(xy[0] - 5.0) < 1e-6 and abs(xy[1] - 0.0) < 1e-6


def test_break_ignores_parallel_edges():
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (10.0, 0.0), 2: (0.0, 5.0), 3: (10.0, 5.0)}
    g.edges = [
        {'u': 0, 'v': 1, 'coords': np.array([[0.0, 0.0], [10.0, 0.0]]),
         'length': 10.0, 'frequency': 1},
        {'u': 2, 'v': 3, 'coords': np.array([[0.0, 5.0], [10.0, 5.0]]),
         'length': 10.0, 'frequency': 1},
    ]
    _out, broken = connect.break_at_crossings(g)
    assert broken == 0                           # parallel, never cross


def test_break_ignores_t_touch_endpoint():
    # A vertical edge whose END touches the middle of the horizontal edge is a
    # T-junction (snap's job), not an interior crossing — break must ignore it.
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (10.0, 0.0), 2: (5.0, 0.0), 3: (5.0, 5.0)}
    g.edges = [
        {'u': 0, 'v': 1, 'coords': np.array([[0.0, 0.0], [10.0, 0.0]]),
         'length': 10.0, 'frequency': 1},
        {'u': 2, 'v': 3, 'coords': np.array([[5.0, 0.0], [5.0, 5.0]]),
         'length': 5.0, 'frequency': 1},
    ]
    _out, broken = connect.break_at_crossings(g)
    assert broken == 0
