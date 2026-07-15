# -*- coding: utf-8 -*-
"""Offline tests for run-logging helpers (WS-L)."""

import json

from gps_road_builder.core import run_log
from gps_road_builder.core import pipeline


def test_format_params_covers_key_groups():
    p = pipeline.default_params()
    p.update({'method': 'kde', 'eps_mode': 'manual', 'eps_value': 0.1})
    lines = run_log.format_params(p)
    text = '\n'.join(lines)
    assert 'method=kde' in text
    assert 'eps=manual(0.1)' in text
    # every line is a compact, greppable 'params | ...' record
    assert all(ln.startswith('params | ') for ln in lines)


def test_format_stage_with_metrics_and_time():
    s = run_log.format_stage('extract', {'threshold': 0.1, 'edges': 42}, 1.5)
    assert 'stage | extract' in s
    assert 'threshold=0.1' in s and 'edges=42' in s
    assert 'Δ 1.5s' in s


def test_format_header():
    lines = run_log.format_header('0.10.0', '3 file(s)', ['numba', 'skimage'])
    assert any('v0.10.0' in ln for ln in lines)
    assert any('3 file(s)' in ln for ln in lines)
    assert any('numba' in ln for ln in lines)


def test_manifest_line_is_valid_json_and_serializes_tuples():
    params = {'weights': (0.5, 0.2, 0.1, 0.7), 'method': 'slide'}
    stats = {'edges': 100, 'nodes': 120}
    line = run_log.manifest_line('0.10.0', params, stats)
    rec = json.loads(line)
    assert rec['version'] == '0.10.0'
    assert rec['params']['weights'] == [0.5, 0.2, 0.1, 0.7]   # tuple → list
    assert rec['stats']['edges'] == 100


def test_manifest_line_handles_nonjsonable():
    line = run_log.manifest_line('0', {'x': object()}, {})
    rec = json.loads(line)
    assert isinstance(rec['params']['x'], str)
