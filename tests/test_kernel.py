# -*- coding: utf-8 -*-
"""Offline tests for ridgeslide.kernel (NumPy reference + Numba equivalence)."""

import numpy as np
import pytest

from gps_road_builder.core.ridgeslide import kernel as sk


def test_bilerp_center_is_corner_average():
    F = np.array([[0.0, 0.0], [0.0, 4.0]])   # corners 0,0,0,4
    v = float(sk._bilerp_np(F, np.array([0.5]), np.array([0.5]))[0])
    assert abs(v - 1.0) < 1e-9              # bilinear centre = mean of corners


def test_bilerp_interior_node_value():
    F = np.arange(9.0).reshape(3, 3)         # 3x3 so node (1,1) is interpolable
    v = float(sk._bilerp_np(F, np.array([1.0]), np.array([1.0]))[0])
    assert abs(v - F[1, 1]) < 1e-9


def test_bilerp_out_of_bounds_zero():
    F = np.ones((3, 3))
    out = sk._bilerp_np(F, np.array([-1.0, 10.0]), np.array([0.0, 0.0]))
    assert np.allclose(out, [0.0, 0.0])


def _ridge_field(height, width, ridge_row, cell=1.0):
    """Плотность-«гребень»: гаусс по строкам с максимумом на ridge_row."""
    rows = np.arange(height)[:, None]
    dens = np.exp(-((rows - ridge_row) ** 2) / (2 * 5.0 ** 2)) * np.ones((1, width))
    return dens


def test_slide_pulls_toward_ridge_numpy():
    # Прямой трек, смещённый от гребня плотности, должен «сползти» к гребню.
    H, W = 40, 60
    ridge = 20.0
    dens = _ridge_field(H, W, ridge)
    from gps_road_builder.core.density import blur
    gx, gy = blur.gradient(dens)

    ys0 = 10.0
    xs = np.linspace(5.0, 54.0, 30)
    track = np.column_stack([xs, np.full_like(xs, ys0)])
    pts = track.copy()
    offsets = np.array([0, len(pts)], dtype=np.int64)

    sk.slide_all(pts, offsets, dens, gx, gy, ox=0.0, oy=0.0, inv_cell=1.0,
                 weights=(0.6, 0.1, 0.05, 0.5), u_thr=1e-9,
                 min_iter=0, max_iter=300, backend='numpy')

    # средняя строка (y) трека должна приблизиться к гребню (20) от 10
    assert pts[:, 1].mean() > ys0 + 2.0
    assert pts[:, 1].mean() < ridge + 1.0
    assert np.all(np.isfinite(pts))


def test_numpy_numba_equivalence():
    pytest.importorskip('numba')
    if not sk.HAVE_NUMBA:
        pytest.skip('numba not available')

    rng = np.random.default_rng(42)
    H, W = 30, 30
    dens = _ridge_field(H, W, 15.0)
    from gps_road_builder.core.density import blur
    gx, gy = blur.gradient(dens)

    # два случайных трека
    t1 = np.column_stack([np.linspace(3, 26, 12), 8 + rng.normal(0, 0.5, 12)])
    t2 = np.column_stack([np.linspace(4, 25, 15), 20 + rng.normal(0, 0.5, 15)])
    pts0, offsets = _csr([t1, t2])

    pts_np = pts0.copy()
    sk.slide_all(pts_np, offsets, dens, gx, gy, 0.0, 0.0, 1.0,
                 u_thr=-1.0, min_iter=6, max_iter=6, backend='numpy')

    pts_nb = pts0.copy()
    sk.slide_all(pts_nb, offsets, dens, gx, gy, 0.0, 0.0, 1.0,
                 u_thr=-1.0, min_iter=6, max_iter=6, backend='numba')

    assert np.allclose(pts_np, pts_nb, atol=1e-3, rtol=1e-5)


def _csr(tracks):
    lengths = [len(t) for t in tracks]
    offsets = np.zeros(len(tracks) + 1, dtype=np.int64)
    offsets[1:] = np.cumsum(lengths)
    pts = np.vstack([np.asarray(t, dtype=float) for t in tracks])
    return pts, offsets
