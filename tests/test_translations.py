# -*- coding: utf-8 -*-
"""Offline tests for the translation subsystem."""

from gps_road_builder.translations import en, ru
from gps_road_builder.translation_manager import TranslationManager, LANGUAGE_LABELS


def test_ru_en_key_parity():
    """RU and EN dictionaries must define exactly the same keys."""
    en_keys = set(en.translations)
    ru_keys = set(ru.translations)
    assert en_keys == ru_keys, (
        "Key mismatch:\n"
        "  only in EN: {0}\n"
        "  only in RU: {1}".format(sorted(en_keys - ru_keys),
                                   sorted(ru_keys - en_keys)))


def test_no_empty_values():
    for lang in (en.translations, ru.translations):
        for key, value in lang.items():
            assert isinstance(value, str) and value.strip(), \
                "Empty translation for key '{0}'".format(key)


def test_language_labels_have_modules():
    supported = {code for code, _ in LANGUAGE_LABELS}
    assert supported == {'ru', 'en'}


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


def test_placeholder_formatting_keys_present():
    """Keys used with .format(...) must exist in both languages."""
    for key in ('deps_installing', 'deps_install_done', 'deps_install_failed'):
        assert '{0}' in en.translations[key]
        assert '{0}' in ru.translations[key]


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
