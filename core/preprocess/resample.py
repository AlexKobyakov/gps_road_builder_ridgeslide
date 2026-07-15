# -*- coding: utf-8 -*-
"""
Equidistant polyline resampling for GPS Road Builder.
Ресэмплинг полилинии эквидистантными точками (требование Slide, §4.0). Работает
в МЕТРИЧЕСКИХ координатах (после проекции в рабочий кадр, §4.6).

Метод: линейная хордовая аппроксимация — точки ставятся на равном расстоянии
вдоль исходной полилинии; концы сохраняются.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np


def polyline_length(xy):
    """Суммарная длина полилинии (Nx2, метры)."""
    xy = np.asarray(xy, dtype=float)
    if len(xy) < 2:
        return 0.0
    seg = np.diff(xy, axis=0)
    return float(np.hypot(seg[:, 0], seg[:, 1]).sum())


def resample_polyline(xy, step):
    """Ресэмплировать полилинию эквидистантными точками с шагом `step`.

    Args:
        xy: массив (N, 2) координат в метрах.
        step: желаемое расстояние между соседними точками (метры), > 0.

    Returns:
        массив (M, 2). Первая и последняя точки совпадают с исходными.
        Вырожденные случаи: < 2 точек — возвращается копия; нулевая длина —
        одна точка.
    """
    xy = np.asarray(xy, dtype=float)
    if step <= 0:
        raise ValueError('step must be positive')
    if len(xy) < 2:
        return xy.copy()

    seg = np.diff(xy, axis=0)
    seglen = np.hypot(seg[:, 0], seg[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(seglen)])
    total = cum[-1]
    if total == 0.0:
        return xy[:1].copy()

    n = max(1, int(round(total / float(step))))
    targets = np.linspace(0.0, total, n + 1)
    x = np.interp(targets, cum, xy[:, 0])
    y = np.interp(targets, cum, xy[:, 1])
    return np.column_stack([x, y])


def is_equidistant(xy, tol=1e-6):
    """Проверка эквидистантности (для тестов): все шаги равны в пределах tol."""
    xy = np.asarray(xy, dtype=float)
    if len(xy) < 3:
        return True
    seg = np.diff(xy, axis=0)
    lengths = np.hypot(seg[:, 0], seg[:, 1])
    return bool(np.ptp(lengths) <= tol * max(1.0, lengths.mean()))
