# -*- coding: utf-8 -*-
"""Offline tests for the RidgeSlide public API façade (ADD4 п.10)."""

from collections import defaultdict

import numpy as np
import pytest

pytest.importorskip('scipy')

from gps_road_builder.core.ridgeslide import (  # noqa: E402
    RidgeSlide, RidgeSlideConfig, RidgeSlideResult)


def _plus_tracks(seed=0):
    """Dense '+' network of planar (metric) tracks: 8 horizontal + 8 vertical."""
    rng = np.random.default_rng(seed)
    steps = np.arange(-100.0, 100.1, 5.0)
    tracks = []
    for _ in range(8):
        jit = rng.normal(0.0, 0.8)
        tracks.append(np.column_stack([steps,
                                       jit + rng.normal(0, 0.2, len(steps))]))
    for _ in range(8):
        jit = rng.normal(0.0, 0.8)
        tracks.append(np.column_stack([jit + rng.normal(0, 0.2, len(steps)),
                                       steps]))
    return tracks


def test_fit_builds_plus_network():
    cfg = RidgeSlideConfig(cell=5.0, sigma1=3.0, sigma2=2.0, sharpness=1.0,
                           min_loops=0, max_loops=80, backend='numpy',
                           eps_mode='otsu', edge_f_min=1, edge_l_min=0.0)
    result = RidgeSlide(cfg).fit(_plus_tracks())
    assert isinstance(result, RidgeSlideResult)
    assert result.edges >= 4                      # four arms
    assert result.density is not None
    deg = defaultdict(int)
    for e in result.graph.edges:
        deg[e['u']] += 1
        deg[e['v']] += 1
    assert max(deg.values()) >= 3                 # central junction


def test_fit_empty_returns_empty_result():
    result = RidgeSlide().fit([])
    assert result.edges == 0 and result.nodes == 0
    assert result.density is None


def test_fit_rejects_non_planar_shape():
    with pytest.raises(ValueError):
        RidgeSlide().fit([np.zeros((5, 3))])      # not (n, 2)


def test_default_config_values():
    cfg = RidgeSlideConfig()
    assert cfg.cell == 5.0 and cfg.backend == 'auto'
    assert cfg.eps_mode == 'otsu' and cfg.node_merge_m is None
