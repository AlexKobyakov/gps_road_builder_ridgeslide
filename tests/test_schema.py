# -*- coding: utf-8 -*-
"""Offline tests for io.schema (column mapping + validation)."""

from gps_road_builder.core.io import schema


def test_detect_columns_plain():
    m = schema.detect_columns(['device_id', 'navigation_dttm', 'lat', 'lon'])
    assert m[schema.DEVICE] == 'device_id'
    assert m[schema.TIME] == 'navigation_dttm'
    assert m[schema.LAT] == 'lat'
    assert m[schema.LON] == 'lon'
    assert schema.mapping_is_complete(m)


def test_detect_columns_quoted():
    m = schema.detect_columns(['"device_id"', '"navigation_dttm"', '"lat"', '"lon"'])
    assert schema.mapping_is_complete(m)


def test_detect_columns_aliases():
    m = schema.detect_columns(['imei', 'datetime', 'latitude', 'longitude'])
    assert schema.mapping_is_complete(m)
    assert m[schema.DEVICE] == 'imei'
    assert m[schema.LON] == 'longitude'


def test_incomplete_mapping():
    m = schema.detect_columns(['foo', 'bar'])
    assert not schema.mapping_is_complete(m)
    assert set(schema.missing_roles(m)) == set(schema.CANONICAL_COLUMNS)


def test_valid_ranges():
    assert schema.valid_lat(45.0)
    assert not schema.valid_lat(120.0)
    assert schema.valid_lon(138.0)
    assert not schema.valid_lon(200.0)
    assert not schema.valid_lat('nan-text')
