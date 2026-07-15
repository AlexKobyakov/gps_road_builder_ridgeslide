# -*- coding: utf-8 -*-
"""Offline tests for the dependency installer (pure logic, no network)."""

import os

import pytest

from gps_road_builder.core.deps import installer


def test_build_pip_command_basic():
    cmd = installer.build_pip_command(['numba'], '/tmp/libs', python='python')
    assert cmd[:4] == ['python', '-m', 'pip', 'install']
    assert '--target' in cmd
    assert '/tmp/libs' in cmd
    assert cmd[-1] == 'numba'
    # PyPI index used by default (no --no-index / --find-links)
    assert '--no-index' not in cmd
    assert '--find-links' not in cmd


def test_build_pip_command_offline():
    cmd = installer.build_pip_command(
        ['scikit-image'], '/t', python='py',
        find_links='/wheels', no_index=True)
    assert '--no-index' in cmd
    i = cmd.index('--find-links')
    assert cmd[i + 1] == '/wheels'


def test_open_url_rejects_non_web_scheme():
    for bad in ('file:///etc/passwd', 'ftp://host/x', 'data:text/plain,hi'):
        with pytest.raises(ValueError):
            installer.open_url(bad)


def test_is_within_blocks_zip_slip():
    assert installer._is_within('/base', os.path.join('/base', 'sub', 'x'))
    assert installer._is_within('/base', '/base')
    assert not installer._is_within('/base', '/etc/passwd')
    assert not installer._is_within('/base', '/base/../escape')


def test_package_registry():
    names = set(installer.PACKAGES)
    assert {'numba', 'scikit-image', 'pyarrow', 'scikit-learn'} <= names
    for cfg in installer.PACKAGES.values():
        assert cfg['import_name']
        assert cfg['pip_spec']
        assert cfg['purpose_key']


def test_package_status_shape():
    rows = installer.package_status()
    assert len(rows) == len(installer.PACKAGES)
    for name, import_name, purpose_key, installed in rows:
        assert isinstance(name, str)
        assert isinstance(import_name, str)
        assert isinstance(purpose_key, str)
        assert isinstance(installed, bool)


def test_is_installed_detects_stdlib():
    assert installer.is_installed('os') is True
    assert installer.is_installed('nonexistent_module_zzz') is False


def test_python_executable_returns_something():
    assert installer.python_executable()
