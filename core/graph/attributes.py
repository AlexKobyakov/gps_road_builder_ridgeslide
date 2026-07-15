# -*- coding: utf-8 -*-
"""
Edge attributes for the road network (WS-G / FGIS LK note).
Прикладные атрибуты рёбер:

- `road_class` — категория дороги по интенсивности проездов (частоте), по образцу
  записки ФГИС ЛК: магистраль / улучшенная / обычная / зимняя. Пороги считаются
  по квантилям положительных частот текущего графа (устойчиво к масштабу данных).
- `reconstructed` — флаг «участок дорисован»: ребро без подтверждённого покрытия
  треками (frequency == 0) — геометрия выведена (буфер/скелет между редкими
  фиксами), а не пройдена реально.

Чистый numpy — тестируется без QGIS.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

# Коды классов (магистраль → зимняя). Хранятся как строки — дружелюбно к ГИС.
ROAD_CLASSES = ('main', 'improved', 'ordinary', 'winter')


def class_thresholds(freqs, quantiles=(0.25, 0.5, 0.75)):
    """Пороги (t1, t2, t3) по квантилям положительных частот.

    Возвращает (0, 0, 0), если положительных частот нет.
    """
    f = np.asarray(freqs, dtype=float)
    f = f[np.isfinite(f) & (f > 0)]
    if f.size == 0:
        return 0.0, 0.0, 0.0
    t1, t2, t3 = np.quantile(f, list(quantiles))
    return float(t1), float(t2), float(t3)


def classify(frequency, thresholds):
    """Категория дороги по частоте и порогам (t1, t2, t3)."""
    t1, t2, t3 = thresholds
    if frequency <= 0:
        return 'winter'
    if frequency >= t3:
        return 'main'
    if frequency >= t2:
        return 'improved'
    if frequency >= t1:
        return 'ordinary'
    return 'winter'


def annotate(graph):
    """Проставить рёбрам 'road_class' и 'reconstructed' по частоте.

    Возвращает граф (изменяется на месте).
    """
    freqs = [int(e.get('frequency', 0)) for e in graph.edges]
    thresholds = class_thresholds(freqs)
    for e in graph.edges:
        f = int(e.get('frequency', 0))
        e['road_class'] = classify(f, thresholds)
        e['reconstructed'] = 1 if f <= 0 else 0
    return graph
