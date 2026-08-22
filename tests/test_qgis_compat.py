# -*- coding: utf-8 -*-
"""Static guards for the QGIS 3 / QGIS 4 compatibility boundary."""

import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _source(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as fh:
        return fh.read()


def test_no_direct_pyqt_major_imports():
    """The QGIS shim, not PyQt5/PyQt6, is the only supported import route."""
    for folder in ('gui', 'core', 'tasks', 'qgis_adapter', 'processing_provider'):
        for root, _dirs, names in os.walk(os.path.join(ROOT, folder)):
            for name in names:
                if not name.endswith('.py'):
                    continue
                text = _source(os.path.relpath(os.path.join(root, name), ROOT))
                assert 'PyQt5' not in text
                assert 'PyQt6' not in text


def test_qt6_sensitive_apis_are_not_used_directly():
    """Qt/QGIS enum spellings must go through qgis_compat at call sites."""
    paths = ('plugin.py', 'gui/gui_handlers.py', 'gui/gui_main.py',
             'gui/gui_widgets.py', 'gui/gui_dialogs.py', 'gui/simple_donation.py',
             'gui/histogram.py', 'gui/layers.py', 'gui/gui_components.py',
             'tasks/build_task.py')
    forbidden = (
        r'\.exec_\(', r'QAction.*QtWidgets', r'QVariant\.(Int|Double|String)',
        r'QgsTask\.CanCancel', r'QgsSymbolLayer\.Property',
        r'QgsWkbTypes\.(Point|Line|Polygon)Geometry', r'\bQt\.',
        r'QFont\.(Thin|ExtraLight|Light|Normal|Medium|DemiBold|Bold|ExtraBold|Black)',
        r'QHeaderView\.(Stretch|ResizeToContents|Interactive|Fixed)',
        r'QTableWidget\.(NoEditTriggers|SelectRows)',
        r'QAbstractItemView\.(NoEditTriggers|SelectRows)',
        r'QPainter\.Antialiasing', r'QFrame\.NoFrame',
    )
    for path in paths:
        text = _source(path)
        for pattern in forbidden:
            assert not re.search(pattern, text), '{0}: {1}'.format(path, pattern)


def test_gui_modules_import_compat_shim_relatively():
    """QGIS loads a plugin as a package, not by adding its root to sys.path."""
    for name in os.listdir(os.path.join(ROOT, 'gui')):
        if not name.endswith('.py'):
            continue
        text = _source(os.path.join('gui', name))
        assert 'from qgis_compat import' not in text


def test_ci_runs_the_official_pyqgis4_checker():
    workflow = _source('.github/workflows/ci.yml')
    assert 'ghcr.io/qgis/pyqgis4-checker:main-ubuntu' in workflow
    assert 'pyqt5_to_pyqt6.py --dry_run' in workflow
    assert 'git diff --exit-code' in workflow


def test_combo_popup_has_explicit_qt6_hover_colours():
    """Qt6 Windows delegates must not render a hovered row white-on-white."""
    source = _source('gui/gui_components.py')
    assert 'QComboBox QAbstractItemView::item:hover' in source
    assert 'color: #ffffff;' in source
    assert 'background-color: #3498db;' in source
    assert 'class ComboPopupDelegate(QStyledItemDelegate):' in source
    assert 'setItemDelegate(ComboPopupDelegate(self.view()))' in source
    for path in ('gui/tabs.py', 'gui/gui_main.py', 'gui/gui_widgets.py'):
        assert 'StyledComboBox()' in _source(path)
