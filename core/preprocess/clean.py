# -*- coding: utf-8 -*-
"""
Cleaning of raw GPS points for GPS Road Builder.
Очистка сырых точек: отбраковка невалидных координат, обязательная
дедупликация (§4.0), физический фильтр скорости/ускорения.

`haversine_m` — чистый numpy (тестируется без pandas). Табличные операции
работают на нормализованном DataFrame (device, time, lat, lon).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

from ..io import schema

# Средний радиус Земли (WGS84), метры.
EARTH_RADIUS_M = 6371008.8


def haversine_m(lat1, lon1, lat2, lon2):
    """Геодезическое расстояние (метры) по формуле гаверсинуса. Векторизовано."""
    lat1 = np.radians(np.asarray(lat1, dtype=float))
    lat2 = np.radians(np.asarray(lat2, dtype=float))
    dlat = lat2 - lat1
    dlon = np.radians(np.asarray(lon2, dtype=float)) - \
        np.radians(np.asarray(lon1, dtype=float))
    a = np.sin(dlat / 2.0) ** 2 + \
        np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def drop_invalid(df):
    """Убрать строки с координатами вне допустимого диапазона / NaN."""
    lat = df[schema.LAT].astype(float)
    lon = df[schema.LON].astype(float)
    mask = (
        lat.between(schema.LAT_MIN, schema.LAT_MAX)
        & lon.between(schema.LON_MIN, schema.LON_MAX)
        & df[schema.TIME].notna()
    )
    return df[mask].reset_index(drop=True)


def deduplicate(df):
    """Дедупликация по (device, time, lat, lon) + сортировка (device, time).

    Обязательный шаг: выгрузки заказчика содержат дубли внутри и между файлами
    (§4.0).
    """
    cleaned = df.drop_duplicates(
        subset=[schema.DEVICE, schema.TIME, schema.LAT, schema.LON])
    cleaned = cleaned.sort_values([schema.DEVICE, schema.TIME])
    return cleaned.reset_index(drop=True)


def _consecutive_speed_mps(sub):
    """Скорость (м/с) до предыдущей точки внутри одного устройства."""
    lat = sub[schema.LAT].to_numpy(dtype=float)
    lon = sub[schema.LON].to_numpy(dtype=float)
    times = sub[schema.TIME].to_numpy()
    dist = np.zeros(len(sub))
    dist[1:] = haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:])
    dt = np.zeros(len(sub))
    if len(sub) > 1:
        dt[1:] = (times[1:] - times[:-1]) / np.timedelta64(1, 's')
    speed = np.full(len(sub), np.nan)
    with np.errstate(divide='ignore', invalid='ignore'):
        moving = dt > 0
        speed[moving] = dist[moving] / dt[moving]
        # Нулевой интервал времени при ненулевом смещении = невозможная скорость.
        speed[(dt <= 0) & (dist > 0)] = np.inf
    return speed, dt


def speed_filter(df, v_max_kmh=70.0, a_max=4.0):
    """Убрать точки с невозможной скоростью/ускорением (физфильтр, §4.0).

    Однопроходный фильтр по каждому устройству: точка удаляется, если скорость
    до предыдущей точки превышает v_max либо модуль ускорения превышает a_max.
    Первая точка каждого устройства сохраняется.

    Returns:
        (filtered_df, removed_count)
    """
    if df.empty:
        return df.reset_index(drop=True), 0

    v_max_mps = float(v_max_kmh) / 3.6
    keep_parts = []
    removed = 0

    for _device, sub in df.groupby(schema.DEVICE, sort=False):
        sub = sub.sort_values(schema.TIME)
        speed, dt = _consecutive_speed_mps(sub)

        keep = np.ones(len(sub), dtype=bool)
        # Скоростной порог. Первая точка: speed=NaN → (NaN > v) == False → keep.
        # Телепорт при dt<=0: speed=inf → (inf > v) == True → remove.
        over_speed = speed > v_max_mps
        keep &= ~over_speed

        # Ускорение между последовательными скоростями (NaN → не срабатывает).
        if a_max is not None and len(sub) > 2:
            accel = np.full(len(sub), np.nan)
            with np.errstate(divide='ignore', invalid='ignore'):
                dv = np.diff(speed)
                accel[1:] = dv / np.where(dt[1:] > 0, dt[1:], np.nan)
            over_accel = np.abs(accel) > float(a_max)
            keep &= ~over_accel

        removed += int((~keep).sum())
        keep_parts.append(sub[keep])

    import pandas as pd
    result = pd.concat(keep_parts, ignore_index=True) if keep_parts \
        else df.iloc[0:0]
    result = result.sort_values([schema.DEVICE, schema.TIME])
    return result.reset_index(drop=True), removed


def reb_filter(df, max_speed_kmh=120.0, jump_m=200.0, jump_dt_s=60.0):
    """Anti-spoofing / РЭБ фильтр из записки ФГИС ЛК.

    Удаляет три типа артефактов радиоэлектронной борьбы/спуфинга (по каждому
    устройству, точки отсортированы по времени):
      1. скорость до предыдущей точки > max_speed_kmh (телепорт);
      2. скачок > jump_m метров за < jump_dt_s секунд;
      3. паттерн A→B→C, где B — выброс: dist(A,B) и dist(B,C) велики, а dist(A,C)
         мал (точка «улетела» и вернулась) — удаляется B.

    Returns:
        (filtered_df, removed_count)
    """
    if df.empty:
        return df.reset_index(drop=True), 0

    v_max_mps = float(max_speed_kmh) / 3.6
    keep_parts = []
    removed = 0

    for _device, sub in df.groupby(schema.DEVICE, sort=False):
        sub = sub.sort_values(schema.TIME)
        lat = sub[schema.LAT].to_numpy(dtype=float)
        lon = sub[schema.LON].to_numpy(dtype=float)
        times = sub[schema.TIME].to_numpy()
        n = len(sub)
        keep = np.ones(n, dtype=bool)
        if n >= 2:
            d = np.zeros(n)
            d[1:] = haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:])
            dt = np.zeros(n)
            dt[1:] = (times[1:] - times[:-1]) / np.timedelta64(1, 's')
            with np.errstate(divide='ignore', invalid='ignore'):
                speed = np.where(dt > 0, d / dt, 0.0)
            keep &= ~(speed > v_max_mps)
            keep &= ~((d > jump_m) & (dt > 0) & (dt < jump_dt_s))
            if n >= 3:
                d_ab = d[1:-1]
                d_bc = d[2:]
                d_ac = haversine_m(lat[:-2], lon[:-2], lat[2:], lon[2:])
                spike = (d_ab > jump_m) & (d_bc > jump_m) & (d_ac < jump_m)
                keep[1:-1][spike] = False
        removed += int((~keep).sum())
        keep_parts.append(sub[keep])

    import pandas as pd
    result = pd.concat(keep_parts, ignore_index=True) if keep_parts \
        else df.iloc[0:0]
    result = result.sort_values([schema.DEVICE, schema.TIME])
    return result.reset_index(drop=True), removed


def clean(df, v_max_kmh=70.0, a_max=4.0, reb=False):
    """Полная очистка: диапазон → дедуп → физфильтр → (опц.) REB.

    Returns:
        (clean_df, stats) где stats — dict со счётчиками этапов.
    """
    n0 = len(df)
    df = drop_invalid(df)
    n1 = len(df)
    df = deduplicate(df)
    n2 = len(df)
    df, removed_speed = speed_filter(df, v_max_kmh=v_max_kmh, a_max=a_max)
    removed_reb = 0
    if reb:
        df, removed_reb = reb_filter(df)
    stats = {
        'input': n0,
        'invalid_removed': n0 - n1,
        'duplicates_removed': n1 - n2,
        'speed_removed': removed_speed,
        'reb_removed': removed_reb,
        'output': len(df),
    }
    return df, stats
