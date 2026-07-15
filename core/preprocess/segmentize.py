# -*- coding: utf-8 -*-
"""
Track segmentation for GPS Road Builder.
Разбиение треков устройства на под-треки по временным/пространственным гэпам
(потеря сигнала под пологом леса, §4.0). Гэп → новый под-трек.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

from ..io import schema
from .clean import haversine_m

# Имя колонки с идентификатором под-трека.
TRACK_ID = 'track_id'


def assign_segments(df, gap_dt_s=300.0, gap_ds_m=500.0):
    """Добавить колонку track_id, разрезая треки по гэпам.

    Внутри каждого устройства (сортировка по времени) начинается новый под-трек,
    если интервал времени > gap_dt_s ИЛИ смещение > gap_ds_m.

    Returns:
        DataFrame с добавленной колонкой TRACK_ID вида "<device>#<seg>".
    """
    import pandas as pd

    if df.empty:
        out = df.copy()
        out[TRACK_ID] = pd.Series(dtype=str)
        return out

    parts = []
    for device, sub in df.groupby(schema.DEVICE, sort=False):
        sub = sub.sort_values(schema.TIME).copy()
        lat = sub[schema.LAT].to_numpy(dtype=float)
        lon = sub[schema.LON].to_numpy(dtype=float)
        times = sub[schema.TIME].to_numpy()

        seg = np.zeros(len(sub), dtype=int)
        if len(sub) > 1:
            dt = (times[1:] - times[:-1]) / np.timedelta64(1, 's')
            ds = haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:])
            new_seg = (dt > float(gap_dt_s)) | (ds > float(gap_ds_m))
            seg[1:] = np.cumsum(new_seg.astype(int))

        sub[TRACK_ID] = ['{0}#{1}'.format(device, s) for s in seg]
        parts.append(sub)

    result = pd.concat(parts, ignore_index=True)
    return result


def iter_tracks(df):
    """Итерировать под-треки как (track_id, sub_df), упорядоченные по времени.

    Требует, чтобы assign_segments уже был применён (наличие колонки TRACK_ID).
    """
    if TRACK_ID not in df.columns:
        raise KeyError('assign_segments() must be called before iter_tracks()')
    for track_id, sub in df.groupby(TRACK_ID, sort=True):
        yield track_id, sub.sort_values(schema.TIME).reset_index(drop=True)


def track_count(df):
    """Число под-треков после сегментации."""
    if TRACK_ID not in df.columns or df.empty:
        return 0
    return int(df[TRACK_ID].nunique())
