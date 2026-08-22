# -*- coding: utf-8 -*-
"""Packaging guards for the installable plugin ZIP."""

import importlib.util
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, 'scripts', 'build_plugin.py')


def _builder_module():
    spec = importlib.util.spec_from_file_location('build_plugin', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_virtual_environments_are_excluded_from_plugin_package():
    builder = _builder_module()
    included = [rel for _full, rel in builder._included_files()]
    assert not any(rel.split(os.sep)[0] == '.venv' for rel in included)


def test_qgis4_smoke_metadata_only_changes_the_zip_copy():
    builder = _builder_module()
    source = '[general]\nqgisMaximumVersion=3.99\n'
    assert builder._qgis4_smoke_metadata(source) == (
        '[general]\nqgisMaximumVersion=4.99\n')


def test_qgis4_smoke_metadata_is_a_noop_after_qgis4_release():
    builder = _builder_module()
    source = '[general]\nqgisMaximumVersion=4.99\n'
    assert builder._qgis4_smoke_metadata(source) == source


def test_processing_provider_and_shared_adapter_are_packaged():
    builder = _builder_module()
    included = {rel.replace(os.sep, '/') for _full, rel in builder._included_files()}
    assert 'processing_provider/provider.py' in included
    assert 'processing_provider/algorithms.py' in included
    assert 'qgis_adapter/layers.py' in included
