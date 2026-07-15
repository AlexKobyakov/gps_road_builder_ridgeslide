# -*- coding: utf-8 -*-
"""Offline sanity checks for metadata.txt."""

import configparser
import os

import gps_road_builder


def _metadata():
    plugin_dir = os.path.dirname(gps_road_builder.__file__)
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(plugin_dir, 'metadata.txt'), encoding='utf-8')
    return cfg['general']


def test_min_qgis_version():
    assert _metadata()['qgisMinimumVersion'] == '3.22'


def test_required_fields_present():
    general = _metadata()
    for field in ('name', 'version', 'description', 'author', 'email',
                  'repository', 'category'):
        assert general.get(field), "metadata.txt missing '{0}'".format(field)


def test_name_and_category():
    general = _metadata()
    # Display name carries the RidgeSlide sub-brand; the package folder and
    # settings keys stay 'gps_road_builder' (unchanged).
    assert general['name'] == 'GPS Road Builder (RidgeSlide)'
    assert general['category'] == 'Vector'
