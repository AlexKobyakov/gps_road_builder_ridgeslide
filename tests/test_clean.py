# -*- coding: utf-8 -*-
"""Offline tests for preprocess.clean."""

import pandas as pd

from gps_road_builder.core.preprocess import clean
from gps_road_builder.core.io import schema


def _df(rows):
    return pd.DataFrame(
        rows, columns=[schema.DEVICE, schema.TIME, schema.LAT, schema.LON])


def test_haversine_one_degree_lat():
    # 1° of latitude ≈ 111.19 km
    d = float(clean.haversine_m(0.0, 0.0, 1.0, 0.0))
    assert abs(d - 111195.0) < 250.0


def test_haversine_zero():
    assert float(clean.haversine_m(45.0, 130.0, 45.0, 130.0)) == 0.0


def test_deduplicate():
    t = pd.Timestamp('2025-01-01 00:00:00')
    df = _df([
        ['a', t, 45.0, 130.0],
        ['a', t, 45.0, 130.0],                       # exact duplicate
        ['a', t + pd.Timedelta(seconds=1), 45.1, 130.1],
    ])
    out = clean.deduplicate(df)
    assert len(out) == 2


def test_drop_invalid():
    t = pd.Timestamp('2025-01-01')
    df = _df([
        ['a', t, 45.0, 130.0],
        ['a', t, 200.0, 130.0],   # bad lat
        ['a', t, 45.0, 999.0],    # bad lon
    ])
    assert len(clean.drop_invalid(df)) == 1


def test_speed_filter_removes_teleport():
    t = pd.Timestamp('2025-01-01 00:00:00')
    df = _df([
        ['a', t, 45.0, 130.0],
        ['a', t + pd.Timedelta(seconds=1), 45.1, 130.0],  # ~11 km in 1 s
    ])
    out, removed = clean.speed_filter(df, v_max_kmh=70.0, a_max=None)
    assert removed == 1
    assert len(out) == 1


def test_speed_filter_removes_zero_dt_teleport():
    # Same timestamp, different location → infinite speed → must be removed.
    t = pd.Timestamp('2025-01-01 00:00:00')
    df = _df([
        ['a', t, 45.0, 130.0],
        ['a', t, 45.5, 130.5],
    ])
    out, removed = clean.speed_filter(df, v_max_kmh=70.0, a_max=None)
    assert removed == 1
    assert len(out) == 1


def test_speed_filter_keeps_plausible():
    t = pd.Timestamp('2025-01-01 00:00:00')
    # ~11 m between points in 1 s ≈ 40 km/h → plausible
    df = _df([
        ['a', t, 45.0, 130.0],
        ['a', t + pd.Timedelta(seconds=1), 45.0001, 130.0],
    ])
    out, removed = clean.speed_filter(df, v_max_kmh=70.0, a_max=None)
    assert removed == 0
    assert len(out) == 2


def test_clean_pipeline_stats():
    t = pd.Timestamp('2025-01-01 00:00:00')
    df = _df([
        ['a', t, 45.0, 130.0],
        ['a', t, 45.0, 130.0],       # duplicate
        ['a', t, 200.0, 0.0],        # invalid lat
    ])
    out, stats = clean.clean(df)
    assert stats['input'] == 3
    assert stats['invalid_removed'] == 1
    assert stats['duplicates_removed'] == 1
    assert stats['output'] == 1


def test_reb_filter_removes_teleport_over_120():
    t = pd.Timestamp('2025-01-01 00:00:00')
    df = _df([
        ['a', t, 45.0, 130.0],
        ['a', t + pd.Timedelta(seconds=1), 45.1, 130.0],  # ~11 km in 1 s
    ])
    out, removed = clean.reb_filter(df)
    assert removed == 1
    assert len(out) == 1


def test_reb_filter_removes_abc_spike():
    # A→B→C: B flies ~1.5 km away and C returns near A. B is a spoof spike.
    t = pd.Timestamp('2025-01-01 00:00:00')
    df = _df([
        ['a', t, 45.0, 130.0],                               # A
        ['a', t + pd.Timedelta(minutes=30), 45.02, 130.0],   # B (~2.2 km away)
        ['a', t + pd.Timedelta(minutes=60), 45.0001, 130.0],  # C (~11 m from A)
    ])
    out, removed = clean.reb_filter(df)
    assert removed == 1
    # the surviving points are A and C (near each other)
    assert len(out) == 2


def test_reb_filter_keeps_normal_track():
    t = pd.Timestamp('2025-01-01 00:00:00')
    # steady ~40 km/h motion, ~11 m/s
    rows = [['a', t + pd.Timedelta(seconds=i), 45.0 + i * 0.0001, 130.0]
            for i in range(5)]
    out, removed = clean.reb_filter(_df(rows))
    assert removed == 0
    assert len(out) == 5


def test_clean_with_reb_flag_reports_stats():
    t = pd.Timestamp('2025-01-01 00:00:00')
    df = _df([
        ['a', t, 45.0, 130.0],
        ['a', t + pd.Timedelta(seconds=1), 45.1, 130.0],   # teleport
    ])
    _out, stats = clean.clean(df, reb=True)
    assert 'reb_removed' in stats
