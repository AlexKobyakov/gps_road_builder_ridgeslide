# -*- coding: utf-8 -*-
"""
Density grid for GPS Road Builder (§3.2 of Guo 2020).
Регулярный растр плотности в метрическом кадре: подсчёт числа треков,
проходящих через каждую ячейку. Чистый numpy — векторизовано.

Соглашение о координатах: пиксель (col, row) соответствует мировым
(x, y); px = (x - ox) / cell, py = (y - oy) / cell. row (ось Y) растёт вместе с
мировой y, поэтому градиент по строкам совпадает с +Y.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np


class Grid:
    """Регулярная сетка плотности.

    Attributes:
        ox, oy: мировые координаты угла пикселя (0, 0), метры.
        cell: размер ячейки τ, метры.
        width, height: размеры в пикселях (col, row).
        values: массив (height, width) float64 — плотность.
    """

    def __init__(self, ox, oy, cell, width, height, values=None):
        self.ox = float(ox)
        self.oy = float(oy)
        self.cell = float(cell)
        self.width = int(width)
        self.height = int(height)
        if values is None:
            self.values = np.zeros((self.height, self.width), dtype=float)
        else:
            self.values = values

    @property
    def inv_cell(self):
        return 1.0 / self.cell

    def world_to_pixel(self, x, y):
        """Мировые координаты → дробные пиксельные (px, py)."""
        px = (np.asarray(x, dtype=float) - self.ox) * self.inv_cell
        py = (np.asarray(y, dtype=float) - self.oy) * self.inv_cell
        return px, py

    @classmethod
    def from_bounds(cls, xmin, ymin, xmax, ymax, cell, margin_cells=3,
                    max_cells=None):
        """Построить пустую сетку по границам с запасом в margin_cells ячеек.

        Если задан max_cells и оценка превышает его — ValueError (защита от OOM;
        сигнал уменьшить область/тайл или увеличить ячейку τ).
        """
        cell = float(cell)
        ox = xmin - margin_cells * cell
        oy = ymin - margin_cells * cell
        width = int(np.ceil((xmax - xmin) / cell)) + 2 * margin_cells + 1
        height = int(np.ceil((ymax - ymin) / cell)) + 2 * margin_cells + 1
        if max_cells is not None and width * height > max_cells:
            raise ValueError(
                'Density raster too large: {0}x{1} = {2:.0f}M cells (limit '
                '{3:.0f}M). Increase cell size or reduce tile size.'.format(
                    width, height, width * height / 1e6, max_cells / 1e6))
        return cls(ox, oy, cell, width, height)


def estimate_cells(bounds, cell, margin_cells=3):
    """Оценить число ячеек растра для границ и размера ячейки."""
    xmin, ymin, xmax, ymax = bounds
    cell = float(cell)
    width = int(np.ceil((xmax - xmin) / cell)) + 2 * margin_cells + 1
    height = int(np.ceil((ymax - ymin) / cell)) + 2 * margin_cells + 1
    return width * height


def bounds_of_tracks(tracks):
    """Общие границы (xmin, ymin, xmax, ymax) по списку треков (Nx2)."""
    xs_min = ys_min = np.inf
    xs_max = ys_max = -np.inf
    for tr in tracks:
        tr = np.asarray(tr, dtype=float)
        if len(tr) == 0:
            continue
        xs_min = min(xs_min, tr[:, 0].min())
        ys_min = min(ys_min, tr[:, 1].min())
        xs_max = max(xs_max, tr[:, 0].max())
        ys_max = max(ys_max, tr[:, 1].max())
    if not np.isfinite(xs_min):
        raise ValueError('No points in tracks')
    return float(xs_min), float(ys_min), float(xs_max), float(ys_max)


def build_density(tracks, cell, bounds=None, margin_cells=3, count_mode='tracks'):
    """Построить сырую поверхность плотности из треков.

    Args:
        tracks: список массивов (Ni, 2) в метрах (эквидистантный ресэмпл).
        cell: размер ячейки τ, метры.
        bounds: (xmin, ymin, xmax, ymax) или None (вычислить по данным).
        count_mode:
            'tracks' — каждый трек добавляет +1 в каждую пройденную ячейку
                       (число треков через ячейку; ближе к Guo);
            'points' — бинниг всех точек (число точек в ячейке).

    Returns:
        Grid с заполненным values.
    """
    if bounds is None:
        bounds = bounds_of_tracks(tracks)
    grid = Grid.from_bounds(*bounds, cell=cell, margin_cells=margin_cells)
    acc = grid.values
    H, W = acc.shape

    for tr in tracks:
        tr = np.asarray(tr, dtype=float)
        if len(tr) == 0:
            continue
        px, py = grid.world_to_pixel(tr[:, 0], tr[:, 1])
        ix = np.floor(px).astype(np.intp)
        iy = np.floor(py).astype(np.intp)
        inside = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
        ix, iy = ix[inside], iy[inside]
        if len(ix) == 0:
            continue
        if count_mode == 'tracks':
            # уникальные ячейки трека → +1 (число треков через ячейку)
            flat = np.unique(iy * W + ix)
            np.add.at(acc.reshape(-1), flat, 1.0)
        else:
            np.add.at(acc, (iy, ix), 1.0)
    return grid
