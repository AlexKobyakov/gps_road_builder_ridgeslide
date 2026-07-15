# -*- coding: utf-8 -*-
"""
GPS Road Builder — main plugin class
Основной класс плагина: интеграция с QGIS (меню, иконка, запуск диалога).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import configparser
import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication

from .translation_manager import translations


class GpsRoadBuilderPlugin:
    """Основной класс плагина GPS Road Builder."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # Гарантируем, что доустановленные зависимости (если есть) видны в sys.path
        try:
            from .core.deps import installer
            installer.ensure_on_path()
        except Exception as exc:  # pragma: no cover - defensive
            print("GPS Road Builder: deps path init failed: {0}".format(exc))

        # Инициализируем файловый лог сразу (иначе файл появлялся только при
        # ошибке) — путь <профиль QGIS>/gps_road_builder/gps_road_builder.log
        try:
            from .core.logging_setup import get_logger, log_path
            get_logger().info('GPS Road Builder loaded; log at %s', log_path())
        except Exception as exc:  # pragma: no cover - defensive
            print("GPS Road Builder: logging init failed: {0}".format(exc))

        # Язык интерфейса: берём локаль QGIS, иначе — русский по умолчанию
        try:
            locale = (QgsApplication.instance().locale() or '').lower()
        except Exception:
            locale = ''

        saved = self._saved_language()
        if saved:
            translations.set_language(saved)
        elif locale[:2] in translations.get_supported_languages():
            translations.set_language(locale[:2])
        elif locale.startswith('ru'):
            translations.set_language('ru')
        else:
            translations.set_language('en')

        self.actions = []
        self.menu = 'GPS Road Builder'
        self.dialog = None

    # ------------------------------------------------------------------
    # Метаданные плагина (из metadata.txt)
    # ------------------------------------------------------------------

    @staticmethod
    def _read_metadata():
        plugin_dir = os.path.dirname(__file__)
        metadata_file = os.path.join(plugin_dir, 'metadata.txt')
        config = configparser.ConfigParser()
        config.read(metadata_file, encoding='utf-8')
        return config['general'] if 'general' in config else {}

    @classmethod
    def get_plugin_version(cls):
        """Версия плагина из metadata.txt."""
        try:
            return cls._read_metadata().get('version', 'Unknown')
        except Exception:
            return 'Unknown'

    @classmethod
    def get_plugin_info(cls):
        """Полная информация о плагине из metadata.txt."""
        default = {
            'name': 'GPS Road Builder',
            'version': 'Unknown',
            'author': 'Кобяков Александр Викторович',
            'email': 'kobyakov@lesburo.ru',
            'description': '',
        }
        try:
            section = cls._read_metadata()
            if not section:
                return default
            return {
                'name': section.get('name', default['name']),
                'version': section.get('version', default['version']),
                'author': section.get('author', default['author']),
                'email': section.get('email', default['email']),
                'description': section.get('description', ''),
            }
        except Exception as exc:
            print("GPS Road Builder: error reading metadata: {0}".format(exc))
            return default

    @staticmethod
    def _saved_language():
        try:
            from .core.settings_manager import SettingsManager
            return SettingsManager().get('language')
        except Exception:
            return ''

    # ------------------------------------------------------------------
    # Интеграция с QGIS
    # ------------------------------------------------------------------

    def add_action(self, icon_path, text, callback, parent=None,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None):
        icon = QIcon(icon_path) if icon_path else QIcon()
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        if status_tip is not None:
            action.setStatusTip(status_tip)
        if add_to_toolbar:
            self.iface.addToolBarIcon(action)
        if add_to_menu:
            self.iface.addPluginToVectorMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'resources', 'icon.svg')
        if not os.path.exists(icon_path):
            icon_path = None

        self.add_action(
            icon_path,
            text="🛰️ {0}".format(translations.get_text('window_title')),
            callback=self.run,
            parent=self.iface.mainWindow(),
            status_tip=translations.get_text('plugin_description'),
        )

    def unload(self):
        for action in self.actions:
            self.iface.removePluginVectorMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        self.actions = []
        if self.dialog is not None:
            self.dialog.close()
            self.dialog = None

    def run(self):
        """Открыть главный диалог плагина."""
        if self.dialog is None:
            from .gui.gui_main import GpsRoadBuilderDialog
            self.dialog = GpsRoadBuilderDialog(self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
