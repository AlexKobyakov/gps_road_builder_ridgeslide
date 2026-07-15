# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
High-level RidgeSlide compaction (Guo 2020 §3.3). Part of the MIT-licensed
RidgeSlide core (see LICENSE / NOTICE in this folder).
Оркестрация шага компактификации: сгладить поверхность плотности, посчитать
градиент, скорректировать треки улучшенным Slide, пересчитать более компактную
поверхность плотности по скорректированным трекам.

Работает в метрическом кадре (после projection.py). Треки — список массивов
(Ni, 2), эквидистантно ресэмплированных (resample.py).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

from ..density import blur, grid as grid_mod
from . import kernel


def tracks_to_csr(tracks):
    """Список треков (Ni,2) → плоский pts (N,2) float64 + offsets (M+1,)."""
    arrays = [np.ascontiguousarray(t, dtype=np.float64) for t in tracks
              if len(t) > 0]
    if not arrays:
        return np.zeros((0, 2)), np.zeros(1, dtype=np.int64)
    lengths = [len(a) for a in arrays]
    offsets = np.zeros(len(arrays) + 1, dtype=np.int64)
    offsets[1:] = np.cumsum(lengths)
    pts = np.vstack(arrays)
    return pts, offsets


def csr_to_tracks(pts, offsets):
    """Обратно: pts + offsets → список треков (Ni,2)."""
    return [pts[int(offsets[t]):int(offsets[t + 1])].copy()
            for t in range(len(offsets) - 1)]


def run_slide(tracks, grid, sigma_px, sharpness=1.5,
              weights=kernel.DEFAULT_WEIGHTS,
              u_thr=kernel.DEFAULT_U_THR,
              min_iter=kernel.DEFAULT_MIN_LOOPS,
              max_iter=kernel.DEFAULT_MAX_LOOPS,
              depth_reduce=False, backend='auto'):
    """Скорректировать треки по поверхности плотности `grid`.

    Returns:
        список скорректированных треков (Ni, 2).
    """
    smoothed = blur.smooth_density(grid.values, sigma_px, sharpness=sharpness)
    gx, gy = blur.gradient(smoothed)
    pts, offsets = tracks_to_csr(tracks)
    if len(pts) == 0:
        return []
    kernel.slide_all(
        pts, offsets, smoothed, gx, gy, grid.ox, grid.oy, grid.inv_cell,
        weights=weights, u_thr=u_thr, min_iter=min_iter, max_iter=max_iter,
        depth_reduce=depth_reduce, backend=backend)
    return csr_to_tracks(pts, offsets)


def compact_density(tracks, cell, sigma1=5.0, sigma2=3.0, sharpness=1.5,
                    weights=kernel.DEFAULT_WEIGHTS,
                    u_thr=kernel.DEFAULT_U_THR,
                    min_iter=kernel.DEFAULT_MIN_LOOPS,
                    max_iter=kernel.DEFAULT_MAX_LOOPS,
                    depth_reduce=False, backend='auto', count_mode='tracks'):
    """Полный шаг компактификации (Guo §3.3).

    1. Построить поверхность плотности по исходным трекам.
    2. Скорректировать треки Slide по сглаженной (σ1) поверхности.
    3. Пересчитать более компактную поверхность плотности по скорректированным
       трекам (сырую; сглаживание σ2 применяет следующий этап — скелет).

    Returns:
        dict: adjusted_tracks, density (Grid, пересчитанная сырая),
              initial_density (Grid), bounds.
    """
    non_empty = [t for t in tracks if len(t) > 0]
    if not non_empty:
        return {'adjusted_tracks': [], 'density': None,
                'initial_density': None, 'bounds': None, 'sigma2': sigma2}
    tracks = non_empty
    bounds = grid_mod.bounds_of_tracks(tracks)
    grid1 = grid_mod.build_density(tracks, cell, bounds=bounds,
                                   count_mode=count_mode)
    adjusted = run_slide(
        tracks, grid1, sigma1, sharpness=sharpness, weights=weights,
        u_thr=u_thr, min_iter=min_iter, max_iter=max_iter,
        depth_reduce=depth_reduce, backend=backend)
    # Пересчёт по скорректированным трекам в тех же границах.
    grid2 = grid_mod.build_density(adjusted, cell, bounds=bounds,
                                   count_mode=count_mode)
    return {
        'adjusted_tracks': adjusted,
        'density': grid2,
        'initial_density': grid1,
        'bounds': bounds,
        'sigma2': sigma2,
    }
