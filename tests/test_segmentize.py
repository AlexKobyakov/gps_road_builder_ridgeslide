# -*- coding: utf-8 -*-
"""Offline tests for preprocess.segmentize."""

import pandas as pd

from gps_road_builder.core.preprocess import segmentize as seg
from gps_road_builder.core.io import schema


def _df(rows):
    return pd.DataFrame(
        rows, columns=[schema.DEVICE, schema.TIME, schema.LAT, schema.LON])


def test_time_gap_splits_track():
    t = pd.Timestamp('2025-01-01 00:00:00')
    df = _df([
        ['a', t, 45.0, 130.0000],
        ['a', t + pd.Timedelta(seconds=10), 45.0, 130.0010],
        ['a', t + pd.Timedelta(hours=2), 45.0, 130.0020],   # big time gap
    ])
    out = seg.assign_segments(df, gap_dt_s=300.0, gap_ds_m=500.0)
    ids = out[seg.TRACK_ID].tolist()
    assert ids[0] == ids[1]
    assert ids[1] != ids[2]
    assert seg.track_count(out) == 2


def test_space_gap_splits_track():
    t = pd.Timestamp('2025-01-01 00:00:00')
    df = _df([
        ['a', t, 45.0, 130.0],
        ['a', t + pd.Timedelta(seconds=10), 45.02, 130.0],  # ~2.2 km apart
    ])
    out = seg.assign_segments(df, gap_dt_s=300.0, gap_ds_m=500.0)
    assert seg.track_count(out) == 2


def test_separate_devices_separate_tracks():
    t = pd.Timestamp('2025-01-01 00:00:00')
    df = _df([
        ['a', t, 45.0, 130.0],
        ['b', t, 45.0, 130.0],
    ])
    out = seg.assign_segments(df)
    assert seg.track_count(out) == 2


def test_iter_tracks_requires_assignment():
    df = _df([['a', pd.Timestamp('2025-01-01'), 45.0, 130.0]])
    try:
        list(seg.iter_tracks(df))
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_iter_tracks_yields_sorted():
    t = pd.Timestamp('2025-01-01 00:00:00')
    df = _df([
        ['a', t + pd.Timedelta(seconds=5), 45.0, 130.001],
        ['a', t, 45.0, 130.000],
    ])
    out = seg.assign_segments(df)
    tracks = list(seg.iter_tracks(out))
    assert len(tracks) == 1
    _tid, sub = tracks[0]
    # sorted by time ascending
    assert sub[schema.TIME].iloc[0] < sub[schema.TIME].iloc[1]
