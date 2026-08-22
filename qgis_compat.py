# -*- coding: utf-8 -*-
"""Qt5/Qt6 and QGIS 3/4 enum compatibility helpers."""

from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QFont
from qgis.core import Qgis, QgsSymbolLayer, QgsTask


def qt_enum(scope, name):
    """Return a scoped Qt enum member, with the Qt5 unscoped fallback."""
    return getattr(getattr(Qt, scope, Qt), name)


def qt_class_enum(owner, scope, name):
    """Return a scoped Qt class enum member with a Qt5 fallback."""
    return getattr(getattr(owner, scope, owner), name)


def qvariant_type(name):
    """Return QVariant.Type member on Qt6 or the Qt5 unscoped member."""
    return getattr(getattr(QVariant, 'Type', QVariant), name)


def qfont_weight(name):
    """Return QFont.Weight member on Qt6 or the Qt5 unscoped member."""
    return getattr(getattr(QFont, 'Weight', QFont), name)


def qgis_enum(scope, name, legacy_owner=None, legacy_name=None):
    """Return a QGIS 4 scoped enum member or its QGIS 3 counterpart."""
    scoped = getattr(Qgis, scope, None)
    if scoped is not None and hasattr(scoped, name):
        return getattr(scoped, name)
    return getattr(legacy_owner or Qgis, legacy_name or name)


def task_can_cancel():
    """QgsTask flag compatible with QGIS 3 and 4."""
    return qgis_enum('TaskFlag', 'CanCancel', QgsTask)


def symbol_layer_property(name):
    """QgsSymbolLayer property enum compatible with QGIS 3 and 4."""
    return qgis_enum('SymbolLayerProperty', name, QgsSymbolLayer)
