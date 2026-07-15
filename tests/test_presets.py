# -*- coding: utf-8 -*-
"""Offline tests for presets and settings→pipeline mapping."""

from gps_road_builder.core import presets


def test_preset_order_and_content():
    assert presets.PRESET_ORDER == (
        'mixed', 'highway', 'spurs',
        'dense_tracks', 'urban_logistics', 'osm_traces',
        'sparse_slide', 'sparse_slide_accurate', 'sparse_ais', 'fgis_kde')
    for name in presets.PRESET_ORDER:
        # every ordered name is a real preset (preset_settings silently falls
        # back to 'mixed' for unknown names, which would hide a typo here)
        assert name in presets.PRESETS
        s = presets.preset_settings(name)
        assert 'cell_tau' in s and 'edge_f_min' in s


def test_scenario_presets_build_valid_params():
    # Every scenario preset (Sprint 10) resolves to a runnable pipeline param
    # set with a known method and a valid threshold mode.
    for name in ('dense_tracks', 'urban_logistics', 'osm_traces', 'sparse_ais'):
        p = presets.build_pipeline_params(presets.preset_settings(name))
        assert p['method'] in ('slide', 'kde')
        assert p['eps_mode'] in ('otsu', 'manual', 'percentile')
        assert p['cell_tau'] > 0 and p['resample_k'] > 0
        assert p['backend'] == 'auto'          # never the slow numpy reference


def test_dense_tracks_finer_than_ais():
    # Running/cycling data is dense with fine detail; AIS is very sparse and
    # coarse — the cell/resample scale must reflect that ordering.
    dense = presets.build_pipeline_params(presets.preset_settings('dense_tracks'))
    ais = presets.build_pipeline_params(presets.preset_settings('sparse_ais'))
    assert dense['cell_tau'] < ais['cell_tau']
    assert dense['resample_k'] < ais['resample_k']


def test_accurate_preset_is_finer_than_sparse():
    # The "accurate" sparse preset trades speed for fidelity: finer cell and
    # resample, less smoothing, micro-loop cleanup, numba (ADD4 п.3).
    acc = presets.build_pipeline_params(
        presets.preset_settings('sparse_slide_accurate'))
    base = presets.build_pipeline_params(presets.preset_settings('sparse_slide'))
    assert acc['cell_tau'] < base['cell_tau']
    assert acc['resample_k'] < base['resample_k']
    assert acc['smooth_iters'] <= base['smooth_iters']
    assert acc['loop_min_m'] > 0
    assert acc['backend'] == 'auto'          # numba, not the slow numpy reference
    assert acc['eps_mode'] == 'percentile'


def test_urban_logistics_favours_busy_roads():
    # Higher min frequency keeps only well-travelled streets; a percentile
    # threshold is robust to depots/parking hot spots (unlike per-tile Otsu).
    urban = presets.preset_settings('urban_logistics')
    assert urban['edge_f_min'] > presets.preset_settings('mixed')['edge_f_min']
    assert urban['eps_mode'] == 'percentile'


def test_fgis_kde_preset_uses_kde():
    p = presets.build_pipeline_params(presets.preset_settings('fgis_kde'))
    assert p['method'] == 'kde'
    assert p['kde_radius'] > 0
    assert p['gap_buffer_m'] > 0


def test_sparse_slide_preset_uses_slide():
    s = presets.preset_settings('sparse_slide')
    p = presets.build_pipeline_params(s)
    assert p['method'] == 'slide'
    assert p['cell_tau'] >= 8.0            # coarse cells for a region
    assert p['smooth_iters'] >= 1          # smoothing on by default
    assert p['spur_min_m'] > 0             # trims spurs
    # perf-critical: numba backend (not numpy) and a coarse resample so sparse
    # points do not explode into tens of millions (grapples with the ui4 hang).
    assert p['backend'] == 'auto'
    assert p['resample_k'] >= 30.0
    # quality: percentile threshold, not per-tile Otsu which blows out on
    # hot-spot tiles and drops roads (ui5 result was too sparse).
    assert p['eps_mode'] == 'percentile'


def test_spurs_preset_is_sensitive():
    spurs = presets.preset_settings('spurs')
    highway = presets.preset_settings('highway')
    assert spurs['edge_f_min'] < highway['edge_f_min']   # keeps rare roads
    assert spurs['cell_tau'] < highway['cell_tau']       # finer cells
    assert spurs['protect_long_edges'] is True


def test_build_pipeline_params_units_and_mapping():
    s = {'gap_dt_min': 5.0, 'protect_long_edges': True, 'edge_l_min': 30.0,
         'eps_mode': 'otsu', 'cell_tau': 3.0}
    p = presets.build_pipeline_params(s)
    assert p['gap_dt_s'] == 300.0                        # minutes → seconds
    assert p['protect_long_m'] == max(200.0, 5.0 * 30.0)
    assert p['eps_mode'] == 'otsu'
    assert p['backend'] == 'auto'


def test_build_pipeline_params_protect_off_and_adaptive():
    s = {'protect_long_edges': False, 'eps_mode': 'adaptive'}
    p = presets.build_pipeline_params(s)
    assert p['protect_long_m'] is None
    assert p['eps_mode'] == 'otsu'                       # adaptive → otsu (MVP)


def test_build_pipeline_params_defaults_on_empty():
    p = presets.build_pipeline_params({})
    assert p['cell_tau'] == 5.0
    assert p['min_point_dist'] == 10.0
    assert p['split_mode'] == 'auto'
