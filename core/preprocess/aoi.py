# -*- coding: utf-8 -*-
"""
Area-of-interest clipping (WS-AOI).
Обрезка точек по полигону области интереса ДО обработки — убирает мусор вне зоны
(точки в море/океане/вне лесфонда) и сразу уменьшает объём. Полигон задаётся
списком колец (lon, lat); внутренность — по правилу even-odd (поддержка дыр и
мультиполигонов).

Чистый numpy (луч-кастинг) — не требует shapely, тестируется офлайн.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

from ..io import schema


def _ray_cast(x, y, ring):
    """Маска «точка внутри одного кольца» (алгоритм чётности пересечений)."""
    ring = np.asarray(ring, dtype=float)
    if len(ring) < 3:
        return np.zeros(len(x), dtype=bool)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    inside = np.zeros(len(x), dtype=bool)
    xr, yr = ring[:, 0], ring[:, 1]
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = xr[i], yr[i]
        xj, yj = xr[j], yr[j]
        # пересекает ли горизонтальный луч из точки ребро (i, j)
        cond = ((yi > y) != (yj > y))
        with np.errstate(divide='ignore', invalid='ignore'):
            xcross = (xj - xi) * (y - yi) / (yj - yi) + xi
        inside ^= cond & (x < xcross)
        j = i
    return inside


def points_in_polygon(lon, lat, rings):
    """Маска точек внутри полигона (список колец, правило even-odd).

    Args:
        lon, lat: массивы координат.
        rings: список колец, каждое — (K, 2) массив (lon, lat).

    Returns:
        bool-маска длины len(lon).
    """
    lon = np.asarray(lon, dtype=float)
    if lon.size == 0 or not rings:
        return np.zeros(lon.shape, dtype=bool)
    inside = np.zeros(lon.shape, dtype=bool)
    for ring in rings:
        inside ^= _ray_cast(lon, lat, ring)
    return inside


def clip_points(df, rings):
    """Оставить в DataFrame только точки внутри полигона AOI.

    Returns:
        (clipped_df, removed_count).
    """
    if df.empty or not rings:
        return df.reset_index(drop=True), 0
    mask = points_in_polygon(
        df[schema.LON].to_numpy(), df[schema.LAT].to_numpy(), rings)
    removed = int((~mask).sum())
    return df[mask].reset_index(drop=True), removed
