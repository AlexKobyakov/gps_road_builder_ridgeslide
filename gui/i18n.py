# -*- coding: utf-8 -*-
"""Small helpers for widgets that support live UI translation."""

from ..translation_manager import translations


class RetranslatableMixin:
    """Keep references to translated Qt objects created by a composite widget."""

    def _init_i18n(self):
        self._text_bindings = []
        self._tooltip_bindings = []
        self._form_labels = []

    def _bind_text(self, widget, key, prefix=''):
        self._text_bindings.append((widget, key, prefix))
        return widget

    def _bind_tooltip(self, widget, key, prefix=''):
        self._tooltip_bindings.append((widget, key, prefix))
        return widget

    def _add_form_row(self, form, key, field):
        from qgis.PyQt.QtWidgets import QLabel
        label = QLabel()
        self._form_labels.append((label, key))
        form.addRow(label, field)
        return label

    def _retranslate_bound_widgets(self):
        t = translations.get_text
        for widget, key, prefix in self._text_bindings:
            text = prefix + t(key)
            if hasattr(widget, 'setText'):
                widget.setText(text)
            else:
                widget.setTitle(text)
        for widget, key, prefix in self._tooltip_bindings:
            widget.setToolTip(prefix + t(key))
        for label, key in self._form_labels:
            label.setText(t(key) if key else '')


def retranslate_combo(combo, items):
    """Replace combo labels while preserving ``currentData`` and silencing slots."""
    from qgis.PyQt.QtCore import QSignalBlocker
    current = combo.currentData()
    blocker = QSignalBlocker(combo)
    combo.clear()
    for key, value in items:
        combo.addItem(translations.get_text(key), value)
    index = combo.findData(current)
    if index >= 0:
        combo.setCurrentIndex(index)
    del blocker


def preset_translation_items(names):
    """Return stable preset ``(translation_key, persistent_name)`` pairs."""
    return tuple(('preset_' + name, name) for name in names)


def dependency_row_text(purpose_key, installed):
    """Return translated purpose and status text without importing dependencies."""
    t = translations.get_text
    status = t('deps_status_installed') if installed else t('deps_status_missing')
    return t(purpose_key), ('✅ ' if installed else '⬜ ') + status


def replace_static_log_text(document, old, new):
    """Translate a known static log fragment while preserving other log history."""
    return document.replace(old, new)
