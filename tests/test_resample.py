# -*- coding: utf-8 -*-
"""Offline tests for preprocess.resample."""

import numpy as np

from gps_road_builder.core.preprocess import resample


def test_polyline_length():
    assert abs(resample.polyline_length([[0, 0], [3, 4]]) - 5.0) < 1e-9
    assert resample.polyline_length([[1, 1]]) == 0.0


def test_resample_straight_line_equidistant():
    xy = np.array([[0.0, 0.0], [100.0, 0.0]])
    out = resample.resample_polyline(xy, 10.0)
    assert out.shape == (11, 2)
    assert np.allclose(out[0], [0.0, 0.0])
    assert np.allclose(out[-1], [100.0, 0.0])
    assert resample.is_equidistant(out)


def test_resample_preserves_endpoints_on_corner():
    xy = np.array([[0.0, 0.0], [0.0, 100.0], [100.0, 100.0]])
    out = resample.resample_polyline(xy, 25.0)
    assert np.allclose(out[0], [0.0, 0.0])
    assert np.allclose(out[-1], [100.0, 100.0])
    # arc length is preserved; total ~200 → ~8 intervals
    assert out.shape[0] == 9


def test_resample_degenerate_single_point():
    out = resample.resample_polyline(np.array([[5.0, 5.0]]), 10.0)
    assert out.shape == (1, 2)


def test_resample_zero_length():
    out = resample.resample_polyline(np.array([[5.0, 5.0], [5.0, 5.0]]), 10.0)
    assert out.shape == (1, 2)


def test_resample_requires_positive_step():
    try:
        resample.resample_polyline(np.array([[0, 0], [1, 1]]), 0.0)
        assert False, "expected ValueError"
    except ValueError:
        pass
