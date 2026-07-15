# -*- coding: utf-8 -*-
"""Offline tests for ridgerefine.refine (CSR + high-level compaction)."""

import numpy as np

from gps_road_builder.core.ridgeslide import refine


def test_csr_roundtrip():
    tracks = [np.array([[0.0, 0.0], [1.0, 1.0]]),
              np.array([[2.0, 2.0], [3.0, 3.0], [4.0, 4.0]])]
    pts, offsets = refine.tracks_to_csr(tracks)
    assert pts.shape == (5, 2)
    assert list(offsets) == [0, 2, 5]
    back = refine.csr_to_tracks(pts, offsets)
    assert len(back) == 2
    assert np.allclose(back[0], tracks[0])
    assert np.allclose(back[1], tracks[1])


def _bundle_of_lines(n_tracks=40, n_pts=40, spread=3.0, length=100.0, seed=1):
    """Пучок почти параллельных прямых с поперечным разбросом ~ N(0, spread)."""
    rng = np.random.default_rng(seed)
    xs = np.linspace(0.0, length, n_pts)
    tracks = []
    for _ in range(n_tracks):
        y0 = rng.normal(0.0, spread)
        ys = y0 + rng.normal(0.0, 0.2, n_pts)
        tracks.append(np.column_stack([xs, ys]))
    return tracks


def _cross_spread(tracks):
    """Разброс поперечного положения (средняя y) между треками."""
    return float(np.std([t[:, 1].mean() for t in tracks]))


def test_compact_collapses_similar_tracks():
    # Регресс «похожие треки → одна линия»: после Slide поперечный разброс
    # треков должен заметно уменьшиться (сходятся к общему гребню плотности).
    tracks = _bundle_of_lines(n_tracks=40, spread=3.0)
    spread_before = _cross_spread(tracks)

    result = refine.compact_density(
        tracks, cell=1.0, sigma1=5.0, sigma2=3.0,
        weights=(0.6, 0.15, 0.05, 0.5), u_thr=1e-9,
        min_iter=0, max_iter=250, backend='numpy')

    adjusted = result['adjusted_tracks']
    spread_after = _cross_spread(adjusted)

    assert len(adjusted) == len(tracks)
    assert all(np.all(np.isfinite(t)) for t in adjusted)
    assert spread_after < 0.6 * spread_before   # заметно компактнее
    # пересчитанная плотность должна стать «резче» (макс. выше на пик)
    assert result['density'].values.max() >= result['initial_density'].values.max()


def test_compact_empty_input():
    result = refine.compact_density([np.zeros((0, 2))], cell=1.0,
                                    min_iter=0, max_iter=5, backend='numpy')
    assert result['adjusted_tracks'] == []
