# -*- coding: utf-8 -*-
"""Offline tests for vector-layer input helpers (WS-Input, ADD3 #12)."""

import numpy as np

from gps_road_builder.core.io import vector_input, schema


def test_synthesize_times_monotonic_per_device():
    dev = ['a', 'a', 'a', 'b', 'b']
    t = vector_input.synthesize_times(dev, step_s=1.0)
    assert len(t) == 5
    # within device 'a': +1 s each; device 'b' restarts at base
    da = (t[1] - t[0]) / np.timedelta64(1, 's')
    assert da == 1.0
    assert t[3] == t[0]                 # 'b' first point == base (same as 'a' first)
    assert (t[4] - t[3]) / np.timedelta64(1, 's') == 1.0


def test_synthesize_times_empty():
    assert len(vector_input.synthesize_times([])) == 0


def test_to_dataframe_synthesizes_time_and_drops_invalid():
    dev = ['a', 'a', 'a']
    lats = [45.0, 200.0, 45.1]          # 200 is invalid latitude → dropped
    lons = [130.0, 130.0, 130.1]
    df = vector_input.to_dataframe(dev, lats, lons)
    assert list(df.columns) == list(schema.CANONICAL_COLUMNS)
    assert len(df) == 2
    assert df[schema.TIME].notna().all()
    assert df[schema.DEVICE].iloc[0] == 'a'


def test_to_dataframe_parses_given_times():
    dev = ['x', 'x']
    df = vector_input.to_dataframe(
        dev, [45.0, 45.1], [130.0, 130.1],
        times=['2025-01-01 00:00:00', '2025-01-01 00:00:05'])
    assert (df[schema.TIME].iloc[1] - df[schema.TIME].iloc[0]).seconds == 5


def test_to_dataframe_bad_times_fall_back_to_synth():
    dev = ['x', 'x']
    df = vector_input.to_dataframe(
        dev, [45.0, 45.1], [130.0, 130.1], times=['nonsense', 'also bad'])
    assert df[schema.TIME].notna().all()        # synthesized, not NaT


def test_detect_device_time_fields():
    dev, tm = vector_input.detect_device_time_fields(
        ['track_fid', 'time', 'ele', 'name'])
    assert dev == 'track_fid'
    assert tm == 'time'
    dev2, tm2 = vector_input.detect_device_time_fields(['a', 'b'])
    assert dev2 is None and tm2 is None
