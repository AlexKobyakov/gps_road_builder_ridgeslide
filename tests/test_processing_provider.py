# -*- coding: utf-8 -*-
"""Offline contract guards for the QGIS Processing public API."""

import os

from gps_road_builder.core.presets import PRESET_ORDER
from gps_road_builder.processing_provider import ids


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _source(relative_path):
    with open(os.path.join(ROOT, relative_path), encoding='utf-8') as handle:
        return handle.read()


def test_processing_machine_ids_are_stable_ascii_and_complete():
    assert ids.PROVIDER_ID == 'gpsroadbuilder'
    assert ids.ALGORITHM_IDS == (
        'build_network_from_layer', 'build_network_from_folder',
        'postprocess_network')
    for value in (ids.PROVIDER_ID, ids.GROUP_ID) + ids.ALGORITHM_IDS:
        assert value.isascii()
        assert value == value.lower()
        assert value.replace('_', '').isalnum()
    for value in ids.PARAMETER_IDS:
        assert value.isascii()
        assert value.replace('_', '').isalnum()
        assert value == value.upper()


def test_processing_provider_has_exactly_three_registered_algorithms():
    source = _source(os.path.join('processing_provider', 'provider.py'))
    assert source.count('self.addAlgorithm(') == 3
    for algorithm_id in ids.ALGORITHM_IDS:
        assert algorithm_id in _source(os.path.join('processing_provider', 'ids.py'))


def test_processing_mapping_reuses_preset_contract_without_qsettings():
    values = {
        ids.PRESET: 'sparse_slide', ids.METHOD: 'kde', ids.CELL_SIZE: 12.5,
        ids.MIN_FREQUENCY: 4, ids.MIN_LENGTH: 42.0, ids.GAP_TIME: 17.0,
        ids.CONNECT_GAP: 25.0, ids.KEEP_LARGEST: True,
    }
    params = ids.pipeline_params_from_machine_values(values)
    assert params['method'] == 'kde'
    assert params['cell_tau'] == 12.5
    assert params['edge_f_min'] == 4
    assert params['edge_l_min'] == 42.0
    assert params['gap_dt_s'] == 17.0 * 60.0
    assert params['connect_gap_m'] == 25.0
    assert params['keep_largest'] is True
    source = _source(os.path.join('processing_provider', 'ids.py'))
    assert 'SettingsManager' not in source
    assert 'QSettings' not in source
    assert tuple(PRESET_ORDER) == ids.PRESET_ORDER


def test_processing_code_has_no_gui_or_project_side_effects():
    source = _source(os.path.join('processing_provider', 'algorithms.py'))
    assert 'gui.' not in source
    assert 'iface' not in source
    assert 'QMessageBox' not in source
    assert 'QgsProject' not in source
    assert 'context.transformContext()' in source
    assert 'feedback.isCanceled' in source
    assert 'QgsProcessingException' in source


def test_processing_output_schema_and_standard_sink_are_fixed():
    adapter = _source(os.path.join('qgis_adapter', 'layers.py'))
    for name in ('id', 'frequency', 'length', 'road_class', 'reconstructed',
                 'n_devices'):
        assert repr(name) in adapter
    source = _source(os.path.join('processing_provider', 'algorithms.py'))
    assert 'QgsProcessingParameterFeatureSink' in source
    assert "QgsCoordinateReferenceSystem('EPSG:4326')" in source
    assert 'parameterAsSink(' in source


def test_processing_qgis4_scoped_enum_fallbacks_are_explicit():
    source = _source(os.path.join('processing_provider', 'algorithms.py'))
    assert "'ProcessingParameterFlag', 'Advanced'" in source
    assert "'ProcessingSourceType', 'VectorAnyGeometry'" in source
    assert 'minValue=minimum' in source


def test_gui_uses_the_shared_qgis_adapter():
    source = _source(os.path.join('gui', 'layers.py'))
    assert 'from ..qgis_adapter.layers import' in source
    handlers = _source(os.path.join('gui', 'gui_handlers.py'))
    assert 'metric_graph_from_feature_source(layer)' in handlers


def test_metadata_enables_processing_provider():
    metadata = _source('metadata.txt')
    assert 'hasProcessingProvider=yes' in metadata


def test_processing_provider_uses_plugin_icon():
    source = _source(os.path.join('processing_provider', 'provider.py'))
    assert 'def icon(self):' in source
    assert "'resources', 'icon.svg'" in source
