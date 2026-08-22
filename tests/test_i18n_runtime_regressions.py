# -*- coding: utf-8 -*-
"""Offline regression tests for live-language-switch failures seen in QGIS."""

import ast
import os

from gps_road_builder.gui.i18n import (
    dependency_row_text, preset_translation_items, replace_static_log_text)
from gps_road_builder.translation_manager import translations


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_preset_items_keep_persistent_names_and_translate_to_russian():
    items = preset_translation_items(('mixed', 'highway'))
    assert items == (('preset_mixed', 'mixed'), ('preset_highway', 'highway'))
    translations.set_language('ru')
    assert translations.get_text(items[0][0]) == 'Смешанное (по умолчанию)'


def test_dependency_rows_translate_without_refreshing_package_state():
    translations.set_language('ru')
    purpose, status = dependency_row_text('deps_purpose_numba', True)
    assert purpose == 'Быстрое ядро RidgeSlide (JIT, параллельно)'
    assert status == '✅ установлено'
    translations.set_language('en')
    purpose, status = dependency_row_text('deps_purpose_numba', False)
    assert purpose == 'Fast RidgeSlide core (JIT, parallel)'
    assert status == '⬜ not installed'


def test_startup_log_translation_preserves_other_history():
    old = 'GPS Road Builder is ready.'
    new = 'GPS Road Builder готов.'
    document = 'before\n' + old + '\nafter'
    assert replace_static_log_text(document, old, new) == 'before\n' + new + '\nafter'


def test_dependency_retranslate_does_not_refresh_installed_packages():
    path = os.path.join(ROOT, 'gui', 'gui_widgets.py')
    tree = ast.parse(open(path, encoding='utf-8').read(), filename=path)
    widget = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                  and node.name == 'DependenciesWidget')
    method = next(node for node in widget.body if isinstance(node, ast.FunctionDef)
                  and node.name == 'retranslateUi')
    refresh_calls = [node for node in ast.walk(method)
                     if isinstance(node, ast.Call) and
                     isinstance(node.func, ast.Attribute) and
                     node.func.attr == 'refresh']
    assert not refresh_calls


def test_language_selector_uses_index_and_canonical_language_codes():
    path = os.path.join(ROOT, 'gui', 'gui_main.py')
    source = open(path, encoding='utf-8').read()
    assert 'currentIndexChanged[int]' in source

    widgets_source = open(
        os.path.join(ROOT, 'gui', 'gui_widgets.py'), encoding='utf-8').read()
    handlers_source = open(
        os.path.join(ROOT, 'gui', 'gui_handlers.py'), encoding='utf-8').read()
    assert 'def language_code_at(self, index):' in widgets_source
    assert 'language_code_at(_index)' in handlers_source
    assert 'language_combo.currentIndex()' in handlers_source
    assert 'language_combo.currentData()' not in handlers_source


def test_checkbox_style_has_a_visible_checked_mark():
    """Qt6 must not render checked boxes as an indistinguishable blue square."""
    source = open(
        os.path.join(ROOT, 'gui', 'gui_components.py'), encoding='utf-8').read()
    assert 'QCheckBox::indicator:checked' in source
    assert 'checkmark-white.svg' in source
    assert os.path.exists(os.path.join(ROOT, 'resources', 'checkmark-white.svg'))
