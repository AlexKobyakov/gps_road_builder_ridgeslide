# -*- coding: utf-8 -*-
"""Offline tests for polyline smoothing (WS-Smooth)."""

import numpy as np

from gps_road_builder.core.graph import smoothing
from gps_road_builder.core.graph.to_graph import RoadGraph


def _max_turn(coords):
    """Максимальный абсолютный угол поворота в вершине (мера «остроты» углов).

    Углорезка Chaikin сохраняет СУММАРНЫЙ поворот, но уменьшает самый острый
    угол — именно это и есть «сглаживание ступенек».
    """
    d = np.diff(coords, axis=0)
    ang = np.arctan2(d[:, 1], d[:, 0])
    dang = np.diff(ang)
    dang = (dang + np.pi) % (2 * np.pi) - np.pi
    return float(np.abs(dang).max()) if len(dang) else 0.0


def test_chaikin_keeps_endpoints():
    pts = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 0.0], [3.0, 1.0]])
    out = smoothing.chaikin(pts, iterations=2, keep_ends=True)
    assert np.allclose(out[0], pts[0])
    assert np.allclose(out[-1], pts[-1])


def test_chaikin_reduces_jaggedness():
    # A stair-step zigzag: the sharpest corner (90°) must become gentler.
    pts = np.array([[0, 0], [1, 0], [1, 1], [2, 1], [2, 2], [3, 2]], float)
    before = _max_turn(pts)
    out = smoothing.chaikin(pts, iterations=3)
    after = _max_turn(out)
    assert after < before
    assert len(out) > len(pts)


def test_chaikin_noop_on_short_or_zero_iters():
    pts = np.array([[0.0, 0.0], [1.0, 1.0]])
    assert np.allclose(smoothing.chaikin(pts, iterations=3), pts)   # <3 points
    pts3 = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 0.0]])
    assert np.allclose(smoothing.chaikin(pts3, iterations=0), pts3)  # 0 iters


def test_smooth_graph_updates_length_and_keeps_ends():
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (3.0, 0.0)}
    coords = np.array([[0, 0], [1, 1], [2, -1], [3, 0]], float)
    g.edges = [{'u': 0, 'v': 1, 'coords': coords.copy(),
                'length': 10.0, 'frequency': 2}]
    smoothing.smooth_graph(g, iterations=2)
    e = g.edges[0]
    assert np.allclose(e['coords'][0], [0.0, 0.0])
    assert np.allclose(e['coords'][-1], [3.0, 0.0])
    assert e['length'] > 0
    assert e['frequency'] == 2                       # attrs preserved
