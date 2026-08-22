# -*- coding: utf-8 -*-
"""Offline tests for the dependency installer (pure logic, no network)."""

import os
from types import SimpleNamespace

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
    assert {'pandas', 'numba', 'scikit-image', 'pyarrow', 'scikit-learn'} <= names
    assert installer.PACKAGES['pandas']['optional'] is False
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


def test_python_executable_finds_osgeo4w_root_python(tmp_path):
    """QGIS may run from apps/qgis/bin while Python is at root/bin."""
    qgis = tmp_path / 'apps' / 'qgis' / 'bin' / 'qgis.exe'
    qgis.parent.mkdir(parents=True)
    qgis.touch()
    python = tmp_path / 'bin' / 'python3.exe'
    python.parent.mkdir()
    python.touch()
    assert installer.python_executable(str(qgis)) == str(python)


def test_pip_environment_bootstraps_only_under_plugin_target(tmp_path, monkeypatch):
    """Missing pip is bootstrapped privately, never into QGIS site-packages."""
    calls = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        root = cmd[cmd.index('--root') + 1]
        package = os.path.join(root, 'Lib', 'site-packages', 'pip')
        os.makedirs(package)
        open(os.path.join(package, '__init__.py'), 'w').close()
        return SimpleNamespace(returncode=0, stdout=b'')

    monkeypatch.setattr(installer, 'ensurepip_available', lambda _python: True)
    monkeypatch.setattr(installer, 'subprocess',
                        SimpleNamespace(run=fake_run, PIPE=-1, STDOUT=-2,
                                        STARTUPINFO=lambda: None,
                                        STARTF_USESHOWWINDOW=0))
    monkeypatch.setattr(installer, '_no_window', lambda: {})
    monkeypatch.setattr(
        installer, '_pip_available', lambda _python, env=None: env is not None)

    python, env = installer.pip_environment('qgis-python', str(tmp_path))
    assert python == 'qgis-python'
    assert calls[0][:3] == ['qgis-python', '-m', 'ensurepip']
    assert env['PYTHONPATH'].startswith(
        os.path.join(str(tmp_path), '_pip_bootstrap', 'Lib', 'site-packages'))


def test_runtime_tag_separates_qgis_major_and_python_abi():
    assert installer.runtime_tag(34412, (3, 9)) == 'qgis3-py39'
    assert installer.runtime_tag(40200, (3, 12)) == 'qgis4-py312'
