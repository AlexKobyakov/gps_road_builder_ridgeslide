# -*- coding: utf-8 -*-
"""Offline tests for the KDE density and gap-closing (sparse-data method)."""

import numpy as np
import pytest

pytest.importorskip('scipy')

from gps_road_builder.core.density import kde  # noqa: E402
from gps_road_builder.core.graph import binarize  # noqa: E402


def test_build_kde_smooths_and_spreads():
    # a handful of scattered points → KDE spreads density around them
    pts = np.array([[0.0, 0.0], [50.0, 0.0], [100.0, 0.0]])
    grid = kde.build_kde([pts], cell=10.0, radius_m=30.0)
    assert grid.values.max() > 0.0
    # density is smooth (many non-zero cells, not just 3)
    assert int((grid.values > 1e-6).sum()) > 10


def test_close_gaps_bridges_line_break():
    mask = np.zeros((7, 20), bool)
    mask[3, :9] = True
    mask[3, 11:] = True          # 1-pixel gap at column 9-10
    closed = binarize.close_gaps(mask, radius_px=2)
    assert closed[3, 9] and closed[3, 10]   # gap bridged


def test_close_gaps_zero_radius_noop():
    mask = np.zeros((5, 5), bool)
    mask[2, 2] = True
    out = binarize.close_gaps(mask, radius_px=0)
    assert np.array_equal(out, mask)
