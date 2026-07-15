# -*- coding: utf-8 -*-
"""
Near-duplicate point thinning for GPS Road Builder.
Прореживание близких точек: точка отбрасывается, если она ближе `min_dist_m` к
последней СОХРАНЁННОЙ точке того же устройства (greedy, как в методике ФГИС ЛК).

Для разрежённых данных ФГИС ЛК (фикс каждые 15 мин / 5 км) с плотными кластерами
это резко сокращает объём (в записке 46.8 млн → существенно меньше) и ускоряет
весь конвейер.

Бэкенды: numba (greedy, C-скорость) при наличии; иначе — векторный
consecutive-distance приблизительный фолбэк.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

from ..io import schema

EARTH_RADIUS_M = 6371008.8

try:
    from numba import njit
    _HAVE_NUMBA = True
except Exception:  # pragma: no cover - numba опциональна
    _HAVE_NUMBA = False


if _HAVE_NUMBA:
    import math

    @njit(cache=True, fastmath=True)
    def _thin_greedy_nb(lat, lon, dev_codes, min_dist):
        n = lat.shape[0]
        keep = np.zeros(n, dtype=np.bool_)
        if n == 0:
            return keep
        cur_dev = -1
        last_lat = 0.0
        last_lon = 0.0
        for i in range(n):
            if dev_codes[i] != cur_dev:
                cur_dev = dev_codes[i]
                keep[i] = True
                last_lat = lat[i]
                last_lon = lon[i]
                continue
            phi1 = math.radians(last_lat)
            phi2 = math.radians(lat[i])
            dphi = phi2 - phi1
            dl = math.radians(lon[i]) - math.radians(last_lon)
            a = (math.sin(dphi / 2.0) ** 2
                 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2.0) ** 2)
            d = 2.0 * EARTH_RADIUS_M * math.asin(math.sqrt(min(1.0, a)))
            if d >= min_dist:
                keep[i] = True
                last_lat = lat[i]
                last_lon = lon[i]
        return keep


def _thin_consecutive_np(lat, lon, dev_codes, min_dist):
    """Векторный приблизительный фолбэк: отбрасывает точку, если она ближе
    min_dist к ПРЕДЫДУЩЕЙ точке того же устройства (не к последней сохранённой)."""
    n = lat.shape[0]
    keep = np.ones(n, dtype=bool)
    if n < 2:
        return keep
    lat1 = np.radians(lat[:-1])
    lat2 = np.radians(lat[1:])
    dphi = lat2 - lat1
    dl = np.radians(lon[1:]) - np.radians(lon[:-1])
    a = np.sin(dphi / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dl / 2.0) ** 2
    dist = 2.0 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    same_dev = dev_codes[1:] == dev_codes[:-1]
    drop = np.zeros(n, dtype=bool)
    drop[1:] = same_dev & (dist < min_dist)
    keep[drop] = False
    return keep


def thin_near_duplicates(df, min_dist_m=10.0, backend='auto'):
    """Проредить близкие точки (в пределах min_dist_m) по каждому устройству.

    Требует, чтобы df был отсортирован по (device, time) — как после
    clean.deduplicate. min_dist_m <= 0 отключает прореживание.

    Returns:
        (thinned_df, removed_count)
    """
    if min_dist_m is None or min_dist_m <= 0 or df.empty:
        return df.reset_index(drop=True), 0

    lat = df[schema.LAT].to_numpy(dtype=float)
    lon = df[schema.LON].to_numpy(dtype=float)
    dev_codes = df[schema.DEVICE].astype('category').cat.codes.to_numpy()

    use_numba = (backend == 'numba') or (backend == 'auto' and _HAVE_NUMBA)
    if backend == 'numba' and not _HAVE_NUMBA:
        raise RuntimeError('numba backend requested but numba is not available')

    if use_numba:
        keep = _thin_greedy_nb(lat, lon, dev_codes.astype(np.int64),
                               float(min_dist_m))
    else:
        keep = _thin_consecutive_np(lat, lon, dev_codes, float(min_dist_m))

    keep = np.asarray(keep, dtype=bool)
    removed = int((~keep).sum())
    return df[keep].reset_index(drop=True), removed
