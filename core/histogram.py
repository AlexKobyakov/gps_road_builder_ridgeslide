# -*- coding: utf-8 -*-
"""
Histogram computation for GPS Road Builder (§8.1 calibration UI).
Чистый расчёт гистограммы (без Qt) для подбора порогов f/l и обзора результата.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np


def compute_histogram(values, bins=12, scale='linear'):
    """Гистограмма значений.

    Args:
        values: массив значений.
        bins: число корзин.
        scale: 'linear' — равные корзины; 'log' — логарифмически растянутые
            корзины по неотрицательным данным (значение сдвигается на +1, так
            что 0 попадает в первую корзину). Для сильно скошенных распределений
            (частоты/длины рёбер) 'log' informativнее, чем одна доминирующая
            корзина при линейной шкале.

    Returns:
        (counts, edges): counts (bins,), edges (bins+1,). Пустой вход →
        пустые массивы.
    """
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.zeros(0), np.zeros(0)
    if scale == 'log':
        shifted = v + 1.0                      # 0 → 1 (первая корзина)
        hi = float(shifted.max())
        if hi <= 1.0:
            hi = 2.0
        edges = np.logspace(0.0, np.log10(hi), bins + 1)
        counts, edges = np.histogram(shifted, bins=edges)
        return counts.astype(float), edges - 1.0   # вернуть реальные значения
    vmin = float(v.min())
    vmax = float(v.max())
    if vmax <= vmin:
        vmax = vmin + 1.0
    counts, edges = np.histogram(v, bins=bins, range=(vmin, vmax))
    return counts.astype(float), edges


def summary(values):
    """Краткая сводка распределения (min/median/mean/max/count)."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {'count': 0, 'min': 0.0, 'median': 0.0, 'mean': 0.0, 'max': 0.0}
    return {
        'count': int(v.size),
        'min': float(v.min()),
        'median': float(np.median(v)),
        'mean': float(v.mean()),
        'max': float(v.max()),
    }
