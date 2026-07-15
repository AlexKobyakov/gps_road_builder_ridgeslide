# -*- coding: utf-8 -*-
"""
Spatial splitting for scalable processing (Guo 2020 §4).
Деление рабочей области на перекрывающиеся тайлы и назначение под-треков.
Каждый тайл обрабатывается независимо (меньше память, параллелизуемо), полоса
перекрытия ~15·τ обеспечивает корректную сшивку графов на границах.

Работает в метрическом кадре (после projection.py). Чистый numpy.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import math

import numpy as np


def plan_tiles(bounds, tile_size, overlap):
    """Разбить прямоугольник bounds на сетку тайлов с перекрытием.

    Args:
        bounds: (xmin, ymin, xmax, ymax), метры.
        tile_size: сторона «ядра» тайла (без перекрытия), метры.
        overlap: ширина полосы перекрытия с каждой стороны, метры.

    Returns:
        список dict: 'core' (x0,y0,x1,y1 без перекрытия), 'rect' (с
        перекрытием), 'ij' (индексы тайла).
    """
    xmin, ymin, xmax, ymax = bounds
    span_x = max(xmax - xmin, 1e-9)
    span_y = max(ymax - ymin, 1e-9)
    nx = max(1, int(math.ceil(span_x / tile_size)))
    ny = max(1, int(math.ceil(span_y / tile_size)))
    tiles = []
    for j in range(ny):
        for i in range(nx):
            cx0 = xmin + i * tile_size
            cy0 = ymin + j * tile_size
            cx1 = min(xmax, cx0 + tile_size)
            cy1 = min(ymax, cy0 + tile_size)
            rect = (cx0 - overlap, cy0 - overlap, cx1 + overlap, cy1 + overlap)
            tiles.append({'core': (cx0, cy0, cx1, cy1), 'rect': rect,
                          'ij': (i, j)})
    return tiles


def _runs(mask):
    """Границы (start, end) максимальных серий True в булевом массиве."""
    runs = []
    start = None
    for k, val in enumerate(mask):
        if val and start is None:
            start = k
        elif not val and start is not None:
            runs.append((start, k))
            start = None
    if start is not None:
        runs.append((start, len(mask)))
    return runs


def _reconstruct_grid(tiles):
    """Восстановить параметры регулярной сетки из списка тайлов (plan_tiles)."""
    nx = max(t['ij'][0] for t in tiles) + 1
    ny = max(t['ij'][1] for t in tiles) + 1
    xmin = min(t['core'][0] for t in tiles)
    ymin = min(t['core'][1] for t in tiles)
    t00 = next(t for t in tiles if t['ij'] == (0, 0))
    ts_x = t00['core'][2] - t00['core'][0]
    ts_y = t00['core'][3] - t00['core'][1]
    overlap = t00['core'][0] - t00['rect'][0]
    return nx, ny, xmin, ymin, ts_x, ts_y, overlap


def _emit_runs(tr, rect, bucket):
    rx0, ry0, rx1, ry1 = rect
    inside = ((tr[:, 0] >= rx0) & (tr[:, 0] <= rx1)
              & (tr[:, 1] >= ry0) & (tr[:, 1] <= ry1))
    if not inside.any():
        return
    for s, e in _runs(inside):
        if e - s >= 2:
            bucket.append(tr[s:e])


def assign_tracks_to_tiles(tracks, tiles):
    """Назначить под-треки тайлам (по попаданию точек в rect тайла).

    Быстрый путь: по bbox трека вычисляем ТОЛЬКО те тайлы регулярной сетки,
    которые он может пересечь (обычно 1–4), вместо перебора всех тайлов
    (было O(тайлы×треки) — на реальных данных 361×2.57млн). Семантика (нарезка
    на непрерывные под-треки, перекрытие) сохранена.

    Returns:
        список (по тайлам) списков под-треков (массивы Ni×2), Ni ≥ 2.
    """
    per_tile = [[] for _ in tiles]
    prepared = [np.asarray(tr, dtype=float) for tr in tracks if len(tr) >= 2]

    if len(tiles) == 1:
        for tr in prepared:
            _emit_runs(tr, tiles[0]['rect'], per_tile[0])
        return per_tile

    nx, ny, xmin, ymin, ts_x, ts_y, overlap = _reconstruct_grid(tiles)
    idx_of = {t['ij']: k for k, t in enumerate(tiles)}
    rect_of = {t['ij']: t['rect'] for t in tiles}

    for tr in prepared:
        bx0, by0 = tr[:, 0].min(), tr[:, 1].min()
        bx1, by1 = tr[:, 0].max(), tr[:, 1].max()
        i0 = max(0, int(np.floor((bx0 - xmin - overlap) / ts_x)))
        i1 = min(nx - 1, int(np.floor((bx1 - xmin + overlap) / ts_x)))
        j0 = max(0, int(np.floor((by0 - ymin - overlap) / ts_y)))
        j1 = min(ny - 1, int(np.floor((by1 - ymin + overlap) / ts_y)))
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                k = idx_of.get((i, j))
                if k is not None:
                    _emit_runs(tr, rect_of[(i, j)], per_tile[k])
    return per_tile


def choose_tiling(bounds, n_points, tau, split_mode='auto',
                  tile_grid=None, max_points_per_tile=400_000,
                  overlap_cells=15):
    """Выбрать параметры тайлинга и вернуть список тайлов.

    Args:
        bounds: (xmin,ymin,xmax,ymax).
        n_points: число точек (для оценки при 'auto').
        tau: размер ячейки (для ширины перекрытия 15·τ).
        split_mode: 'off' | 'auto' | 'forced'.
        tile_grid: (nx, ny) для 'forced'.
    """
    xmin, ymin, xmax, ymax = bounds
    span = max(xmax - xmin, ymax - ymin, 1e-9)
    overlap = overlap_cells * tau

    if split_mode == 'off':
        # один тайл на всю область, без перекрытия
        return [{'core': bounds, 'rect': bounds, 'ij': (0, 0)}]

    if split_mode == 'forced' and tile_grid:
        nx, ny = tile_grid
        k = max(1, max(nx, ny))
        tile_size = span / k
        return plan_tiles(bounds, tile_size, overlap)

    # auto
    if n_points <= max_points_per_tile:
        return [{'core': bounds, 'rect': bounds, 'ij': (0, 0)}]
    k = int(math.ceil(math.sqrt(n_points / float(max_points_per_tile))))
    tile_size = span / max(1, k)
    return plan_tiles(bounds, tile_size, overlap)
