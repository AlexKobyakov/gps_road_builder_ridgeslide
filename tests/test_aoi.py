# -*- coding: utf-8 -*-
"""Offline tests for AOI clipping (WS-AOI)."""

import numpy as np
import pandas as pd

from gps_road_builder.core.preprocess import aoi
from gps_road_builder.core.io import schema


def _square(x0, y0, x1, y1):
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]])


def test_points_in_polygon_square():
    ring = _square(0, 0, 10, 10)
    lon = np.array([5.0, 15.0, -1.0, 9.9])
    lat = np.array([5.0, 5.0, 5.0, 9.9])
    mask = aoi.points_in_polygon(lon, lat, [ring])
    assert list(mask) == [True, False, False, True]


def test_points_in_polygon_with_hole():
    outer = _square(0, 0, 10, 10)
    hole = _square(4, 4, 6, 6)
    lon = np.array([5.0, 1.0])     # (5,5) is inside the hole → outside AOI
    lat = np.array([5.0, 1.0])
    mask = aoi.points_in_polygon(lon, lat, [outer, hole])
    assert list(mask) == [False, True]


def test_clip_points_filters_df():
    ring = _square(0, 0, 10, 10)
    df = pd.DataFrame(
        [['a', pd.Timestamp('2025-01-01'), 5.0, 5.0],     # inside
         ['a', pd.Timestamp('2025-01-01'), 50.0, 50.0]],  # outside (sea)
        columns=[schema.DEVICE, schema.TIME, schema.LAT, schema.LON])
    out, removed = aoi.clip_points(df, [ring])
    assert removed == 1
    assert len(out) == 1
    assert out.iloc[0][schema.LON] == 5.0


def test_clip_points_no_polygon_is_noop():
    df = pd.DataFrame(
        [['a', pd.Timestamp('2025-01-01'), 5.0, 5.0]],
        columns=[schema.DEVICE, schema.TIME, schema.LAT, schema.LON])
    out, removed = aoi.clip_points(df, None)
    assert removed == 0 and len(out) == 1
