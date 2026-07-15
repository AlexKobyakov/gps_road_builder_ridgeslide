# -*- coding: utf-8 -*-
"""Offline tests for density.grid."""

import numpy as np

from gps_road_builder.core.density import grid as grid_mod


def test_grid_from_bounds_dimensions():
    g = grid_mod.Grid.from_bounds(0, 0, 100, 50, cell=10, margin_cells=2)
    assert g.cell == 10
    # width covers x-range + 2*margin on each side + 1
    assert g.width == int(np.ceil(100 / 10)) + 2 * 2 + 1
    assert g.height == int(np.ceil(50 / 10)) + 2 * 2 + 1
    assert g.ox == -20 and g.oy == -20


def test_world_to_pixel():
    g = grid_mod.Grid(ox=0.0, oy=0.0, cell=2.0, width=10, height=10)
    px, py = g.world_to_pixel(4.0, 6.0)
    assert px == 2.0 and py == 3.0


def test_build_density_counts_tracks():
    # Two tracks sharing the same central cells → those cells count 2.
    t1 = np.array([[0.0, 0.0], [10.0, 0.0]])
    t2 = np.array([[0.0, 0.0], [10.0, 0.0]])
    g = grid_mod.build_density([t1, t2], cell=1.0, count_mode='tracks')
    assert g.values.max() == 2.0
    assert g.values.sum() > 0


def test_build_density_points_mode_higher():
    t = np.array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])  # 3 points, same cell
    g_tracks = grid_mod.build_density([t], cell=1.0, count_mode='tracks')
    g_points = grid_mod.build_density([t], cell=1.0, count_mode='points')
    assert g_tracks.values.max() == 1.0   # one track through the cell
    assert g_points.values.max() == 3.0   # three points in the cell


def test_bounds_of_tracks():
    b = grid_mod.bounds_of_tracks([np.array([[1.0, 2.0], [5.0, 9.0]])])
    assert b == (1.0, 2.0, 5.0, 9.0)


def test_estimate_cells_matches_from_bounds():
    bounds = (0.0, 0.0, 100.0, 50.0)
    g = grid_mod.Grid.from_bounds(*bounds, cell=10.0, margin_cells=2)
    assert grid_mod.estimate_cells(bounds, 10.0, margin_cells=2) == \
        g.width * g.height


def test_from_bounds_max_cells_guard():
    import pytest
    with pytest.raises(ValueError):
        grid_mod.Grid.from_bounds(0, 0, 100000, 100000, cell=1.0,
                                  max_cells=1_000_000)
