# -*- coding: utf-8 -*-
"""Offline tests for checkpointing, preset save/load, and pipeline resume."""

import numpy as np
import pandas as pd

from gps_road_builder.core import checkpoint, presets
from gps_road_builder.core.io import schema


def _df():
    t = pd.Timestamp('2025-01-01')
    return pd.DataFrame(
        [['a', t, 45.0, 130.0], ['a', t + pd.Timedelta(seconds=1), 45.1, 130.1]],
        columns=[schema.DEVICE, schema.TIME, schema.LAT, schema.LON])


def test_points_checkpoint_roundtrip(tmp_path):
    cache = str(tmp_path)
    assert not checkpoint.has_points(cache)
    checkpoint.save_points(cache, _df(), {'clean_stats': {'input': 2},
                                          'near_dup_removed': 3})
    assert checkpoint.has_points(cache)
    df2, meta = checkpoint.load_points(cache)
    assert len(df2) == 2
    assert meta['near_dup_removed'] == 3
    assert meta['clean_stats']['input'] == 2


def test_tracks_checkpoint_roundtrip(tmp_path):
    cache = str(tmp_path)
    tracks = [np.array([[0.0, 0.0], [1.0, 1.0]]),
              np.array([[2.0, 2.0], [3.0, 3.0], [4.0, 4.0]])]
    proj4 = '+proj=tmerc +lon_0=134 +datum=WGS84 +units=m +no_defs'
    checkpoint.save_tracks(cache, tracks, proj4, {'near_dup_removed': 1})
    assert checkpoint.has_tracks(cache)
    loaded, p4, meta = checkpoint.load_tracks(cache)
    assert p4 == proj4
    assert len(loaded) == 2
    assert np.allclose(loaded[1], tracks[1])


def test_preset_save_load_roundtrip(tmp_path):
    path = str(tmp_path / 'my.json')
    values = {'cell_tau': 7.0, 'method': 'kde', 'weights': (0.5, 0.2, 0.1, 0.7)}
    presets.save_preset(path, values)
    loaded = presets.load_preset(path)
    assert loaded['cell_tau'] == 7.0
    assert loaded['method'] == 'kde'
    assert loaded['weights'] == [0.5, 0.2, 0.1, 0.7]   # tuple → list in JSON
