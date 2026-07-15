# -*- coding: utf-8 -*-
"""Offline tests for the graph-extraction modules."""

from collections import defaultdict

import numpy as np

from gps_road_builder.core.graph import (
    binarize, skeletonize, to_graph, simplify, edge_weights)
from gps_road_builder.core.density.grid import Grid


def _degrees(graph):
    deg = defaultdict(int)
    for e in graph.edges:
        deg[e['u']] += 1
        deg[e['v']] += 1
    return deg


# --- binarize ---

def test_binarize_manual():
    vals = np.array([[0.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 0.0]])
    mask, thr = binarize.binarize(vals, eps=1.0, method='manual')
    assert thr == 1.0
    assert mask[1, 1]
    assert not mask[0, 0]


def test_binarize_otsu_picks_signal():
    vals = np.zeros((5, 5))
    vals[2, 1:4] = 10.0
    mask, thr = binarize.binarize(vals, method='otsu')
    assert mask[2, 1:4].all()
    assert mask.sum() == 3


def test_binarize_percentile():
    # positive values 1, 2, 10, 50 → 50th percentile (median) = 6.0
    vals = np.zeros((5, 5))
    vals[2, 1:5] = [1.0, 2.0, 10.0, 50.0]
    mask, thr = binarize.binarize(vals, method='percentile', percentile=50.0)
    assert abs(thr - 6.0) < 1e-9
    assert mask.sum() == 2                      # only 10 and 50 survive


def test_fill_small_holes_noop_without_area():
    m = np.zeros((5, 5), bool)
    m[1:4, 1:4] = True
    out = binarize.fill_small_holes(m, 0)
    assert (out == m).all()


# --- skeletonize (fallback path is deterministic and dependency-free) ---

def test_zhang_suen_thins_bar_to_line():
    # An elongated bar (3 rows thick, 9 wide) thins to a ~1-pixel-wide line.
    img = np.zeros((13, 15), bool)
    img[5:8, 3:12] = True
    sk = skeletonize.skeletonize(img, backend='zhang_suen')
    assert sk.sum() < img.sum()      # thinned
    assert sk.sum() >= 5             # elongated line remains
    # 1-pixel width: no full 2x2 block remains
    for r in range(sk.shape[0] - 1):
        for c in range(sk.shape[1] - 1):
            assert not (sk[r, c] and sk[r, c + 1]
                        and sk[r + 1, c] and sk[r + 1, c + 1])


# --- to_graph ---

def test_to_graph_simple_line():
    sk = np.zeros((5, 10), bool)
    sk[2, 1:9] = True
    g = to_graph.to_graph(sk)
    assert g.node_count() == 2
    assert g.edge_count() == 1
    assert g.edges[0]['v'] != -1


def test_to_graph_plus_has_junction():
    sk = np.zeros((11, 11), bool)
    sk[5, 1:10] = True
    sk[1:10, 5] = True
    g = to_graph.to_graph(sk)
    assert g.edge_count() >= 4
    assert g.node_count() >= 5
    assert max(_degrees(g).values()) >= 3   # junction detected
    assert all(e['v'] != -1 for e in g.edges)


# --- simplify ---

def test_simplify_straight_line():
    g = to_graph.RoadGraph()
    g.nodes = {0: (2, 1), 1: (2, 8)}
    g.edges = [{'u': 0, 'v': 1,
                'pixels': np.array([[2, c] for c in range(1, 9)])}]
    grid = Grid(0.0, 0.0, 1.0, 10, 5)
    simplify.simplify_graph(g, grid, epsilon_m=2.0)
    e = g.edges[0]
    assert len(e['coords']) == 2               # straight → 2 points
    assert abs(e['length'] - 7.0) < 1e-6       # cols 1..8 centers → dx = 7 m


def test_rdp_keeps_corner():
    pts = np.array([[0, 0], [1, 0], [2, 0], [2, 1], [2, 2]], float)
    out = simplify.rdp(pts, 0.1)
    assert len(out) == 3                        # start, corner, end


# --- edge_weights ---

def _line_graph():
    g = to_graph.RoadGraph()
    g.nodes = {0: (2, 1), 1: (2, 8)}
    g.edges = [{'u': 0, 'v': 1,
                'pixels': np.array([[2, c] for c in range(1, 9)]),
                'length': 7.0}]
    return g


def test_compute_frequency_and_filter():
    grid = Grid(0.0, 0.0, 1.0, 10, 5)
    g = _line_graph()
    # track running along the line (world centres of the edge pixels)
    xs = np.arange(1, 9) + 0.5
    track = np.column_stack([xs, np.full_like(xs, 2.5)])
    edge_weights.compute_frequencies(g, [track], grid)
    assert g.edges[0]['frequency'] >= 1

    # aggressive filter removes the short, low-frequency edge
    g2 = _line_graph()
    g2.edges[0]['frequency'] = 1
    _g, removed = edge_weights.filter_edges(g2, f_min=2, l_min=100.0)
    assert removed == 1
    assert g2.edge_count() == 0

    # lenient filter keeps it
    g3 = _line_graph()
    g3.edges[0]['frequency'] = 1
    edge_weights.filter_edges(g3, f_min=1, l_min=100.0)
    assert g3.edge_count() == 1


def test_count_devices():
    # An edge with world geometry; points from two devices lie on it, one far.
    g = to_graph.RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (10.0, 0.0)}
    g.edges = [{'u': 0, 'v': 1, 'length': 10.0, 'frequency': 1,
                'coords': np.array([[0.0, 0.0], [5.0, 0.0], [10.0, 0.0]])}]
    px = np.array([0.0, 5.0, 10.0, 500.0])
    py = np.array([0.0, 0.1, 0.0, 500.0])
    dev = np.array(['a', 'a', 'b', 'c'])       # 'c' is far away → ignored
    edge_weights.count_devices(g, px, py, dev, max_dist_m=1.0)
    assert g.edges[0]['n_devices'] == 2
