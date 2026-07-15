# -*- coding: utf-8 -*-
"""End-to-end offline test of the MVP pipeline on a synthetic '+' network."""

from collections import defaultdict
import math

import numpy as np
import pytest

pytest.importorskip('pandas')
pytest.importorskip('scipy')
pytest.importorskip('pyproj')

import pandas as pd  # noqa: E402

from gps_road_builder.core import pipeline  # noqa: E402
from gps_road_builder.core.io import schema  # noqa: E402

LAT0, LON0 = 45.0, 134.0
_M_PER_DEG_LAT = 111320.0
_M_PER_DEG_LON = 111320.0 * math.cos(math.radians(LAT0))


def _to_lonlat(x, y):
    return LON0 + x / _M_PER_DEG_LON, LAT0 + y / _M_PER_DEG_LAT


def _plus_dataframe(seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    dev = 0
    base = pd.Timestamp('2025-01-01 00:00:00')

    def add_track(points):
        nonlocal dev
        dev += 1
        for i, (x, y) in enumerate(points):
            lon, lat = _to_lonlat(x, y)
            rows.append([str(dev), base + pd.Timedelta(seconds=i * 2),
                         lat, lon])

    steps = np.arange(-100.0, 100.1, 5.0)
    for _ in range(8):                       # horizontal arm
        jit = rng.normal(0.0, 0.8)
        add_track([(x, jit + rng.normal(0, 0.2)) for x in steps])
    for _ in range(8):                       # vertical arm
        jit = rng.normal(0.0, 0.8)
        add_track([(jit + rng.normal(0, 0.2), y) for y in steps])

    return pd.DataFrame(
        rows, columns=[schema.DEVICE, schema.TIME, schema.LAT, schema.LON])


def test_pipeline_builds_plus_graph():
    df = _plus_dataframe()
    params = {
        'cell_tau': 5.0, 'sigma1': 3.0, 'sigma2': 2.0, 'sharpness': 1.0,
        'resample_k': 5.0, 'eps_mode': 'otsu', 'min_point_dist': 0.0,
        'edge_f_min': 1, 'edge_l_min': 0.0, 'protect_long_m': None,
        'slide_min_loops': 0, 'slide_max_loops': 80, 'backend': 'numpy',
    }
    seen = []
    result = pipeline.build_road_graph(
        df, params=params, progress=lambda f, m: seen.append((f, m)))

    assert result is not None
    graph = result['graph']
    assert graph.edge_count() >= 4          # four arms
    deg = defaultdict(int)
    for e in graph.edges:
        deg[e['u']] += 1
        deg[e['v']] += 1
    assert max(deg.values()) >= 3           # central junction

    # geometry reprojected back to lon/lat near the network centre
    for e in graph.edges:
        assert 'coords_lonlat' in e
        ll = e['coords_lonlat']
        assert np.all(np.abs(ll[:, 0] - LON0) < 0.02)
        assert np.all(np.abs(ll[:, 1] - LAT0) < 0.02)

    assert seen and seen[-1][1] == 'done'
    assert result['stats']['edges'] == graph.edge_count()


def test_pipeline_tiled_matches_junction():
    # Split-and-merge (forced 2x2) must still reconstruct the central junction
    # via boundary fixing, and stay connected.
    df = _plus_dataframe()
    params = {
        'cell_tau': 5.0, 'sigma1': 3.0, 'sigma2': 2.0, 'sharpness': 1.0,
        'resample_k': 5.0, 'eps_mode': 'otsu', 'min_point_dist': 0.0,
        'edge_f_min': 1, 'edge_l_min': 0.0, 'protect_long_m': None,
        'slide_min_loops': 0, 'slide_max_loops': 80, 'backend': 'numpy',
        'split_mode': 'forced', 'tile_grid': (2, 2), 'overlap_cells': 15,
    }
    result = pipeline.build_road_graph(df, params=params)
    assert result is not None
    assert result['stats']['tiles'] == 4
    graph = result['graph']
    assert graph.edge_count() >= 4
    deg = defaultdict(int)
    for e in graph.edges:
        deg[e['u']] += 1
        deg[e['v']] += 1
    assert max(deg.values()) >= 3           # junction survived merge


def test_pipeline_kde_method_builds_graph():
    # KDE + buffer method (sparse-data mode) on the same '+' network.
    df = _plus_dataframe()
    params = {
        'method': 'kde', 'cell_tau': 5.0, 'kde_radius': 20.0,
        'gap_buffer_m': 10.0, 'eps_mode': 'otsu', 'min_point_dist': 0.0,
        'edge_f_min': 1, 'edge_l_min': 0.0, 'protect_long_m': None,
        'split_mode': 'off',
    }
    result = pipeline.build_road_graph(df, params=params)
    assert result is not None
    graph = result['graph']
    assert graph.edge_count() >= 3
    for e in graph.edges:
        assert 'coords_lonlat' in e


def test_pipeline_checkpoint_stop_and_resume(tmp_path):
    from gps_road_builder.core import checkpoint
    df = _plus_dataframe()
    cache = str(tmp_path)
    base = {
        'cell_tau': 5.0, 'sigma1': 3.0, 'sigma2': 2.0, 'sharpness': 1.0,
        'resample_k': 5.0, 'eps_mode': 'otsu', 'min_point_dist': 0.0,
        'edge_f_min': 1, 'edge_l_min': 0.0, 'protect_long_m': None,
        'slide_min_loops': 0, 'slide_max_loops': 60, 'backend': 'numpy',
        'split_mode': 'off',
    }

    # stop after 'tracks' → partial result, tracks checkpoint written
    p1 = dict(base, cache_dir=cache, stop_after='tracks')
    r1 = pipeline.build_road_graph(df, params=p1)
    assert r1 is not None and r1.get('partial')
    assert r1['stage'] == 'tracks' and r1['graph'] is None
    assert checkpoint.has_tracks(cache)

    # resume from 'tracks' → full graph without touching the input df
    p2 = dict(base, cache_dir=cache, start_stage='tracks')
    r2 = pipeline.build_road_graph(None, params=p2)
    assert r2 is not None and not r2.get('partial')
    assert r2['graph'].edge_count() >= 1


def test_pipeline_stop_after_points(tmp_path):
    from gps_road_builder.core import checkpoint
    df = _plus_dataframe()
    r = pipeline.build_road_graph(df, params={
        'cache_dir': str(tmp_path), 'stop_after': 'points',
        'min_point_dist': 0.0, 'backend': 'numpy'})
    assert r is not None and r.get('partial') and r['stage'] == 'points'
    assert r['graph'] is None
    assert checkpoint.has_points(str(tmp_path))


def test_pipeline_cancellation():
    df = _plus_dataframe()
    # cancel immediately → pipeline returns None
    result = pipeline.build_road_graph(
        df, params={'backend': 'numpy'}, is_cancelled=lambda: True)
    assert result is None


def test_pipeline_logs_params_and_stage_metrics():
    # §WS-L: the log callback must receive the resolved params and stage metrics.
    df = _plus_dataframe()
    lines = []
    params = {
        'cell_tau': 5.0, 'resample_k': 5.0, 'eps_mode': 'otsu',
        'min_point_dist': 0.0, 'edge_f_min': 1, 'edge_l_min': 0.0,
        'protect_long_m': None, 'slide_min_loops': 0, 'slide_max_loops': 60,
        'backend': 'numpy', 'split_mode': 'off',
    }
    result = pipeline.build_road_graph(df, params=params, log=lines.append)
    assert result is not None
    text = '\n'.join(lines)
    assert 'params | method=slide' in text          # settings logged
    assert 'stage | extract' in text                # stage metric logged
    assert 'stage | cleanup' in text


def test_pipeline_percentile_threshold_and_devices():
    # §WS-KDE/WS-Dev: percentile threshold mode + n_devices attribute.
    df = _plus_dataframe()
    params = {
        'cell_tau': 5.0, 'resample_k': 5.0, 'eps_mode': 'percentile',
        'eps_percentile': 40.0, 'min_point_dist': 0.0, 'edge_f_min': 1,
        'edge_l_min': 0.0, 'protect_long_m': None, 'slide_min_loops': 0,
        'slide_max_loops': 60, 'backend': 'numpy', 'split_mode': 'off',
    }
    result = pipeline.build_road_graph(df, params=params)
    assert result is not None
    graph = result['graph']
    assert graph.edge_count() >= 1
    # every edge carries n_devices, and the '+' has many devices → some > 0
    assert all('n_devices' in e for e in graph.edges)
    assert max(e['n_devices'] for e in graph.edges) >= 1


def test_pipeline_kde_feeds_single_points():
    # §WS-KDE: KDE keeps single-point tracks (min_points=1) → builds a graph
    # even when segmentation shatters sparse fixes.
    df = _plus_dataframe()
    params = {
        'method': 'kde', 'cell_tau': 5.0, 'kde_radius': 20.0,
        'gap_buffer_m': 10.0, 'eps_mode': 'otsu', 'min_point_dist': 0.0,
        'edge_f_min': 1, 'edge_l_min': 0.0, 'protect_long_m': None,
        'split_mode': 'off', 'gap_dt_s': 1.0,   # tiny gap → many 1-point tracks
    }
    result = pipeline.build_road_graph(df, params=params)
    assert result is not None
    assert result['graph'].edge_count() >= 1


def test_pipeline_aoi_and_connectivity_params():
    # §WS-AOI/WS-Conn: AOI clip + connectivity params flow through the build.
    df = _plus_dataframe()
    # AOI polygon (lon/lat) covering the whole '+' network → keeps all points.
    d = 0.02
    aoi = [np.array([[LON0 - d, LAT0 - d], [LON0 + d, LAT0 - d],
                     [LON0 + d, LAT0 + d], [LON0 - d, LAT0 + d],
                     [LON0 - d, LAT0 - d]])]
    params = {
        'cell_tau': 5.0, 'resample_k': 5.0, 'eps_mode': 'otsu',
        'min_point_dist': 0.0, 'edge_f_min': 1, 'edge_l_min': 0.0,
        'protect_long_m': None, 'slide_min_loops': 0, 'slide_max_loops': 60,
        'backend': 'numpy', 'split_mode': 'off',
        'aoi_polygon': aoi, 'connect_gap_m': 5.0, 'keep_largest': True,
        'slide_close_gaps_m': 5.0,
    }
    result = pipeline.build_road_graph(df, params=params)
    assert result is not None
    assert result['stats'].get('aoi_removed', 0) == 0     # nothing outside AOI
    assert result['graph'].edge_count() >= 1


def test_pipeline_smoothing_preserves_topology():
    # §WS-Smooth: smoothing must run end-to-end without breaking topology or
    # geometry (the '+' arms are straight, so vertex count may not grow here —
    # densification is covered in test_smoothing).
    df = _plus_dataframe()
    base = {
        'cell_tau': 5.0, 'resample_k': 5.0, 'eps_mode': 'otsu',
        'min_point_dist': 0.0, 'edge_f_min': 1, 'edge_l_min': 0.0,
        'protect_long_m': None, 'slide_min_loops': 0, 'slide_max_loops': 60,
        'backend': 'numpy', 'split_mode': 'off',
    }
    raw = pipeline.build_road_graph(df, params=dict(base, smooth_iters=0))
    smooth = pipeline.build_road_graph(df, params=dict(base, smooth_iters=3))
    assert raw is not None and smooth is not None
    assert smooth['graph'].edge_count() == raw['graph'].edge_count()
    for e in smooth['graph'].edges:
        ll = e['coords_lonlat']
        assert len(ll) >= 2 and np.all(np.isfinite(ll))
