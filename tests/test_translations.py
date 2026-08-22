# -*- coding: utf-8 -*-
"""Offline tests for the translation subsystem."""

from gps_road_builder.translations import (
    ar, de, en, es, fr, hi, id as indonesian, pt, ru, th, vi, zh)
from gps_road_builder.translation_manager import (
    RTL_LANGUAGES, TranslationManager, LANGUAGE_LABELS)


LANGUAGE_MODULES = {
    'ru': ru, 'en': en, 'zh': zh, 'hi': hi, 'es': es, 'ar': ar,
    'fr': fr, 'pt': pt, 'de': de, 'id': indonesian, 'th': th, 'vi': vi,
}


def test_all_language_key_parity():
    """Every locale must expose the complete English source-key contract."""
    en_keys = set(en.translations)
    for code, module in LANGUAGE_MODULES.items():
        keys = set(module.translations)
        assert en_keys == keys, (
            "Key mismatch for {0}:\n  only in EN: {1}\n  only in {0}: {2}"
            .format(code, sorted(en_keys - keys), sorted(keys - en_keys)))


def test_no_empty_values():
    for module in LANGUAGE_MODULES.values():
        lang = module.translations
        for key, value in lang.items():
            assert isinstance(value, str) and value.strip(), \
                "Empty translation for key '{0}'".format(key)


def test_language_labels_have_modules():
    supported = {code for code, _ in LANGUAGE_LABELS}
    assert supported == set(LANGUAGE_MODULES)


def test_manager_get_text_and_fallback():
    tm = TranslationManager()
    # existing key resolves to a real string (not the key itself)
    assert tm.get_text('window_title') == ru.translations['window_title']
    # missing key falls back to the key
    assert tm.get_text('___definitely_missing___') == '___definitely_missing___'


def test_manager_switch_language():
    tm = TranslationManager()
    assert tm.set_language('en')
    assert tm.get_current_language() == 'en'
    assert tm.get_text('header_support') == en.translations['header_support']
    assert not tm.set_language('xx')  # unsupported code rejected


def test_manager_loads_every_language_without_english_fallback():
    """A missing module must not be hidden by the English fallback dictionary."""
    tm = TranslationManager()
    for code, module in LANGUAGE_MODULES.items():
        assert tm.set_language(code), code
        assert tm.is_language_loaded(code), code
        assert tm.get_text('header_support') == module.translations['header_support']


def test_arabic_is_the_only_rtl_locale():
    assert RTL_LANGUAGES == {'ar'}


def test_main_dialog_sets_rtl_direction_from_current_language():
    """Arabic must change the actual dialog direction during a live switch."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, 'gui', 'gui_main.py'), encoding='utf-8') as fh:
        source = fh.read()
    assert 'self.setLayoutDirection(qt_enum(' in source
    assert "'RightToLeft' if translations.is_rtl() else 'LeftToRight'" in source


def test_no_fixed_size_blocks_localised_content():
    """Long German/Portuguese labels must be allowed to grow with the dialog."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for filename in ('gui_dialogs.py', 'gui_widgets.py', 'simple_donation.py'):
        with open(os.path.join(root, 'gui', filename), encoding='utf-8') as fh:
            assert 'setFixedSize(' not in fh.read(), filename


def test_placeholder_formatting_keys_present():
    """Keys used with .format(...) must exist in both languages."""
    for key in ('deps_installing', 'deps_install_done', 'deps_install_failed'):
        assert '{0}' in en.translations[key]
        assert '{0}' in ru.translations[key]


def test_format_placeholder_parity_for_every_language():
    """Fallback must not hide a missing format placeholder in any locale."""
    import string
    formatter = string.Formatter()
    for key in en.translations:
        en_fields = {name for _, name, _, _ in formatter.parse(en.translations[key])
                     if name is not None}
        for code, module in LANGUAGE_MODULES.items():
            fields = {name for _, name, _, _ in formatter.parse(
                module.translations[key]) if name is not None}
            assert en_fields == fields, 'placeholder mismatch for {0}: {1}'.format(
                code, key)


def test_english_values_contain_no_cyrillic():
    """English UI must never quietly fall back to Russian user-visible text."""
    import re
    for key, value in en.translations.items():
        assert not re.search(r'[А-Яа-яЁё]', value), key


def test_new_locales_resolve_their_own_core_ui_values():
    """A target dictionary must win over English, even where a word coincides."""
    tm = TranslationManager()
    for code, module in LANGUAGE_MODULES.items():
        if code == 'en':
            continue
        assert tm.set_language(code)
        for key in ('header_support', 'tab_data', 'build_graph', 'preset_mixed',
                    'data_group', 'method_label', 'out_group', 'build_done'):
            assert tm.get_text(key) == module.translations[key]


def test_composite_gui_classes_define_retranslate_contract():
    """Keep live translation coverage without importing unavailable QGIS/PyQt."""
    import ast
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    required = {
        'tabs.py': {'DataTab', 'PreprocessTab', 'DensitySlideTab', 'GraphTab',
                    'ScaleTab', 'PostprocessTab', 'OutputTab'},
        'gui_widgets.py': {'HeaderWidget', 'ControlButtonsWidget',
                           'ResultsTableWidget', 'DependenciesWidget'},
        'gui_dialogs.py': {'AuthorInfoDialog', 'InstallProgressDialog', 'ErrorDialog'},
        'simple_donation.py': {'SimpleDonationDialog'},
    }
    for filename, classes in required.items():
        path = os.path.join(root, 'gui', filename)
        tree = ast.parse(open(path, encoding='utf-8').read(), filename=path)
        found = {node.name for node in tree.body if isinstance(node, ast.ClassDef)
                 and any(isinstance(item, ast.FunctionDef) and
                         item.name == 'retranslateUi' for item in node.body)}
        assert classes <= found, filename + ': ' + repr(classes - found)


def test_main_dialog_retranslates_presets_and_startup_log():
    """Live language changes must not leave initial English UI state behind."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, 'gui', 'gui_main.py'), encoding='utf-8') as fh:
        source = fh.read()
    assert 'retranslate_combo(\n            self.preset_combo' in source
    assert 'def _retranslate_ready_log(self):' in source


def test_every_preset_has_a_label():
    """Each built-in preset must have a translated name in both languages,
    otherwise the preset combo box shows the raw key (get_text falls back to
    the key for missing entries)."""
    from gps_road_builder.core.presets import PRESET_ORDER
    for name in PRESET_ORDER:
        key = 'preset_' + name
        assert key in en.translations, "missing EN label for preset " + name
        assert key in ru.translations, "missing RU label for preset " + name


def test_language_flags_present():
    """Every language must map to a flag icon file that actually exists
    (flags are drawn as icons, not emoji — ADD4 п.8)."""
    import os
    from gps_road_builder.translation_manager import (
        LANGUAGE_FLAGS, LANGUAGE_LABELS)
    pkg = os.path.dirname(os.path.dirname(os.path.abspath(ru.__file__)))
    for code, _ in LANGUAGE_LABELS:
        assert code in LANGUAGE_FLAGS, "no flag mapping for " + code
        path = os.path.join(pkg, 'resources', 'flags', LANGUAGE_FLAGS[code])
        assert os.path.exists(path), "missing flag file: " + path


def test_flag_icons_have_local_license_notice():
    import os
    pkg = os.path.dirname(os.path.dirname(os.path.abspath(ru.__file__)))
    license_path = os.path.join(pkg, 'resources', 'flags', 'LICENSE.txt')
    assert os.path.exists(license_path)


def test_ui_labels_use_ridgeslide_brand():
    """Core UI labels must say 'RidgeSlide', not bare 'Slide' (ADD4 п.9).
    Lineage text (e.g. about_algorithm_text) may still mention the original
    Slide approach and is intentionally excluded."""
    import re
    label_keys = ('tab_density', 'method_slide', 'ds_slide_backend', 'ds_group',
                  'ds_min_loops', 'ds_max_loops', 'preset_sparse_slide',
                  'deps_purpose_numba')
    for lang in (en.translations, ru.translations):
        for key in label_keys:
            assert not re.search(r'(?<!Ridge)Slide', lang[key]), \
                "bare 'Slide' in label '{0}': {1}".format(key, lang[key])
