# -*- coding: utf-8 -*-
"""Offline tests for io.csv_reader (format detection + normalization)."""

import pandas as pd

from gps_road_builder.core.io import csv_reader, schema


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding='utf-8')
    return str(path)


def test_sniff_delimiter():
    assert csv_reader.sniff_delimiter('a;b;c;d') == ';'
    assert csv_reader.sniff_delimiter('"a"/"b"/"c"/"d"') == '/'
    assert csv_reader.sniff_delimiter('a,b,c') == ','
    assert csv_reader.sniff_delimiter('a\tb\tc') == '\t'


def test_read_semicolon_iso(tmp_path):
    path = _write(
        tmp_path, 'a.csv',
        'device_id;navigation_dttm;lat;lon\n'
        '3070706185;2025-08-13 02:28:54;47.4403809;138.7108925\n')
    df = csv_reader.read_normalized(path)
    assert list(df.columns) == list(schema.CANONICAL_COLUMNS)
    assert len(df) == 1
    assert df[schema.DEVICE].iloc[0] == '3070706185'
    assert abs(df[schema.LAT].iloc[0] - 47.4403809) < 1e-6
    assert df[schema.TIME].iloc[0] == pd.Timestamp('2025-08-13 02:28:54')


def test_read_slash_quoted(tmp_path):
    path = _write(
        tmp_path, 'b.csv',
        '"device_id"/"navigation_dttm"/"lat"/"lon"\n'
        '3065162782/2025-08-27 03:50:52/44.1639200/133.8619200\n')
    df = csv_reader.read_normalized(path)
    assert len(df) == 1
    assert df[schema.DEVICE].iloc[0] == '3065162782'
    assert abs(df[schema.LON].iloc[0] - 133.8619200) < 1e-6


def test_read_dotted_dayfirst(tmp_path):
    path = _write(
        tmp_path, 'c.csv',
        'device_id;navigation_dttm;lat;lon\n'
        '3061726861;12.04.2025 8:21;44.39974;131.2594233\n')
    df = csv_reader.read_normalized(path)
    # 12.04.2025 → day-first → 12 April 2025
    assert df[schema.TIME].iloc[0] == pd.Timestamp('2025-04-12 08:21:00')


def test_unparseable_rows_dropped(tmp_path):
    path = _write(
        tmp_path, 'd.csv',
        'device_id;navigation_dttm;lat;lon\n'
        '1;2025-08-13 02:28:54;47.4;138.7\n'
        '2;not-a-date;xx;yy\n')
    df = csv_reader.read_normalized(path)
    assert len(df) == 1


def test_iter_data_files_recursive(tmp_path):
    month = tmp_path / 'август'
    month.mkdir()
    (month / 'x.csv').write_text(
        'device_id;navigation_dttm;lat;lon\n1;2025-08-13 02:28:54;47;138\n',
        encoding='utf-8')
    files = csv_reader.iter_data_files(str(tmp_path))
    assert len(files) == 1
    assert files[0][0] == 'август'
    assert files[0][1].endswith('x.csv')


def test_load_dataset_concatenates(tmp_path):
    _write(tmp_path, 'a.csv',
           'device_id;navigation_dttm;lat;lon\n1;2025-08-13 02:28:54;47;138\n')
    _write(tmp_path, 'b.csv',
           '"device_id"/"navigation_dttm"/"lat"/"lon"\n2/2025-08-27 03:50:52/44/133\n')
    df = csv_reader.load_dataset(str(tmp_path))
    assert len(df) == 2
    assert set(df[schema.DEVICE]) == {'1', '2'}
