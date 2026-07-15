# -*- coding: utf-8 -*-
"""Offline tests for density.projection (CRS math + pyproj Projector)."""

import numpy as np
import pytest

from gps_road_builder.core.density import projection as prj


def test_circular_mean_simple():
    assert abs(prj.circular_mean_deg([130.0, 140.0]) - 135.0) < 1e-6


def test_circular_mean_antimeridian():
    m = prj.circular_mean_deg([179.0, -179.0])
    assert abs(abs(m) - 180.0) < 1e-6


def test_covering_arc_normal():
    span, crosses = prj._covering_arc([131.0, 132.0, 138.0])
    assert abs(span - 7.0) < 1e-6
    assert not crosses


def test_covering_arc_antimeridian():
    span, crosses = prj._covering_arc([179.0, -179.0])
    assert crosses
    assert span < 5.0


def test_data_extent_primorye():
    ext = prj.data_extent([131.0, 133.0, 135.0, 138.0], [42.0, 44.0, 46.0, 47.0])
    assert 133.0 < ext['center_lon'] < 136.0
    assert not ext['crosses_antimeridian']
    assert abs(ext['lon_span'] - 7.0) < 1e-6


def test_choose_crs_midlat_is_tmerc():
    proj4, meta = prj.choose_working_crs([131.0, 138.0], [44.0, 46.0])
    assert meta['kind'] == 'tmerc'
    assert '+proj=tmerc' in proj4
    assert '+lon_0=' in proj4


def test_choose_crs_polar_is_aeqd():
    proj4, meta = prj.choose_working_crs([10.0, 12.0], [85.0, 86.0])
    assert meta['kind'] == 'aeqd'
    assert '+proj=aeqd' in proj4


pyproj = pytest.importorskip('pyproj')


def test_projector_roundtrip():
    lons = np.array([131.0, 134.5, 138.0])
    lats = np.array([43.0, 45.0, 47.0])
    p = prj.Projector.for_data(lons, lats)
    x, y = p.forward(lons, lats)
    lon2, lat2 = p.inverse(x, y)
    assert np.allclose(lon2, lons, atol=1e-6)
    assert np.allclose(lat2, lats, atol=1e-6)


def test_projector_central_meridian_maps_to_zero_x():
    lons = np.array([134.0, 136.0])
    lats = np.array([45.0, 45.0])
    p = prj.Projector.for_data(lons, lats)
    x, _y = p.forward(p.meta['center_lon'], 45.0)
    assert abs(float(x)) < 1e-3


def test_projector_metric_distance_matches_haversine():
    # Two nearby points; projected planar distance ≈ geodesic distance.
    from gps_road_builder.core.preprocess.clean import haversine_m
    lons = np.array([134.0, 134.01])
    lats = np.array([45.0, 45.0])
    p = prj.Projector.for_data(lons, lats)
    x, y = p.forward(lons, lats)
    planar = float(np.hypot(x[1] - x[0], y[1] - y[0]))
    geo = float(haversine_m(lats[0], lons[0], lats[1], lons[1]))
    assert abs(planar - geo) / geo < 0.01
