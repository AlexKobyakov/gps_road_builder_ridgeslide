# -*- coding: utf-8 -*-
"""
Binarization of the density surface (Guo 2020 §3.4).
Порог ε → бинарная маска дорог. Порог задаётся вручную или автоматически (Otsu).
Чистый numpy.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np


def otsu_threshold(values, bins=256):
    """Порог Оцу по ненулевым значениям поверхности.

    Возвращает порог, максимизирующий межклассовую дисперсию. Ноли (фон)
    исключаются, чтобы порог считался по «занятым» ячейкам.
    """
    v = np.asarray(values, dtype=float).ravel()
    v = v[v > 0]
    if v.size == 0:
        return 0.0
    vmax = float(v.max())
    if vmax <= 0:
        return 0.0
    hist, edges = np.histogram(v, bins=bins, range=(0.0, vmax))
    hist = hist.astype(float)
    total = hist.sum()
    if total == 0:
        return 0.0
    centers = (edges[:-1] + edges[1:]) / 2.0
    w0 = np.cumsum(hist)
    w1 = total - w0
    sum_total = np.cumsum(hist * centers)
    mean_total = sum_total[-1]
    with np.errstate(divide='ignore', invalid='ignore'):
        mu0 = sum_total / w0
        mu1 = (mean_total - sum_total) / w1
        between = w0 * w1 * (mu0 - mu1) ** 2
    between[~np.isfinite(between)] = 0.0
    idx = int(np.argmax(between))
    return float(centers[idx])


def percentile_threshold(values, pct):
    """Порог по перцентилю НЕНУЛЕВЫХ значений поверхности.

    Устойчивее Otsu на сильно скошенных KDE-поверхностях, где Otsu режет выше
    дорожных коридоров (оставляет только горячие пятна). pct — доля «занятых»
    ячеек ниже порога (80 → оставить верхние 20% плотности).
    """
    v = np.asarray(values, dtype=float).ravel()
    v = v[v > 0]
    if v.size == 0:
        return 0.0
    return float(np.percentile(v, float(np.clip(pct, 0.0, 100.0))))


def fill_small_holes(mask, max_area):
    """Заполнить мелкие дыры в маске (< max_area пикселей).

    Дыры в толстой маске KDE после скелетизации превращаются в паразитные
    петли-«перекрестья»; заполнение их убирает. Требует scikit-image; без него —
    возвращает маску как есть.
    """
    if not max_area or max_area <= 0:
        return np.asarray(mask, dtype=bool)
    try:
        from skimage.morphology import remove_small_holes
        return remove_small_holes(np.asarray(mask, dtype=bool),
                                  area_threshold=int(max_area))
    except Exception:
        return np.asarray(mask, dtype=bool)


def close_gaps(mask, radius_px):
    """Буферизация маски дилатацией (мостит разрывы до ~2·radius_px).

    Приём из методики ФГИС ЛК: вокруг «дорожной» маски строится буфер, который
    закрывает разрывы там, где сигналы фиксировались редко. Ширину дилатация
    «раздувает», но последующая скелетизация возвращает ось шириной 1 пиксель,
    поэтому расширение не влияет на итоговую геометрию — только сшивает разрывы.
    """
    r = int(round(radius_px))
    if r <= 0:
        return np.asarray(mask, dtype=bool)
    from scipy.ndimage import (
        binary_dilation, generate_binary_structure, iterate_structure)
    struct = iterate_structure(generate_binary_structure(2, 1), r)
    return binary_dilation(np.asarray(mask, dtype=bool), structure=struct)


def binarize(values, eps=None, method='manual', percentile=80.0):
    """Построить бинарную маску: density > threshold.

    Args:
        values: поверхность плотности (H, W).
        eps: явный порог (для method='manual'); игнорируется иначе.
        method: 'manual' | 'otsu' | 'percentile'.
        percentile: перцентиль для method='percentile' (0..100).

    Returns:
        (mask: bool (H,W), threshold: float)
    """
    values = np.asarray(values, dtype=float)
    if method == 'otsu':
        threshold = otsu_threshold(values)
    elif method == 'percentile':
        threshold = percentile_threshold(values, percentile)
    else:
        if eps is None:
            raise ValueError("manual binarization requires eps")
        threshold = float(eps)
    mask = values > threshold
    return mask, threshold
