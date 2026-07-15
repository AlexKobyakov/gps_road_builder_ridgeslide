# -*- coding: utf-8 -*-
"""
Kernel-density surface for sparse GPS data (method of the FGIS LK note).
Ядерная оценка плотности по точкам (без ресэмпла и Slide) — подходит для
разрежённых данных ФГИС ЛК (фикс каждые 15 мин / 5 км), где интерполяция между
далёкими фиксами рисует фейковую геометрию.

Реализация: биннинг точек в растр + гауссово размытие с σ = radius / cell
(эквивалент KDE с гауссовым ядром; аналог ArcGIS Kernel Density со search
radius). См. docs/ADD1_ANALYSIS_AND_PLAN.md (WS-B).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from . import grid as grid_mod


def build_kde(tracks, cell, radius_m=50.0, bounds=None, margin_cells=3,
              max_cells=None):
    """Построить KDE-поверхность плотности по точкам треков.

    Args:
        tracks: список массивов (Ni, 2) в метрах (НЕ ресэмплированные — сырые
            точки).
        cell: размер ячейки, м (для разрежённых данных обычно 10 м).
        radius_m: радиус ядра (search radius), м.
        bounds: (xmin, ymin, xmax, ymax) или None.

    Returns:
        Grid со сглаженной плотностью.
    """
    from scipy.ndimage import gaussian_filter

    if bounds is None:
        bounds = grid_mod.bounds_of_tracks(tracks)
    if max_cells is not None:
        # ранняя проверка размера (защита от OOM)
        if grid_mod.estimate_cells(bounds, cell, margin_cells) > max_cells:
            raise ValueError('KDE raster too large; increase cell or reduce area')

    grid = grid_mod.build_density(tracks, cell, bounds=bounds,
                                  margin_cells=margin_cells, count_mode='points')
    sigma_px = max(0.5, float(radius_m) / float(cell))
    grid.values = gaussian_filter(grid.values, sigma=sigma_px, mode='constant')
    return grid
