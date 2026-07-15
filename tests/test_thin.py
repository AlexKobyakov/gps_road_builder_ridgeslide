# -*- coding: utf-8 -*-
"""Offline tests for preprocess.thin (near-duplicate thinning)."""

import numpy as np
import pandas as pd
import pytest

from gps_road_builder.core.preprocess import thin
from gps_road_builder.core.preprocess.clean import haversine_m
from gps_road_builder.core.io import schema


def _df(rows):
    return pd.DataFrame(
        rows, columns=[schema.DEVICE, schema.TIME, schema.LAT, schema.LON])


def _line(dev, lat0, lon0, step_deg, n):
    t0 = pd.Timestamp('2025-01-01')
    return [[dev, t0 + pd.Timedelta(seconds=i), lat0 + i * step_deg, lon0]
            for i in range(n)]


def test_thin_disabled_returns_all():
    df = _df(_line('a', 45.0, 130.0, 0.001, 5))
    out, removed = thin.thin_near_duplicates(df, min_dist_m=0.0)
    assert removed == 0 and len(out) == 5


def test_thin_consecutive_fallback_reduces():
    # points ~1.1 m apart (1e-5 deg lat); min_dist 10 m → most dropped
    df = _df(_line('a', 45.0, 130.0, 1e-5, 20))
    out, removed = thin.thin_near_duplicates(df, min_dist_m=10.0, backend='numpy')
    assert removed > 0
    assert out[schema.DEVICE].iloc[0] == 'a'
    assert len(out) < 20


def test_thin_keeps_first_of_each_device_numpy():
    df = _df(_line('a', 45.0, 130.0, 1e-6, 3) + _line('b', 46.0, 131.0, 1e-6, 3))
    out, _removed = thin.thin_near_duplicates(df, min_dist_m=50.0, backend='numpy')
    # at least the first point of each device survives
    assert set(out[schema.DEVICE]) == {'a', 'b'}


def test_thin_greedy_numba_matches_spacing():
    pytest.importorskip('numba')
    if not thin._HAVE_NUMBA:
        pytest.skip('numba not available')
    # 40 points 1.1 m apart; greedy keeps ~every 10 m
    df = _df(_line('a', 45.0, 130.0, 1e-5, 40))
    out, removed = thin.thin_near_duplicates(df, min_dist_m=10.0, backend='numba')
    kept = out[[schema.LAT, schema.LON]].to_numpy()
    # consecutive kept points must be >= ~10 m apart (greedy guarantee)
    d = haversine_m(kept[:-1, 0], kept[:-1, 1], kept[1:, 0], kept[1:, 1])
    assert np.all(d >= 9.0)
    assert removed > 0
