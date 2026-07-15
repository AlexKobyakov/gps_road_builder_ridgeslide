# -*- coding: utf-8 -*-
"""
Edge geometry simplification (Guo 2020 §3.4).
Перевод пиксельных путей рёбер в мировые координаты и упрощение
Douglas–Peucker с допуском в метрах. Чистый numpy.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np


def rdp(points, epsilon):
    """Упрощение полилинии Рамера–Дугласа–Пекера (итеративно, без рекурсии).

    Args:
        points: (N, 2) массив.
        epsilon: допуск (в тех же единицах, что и координаты).

    Returns:
        (M, 2) упрощённая полилиния (концы сохраняются).
    """
    pts = np.asarray(points, dtype=float)
    n = len(pts)
    if n < 3:
        return pts.copy()
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue
        a = pts[start]
        b = pts[end]
        seg = b - a
        seg_len = np.hypot(seg[0], seg[1])
        chunk = pts[start + 1:end]
        if seg_len < 1e-12:
            dist = np.hypot(chunk[:, 0] - a[0], chunk[:, 1] - a[1])
        else:
            # перпендикулярное расстояние до прямой ab
            dist = np.abs(seg[0] * (a[1] - chunk[:, 1])
                          - (a[0] - chunk[:, 0]) * seg[1]) / seg_len
        idx = int(np.argmax(dist))
        if dist[idx] > epsilon:
            split = start + 1 + idx
            keep[split] = True
            stack.append((start, split))
            stack.append((split, end))
    return pts[keep]


def pixels_to_world(pixels, grid):
    """Пиксельный путь (row, col) → мировые координаты (x, y) центров ячеек."""
    pixels = np.asarray(pixels, dtype=float)
    x = grid.ox + (pixels[:, 1] + 0.5) * grid.cell
    y = grid.oy + (pixels[:, 0] + 0.5) * grid.cell
    return np.column_stack([x, y])


def polyline_length(coords):
    coords = np.asarray(coords, dtype=float)
    if len(coords) < 2:
        return 0.0
    seg = np.diff(coords, axis=0)
    return float(np.hypot(seg[:, 0], seg[:, 1]).sum())


def simplify_graph(graph, grid, epsilon_m=2.0):
    """Добавить рёбрам мировую геометрию 'coords' и 'length' (упрощённо)."""
    for edge in graph.edges:
        world = pixels_to_world(edge['pixels'], grid)
        simplified = rdp(world, epsilon_m)
        edge['coords'] = simplified
        edge['length'] = polyline_length(simplified)
    return graph
