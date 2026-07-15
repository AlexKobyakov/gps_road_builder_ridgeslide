# -*- coding: utf-8 -*-
"""Offline tests for io.writer (GeoJSON / GraphML) and logging_setup."""

import json
import xml.etree.ElementTree as ET

import numpy as np

from gps_road_builder.core.io import writer
from gps_road_builder.core import logging_setup
from gps_road_builder.core.graph.to_graph import RoadGraph


def _graph():
    g = RoadGraph()
    g.nodes = {0: (100.0, 200.0), 1: (150.0, 250.0)}
    g.node_lonlat = {0: (134.0, 45.0), 1: (134.001, 45.001)}
    g.edges = [{
        'u': 0, 'v': 1, 'frequency': 7, 'length': 55.0,
        'coords_lonlat': np.array([[134.0, 45.0], [134.001, 45.001]]),
    }]
    return g


def test_write_geojson(tmp_path):
    path = str(tmp_path / 'roads.geojson')
    writer.write_geojson(_graph(), path)
    with open(path, encoding='utf-8') as fh:
        gj = json.load(fh)
    assert gj['type'] == 'FeatureCollection'
    assert len(gj['features']) == 1
    assert gj['features'][0]['properties']['frequency'] == 7
    assert gj['features'][0]['geometry']['type'] == 'LineString'


def test_write_graphml_is_valid_xml(tmp_path):
    path = str(tmp_path / 'roads.graphml')
    writer.write_graphml(_graph(), path)
    tree = ET.parse(path)
    root = tree.getroot()
    ns = '{http://graphml.graphdrawing.org/xmlns}'
    graph = root.find(ns + 'graph')
    nodes = graph.findall(ns + 'node')
    edges = graph.findall(ns + 'edge')
    assert len(nodes) == 2
    assert len(edges) == 1
    assert edges[0].get('source') == 'n0'
    assert edges[0].get('target') == 'n1'


def test_graphml_uses_node_lonlat(tmp_path):
    path = str(tmp_path / 'r.graphml')
    writer.write_graphml(_graph(), path)
    text = open(path, encoding='utf-8').read()
    assert '134.0' in text and '45.0' in text        # lon/lat, not metric


def test_logging_setup(tmp_path):
    logger = logging_setup.get_logger(base_dir=str(tmp_path))
    assert logger.handlers                            # configured
    logger.info('hello test')
    # idempotent: second call does not add handlers
    n = len(logger.handlers)
    logging_setup.get_logger(base_dir=str(tmp_path))
    assert len(logger.handlers) == n
