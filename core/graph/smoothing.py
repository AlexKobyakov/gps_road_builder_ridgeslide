# -*- coding: utf-8 -*-
"""
Polyline smoothing for road edges (WS-Smooth).
Сглаживание «ступенек» растрового скелета (8-связность даёт 45°/90° зигзаги,
которых почти не бывает у реальных дорог). Алгоритм Chaikin (corner-cutting):
каждый внутренний угол срезается двумя точками (1/4 и 3/4 сегмента); за несколько
итераций линия становится плавной. Концы рёбер (узлы графа) ФИКСИРУЮТСЯ, чтобы не
рвать топологию — сглаживается только «тело» ребра.

Чистый numpy — тестируется без QGIS.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

from . import simplify as simplify_mod


def chaikin(coords, iterations=2, keep_ends=True):
    """Сгладить полилинию углорезкой Chaikin.

    Args:
        coords: (N, 2) массив точек.
        iterations: число проходов (0 = без изменений).
        keep_ends: сохранять первую и последнюю точки на месте.

    Returns:
        (M, 2) сглаженная полилиния.
    """
    pts = np.asarray(coords, dtype=float)
    if iterations <= 0 or len(pts) < 3:
        return pts.copy()
    for _ in range(int(iterations)):
        p = pts
        q = 0.75 * p[:-1] + 0.25 * p[1:]      # точки 1/4 каждого сегмента
        r = 0.25 * p[:-1] + 0.75 * p[1:]      # точки 3/4 каждого сегмента
        newpts = np.empty((2 * len(q), 2), dtype=float)
        newpts[0::2] = q
        newpts[1::2] = r
        if keep_ends:
            newpts = np.vstack([p[0], newpts, p[-1]])
        pts = newpts
    return pts


def smooth_graph(graph, iterations=2):
    """Сгладить геометрию всех рёбер графа Chaikin, пересчитать длину.

    Концы рёбер фиксируются (keep_ends). Работает по ключу 'coords' (мировые
    координаты) — вызывать ДО перевода в lon/lat. Возвращает граф (на месте).
    """
    if iterations <= 0:
        return graph
    for edge in graph.edges:
        coords = edge.get('coords')
        if coords is None or len(coords) < 3:
            continue
        smoothed = chaikin(coords, iterations=iterations, keep_ends=True)
        edge['coords'] = smoothed
        edge['length'] = simplify_mod.polyline_length(smoothed)
    return graph
