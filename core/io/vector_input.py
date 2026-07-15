# -*- coding: utf-8 -*-
"""
Vector input helpers for GPS Road Builder (§WS-Input, ADD3 #12).
Чистые (без QGIS) помощники для сборки нормализованного набора точек из
координат/устройств/времени, полученных из векторного слоя или файла GPX/KML/SHP.
Обвязка QGIS (обход геометрии, трансформация CRS) — в `gui/layers.py`; здесь —
только табличная нормализация и синтез времени, чтобы это тестировалось офлайн.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

from . import schema

# База отсчёта для синтетического времени (когда у слоя нет колонки времени).
_TIME_BASE = np.datetime64('2000-01-01T00:00:00')


def synthesize_times(devices, step_s=1.0):
    """Синтетические монотонные метки времени внутри каждого устройства.

    Точки одного устройства идут подряд (как при обходе объектов слоя): каждой
    присваивается base + i·step_s, где i — индекс внутри непрерывного блока
    устройства. Так сегментация по времени не даёт ложных разрывов, а скорость
    конечна.

    Args:
        devices: последовательность идентификаторов устройств, выровненная с
            точками (в порядке следования).
        step_s: шаг, секунды.

    Returns:
        np.ndarray datetime64[s] той же длины.
    """
    dev = np.asarray(devices)
    n = len(dev)
    if n == 0:
        return np.array([], dtype='datetime64[s]')
    # индекс внутри непрерывного блока одного устройства
    idx = np.zeros(n, dtype=np.int64)
    start = 0
    for i in range(1, n):
        if dev[i] != dev[i - 1]:
            start = i
        idx[i] = i - start
    secs = (idx * float(step_s)).astype('timedelta64[s]')
    return _TIME_BASE + secs


def to_dataframe(devices, lats, lons, times=None):
    """Собрать нормализованный DataFrame (device/time/lat/lon).

    Невалидные координаты отбрасываются. Если times=None — синтезируются.

    Returns:
        pandas.DataFrame с каноническими колонками schema.
    """
    import pandas as pd

    devices = np.asarray(devices)
    lats = np.asarray(lats, dtype=float)
    lons = np.asarray(lons, dtype=float)
    if times is None:
        times = synthesize_times(devices)
    else:
        parsed = pd.to_datetime(pd.Series(list(times)), errors='coerce')
        # если разбор времени дал пропуски — синтезируем (устойчиво к формату)
        times = (synthesize_times(devices) if parsed.isna().any()
                 else parsed.to_numpy())

    valid = (np.isfinite(lats) & np.isfinite(lons)
             & (lats >= schema.LAT_MIN) & (lats <= schema.LAT_MAX)
             & (lons >= schema.LON_MIN) & (lons <= schema.LON_MAX))
    df = pd.DataFrame({
        schema.DEVICE: [str(d) for d in devices[valid]],
        schema.TIME: pd.to_datetime(times[valid]),
        schema.LAT: lats[valid],
        schema.LON: lons[valid],
    })
    return df.reset_index(drop=True)


def detect_device_time_fields(field_names):
    """Найти в именах полей слоя роли device/time (по алиасам schema).

    Returns:
        (device_field | None, time_field | None).
    """
    mapping = schema.detect_columns(field_names)
    return mapping.get(schema.DEVICE), mapping.get(schema.TIME)
