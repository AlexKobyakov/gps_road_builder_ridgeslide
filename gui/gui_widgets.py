# -*- coding: utf-8 -*-
"""
Widgets for GPS Road Builder main dialog.
Виджеты главного окна: шапка (язык/поддержка/автор), кнопки управления,
лог, таблица результатов, вкладка зависимостей и плейсхолдеры этапов.

HeaderWidget повторяет дизайн референсного плагина garmin_export.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFrame,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QTableWidgetItem as _Item,
)

from .gui_components import ModernButton, create_styled_button, create_info_label
from ..translation_manager import translations


def _flag_icon(code):
    """QIcon флага языка из resources/flags/ (или None, если файла нет).
    Флаги — иконками, т.к. Windows не рисует эмодзи-флаги (ADD4 п.8)."""
    from ..translation_manager import LANGUAGE_FLAGS
    fname = LANGUAGE_FLAGS.get(code)
    if not fname:
        return None
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        'resources', 'flags', fname)
    return QIcon(path) if os.path.exists(path) else None


class HeaderWidget(QFrame):
    """Градиентная шапка: язык, «Поддержка», «Об авторе»."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #3498db, stop:1 #2ecc71);
                border-radius: 10px;
                margin: 5px;
            }
        """)
        self.setupUi()

    def setupUi(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(20)

        self.title_label = QLabel("🛰️ GPS Road Builder (RidgeSlide)")
        self.title_label.setStyleSheet("""
            QLabel { color: white; font-size: 18px; font-weight: bold;
                     background: transparent; }
        """)

        self.controls_widget = QWidget()
        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(15)

        self._createLanguageSelector(controls_layout)
        self._createDonationButton(controls_layout)
        self._createAuthorButton(controls_layout)

        main_layout.addWidget(self.title_label)
        main_layout.addStretch()
        main_layout.addWidget(self.controls_widget)

    def _createLanguageSelector(self, layout):
        lang_container = QWidget()
        lang_layout = QHBoxLayout(lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.setSpacing(8)

        lang_icon = QLabel("🌐")
        lang_icon.setStyleSheet(
            "QLabel { color: white; font-size: 16px; background: transparent; }")

        self.language_combo = QComboBox()
        self.language_combo.setFixedSize(150, 32)

        # Цвета пунктов задаём на уровне модели (роли), чтобы избежать
        # «белое на белом» на некоторых сборках Qt/Windows.
        dark, white = QColor('#2c3e50'), QColor('#ffffff')
        for code, label in translations.get_language_labels():
            icon = _flag_icon(code)
            if icon is not None:
                self.language_combo.addItem(icon, label, code)
            else:
                self.language_combo.addItem(label, code)
            i = self.language_combo.count() - 1
            self.language_combo.setItemData(i, dark, Qt.ForegroundRole)
            self.language_combo.setItemData(i, white, Qt.BackgroundRole)

        current = translations.get_current_language()
        idx = self.language_combo.findData(current)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)

        self.language_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.95);
                color: #2c3e50;
                border: 2px solid rgba(255, 255, 255, 0.6);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 11px;
            }
            QComboBox:hover { background: #ffffff; border-color: #ffffff; }
            QComboBox::drop-down { border: none; width: 20px; background: transparent; }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                outline: none;
                selection-background-color: #3498db;
                selection-color: #ffffff;
            }
        """)

        lang_layout.addWidget(lang_icon)
        lang_layout.addWidget(self.language_combo)
        layout.addWidget(lang_container)

    def _createDonationButton(self, layout):
        self.donation_button = ModernButton(
            "☕ {0}".format(translations.get_text('header_support')))
        self.donation_button.setFixedSize(130, 32)
        self.donation_button.setToolTip("❤️ " + translations.get_text('support_tip'))
        self.donation_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(244,93,34,0.9),
                                            stop:1 rgba(230,81,0,0.9));
                color: white;
                border: 2px solid rgba(255,255,255,0.3);
                border-radius: 8px;
                font-weight: bold; font-size: 11px; padding: 6px 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(244,93,34,1.0),
                                            stop:1 rgba(230,81,0,1.0));
                border-color: rgba(255,255,255,0.5);
            }
        """)
        layout.addWidget(self.donation_button)

    def _createAuthorButton(self, layout):
        self.author_button = ModernButton(
            "👤 {0}".format(translations.get_text('header_about_author')))
        self.author_button.setFixedSize(120, 32)
        self.author_button.setToolTip("📝 " + translations.get_text('author_tip'))
        self.author_button.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.2);
                color: white;
                border: 2px solid rgba(255,255,255,0.3);
                border-radius: 8px;
                font-weight: bold; font-size: 11px; padding: 6px 12px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.3);
                border-color: rgba(255,255,255,0.5);
            }
        """)
        layout.addWidget(self.author_button)


class ControlButtonsWidget(QWidget):
    """Кнопки управления: построить / тестовый прогон / очистить лог."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        t = translations.get_text
        self.build_button = create_styled_button(t('build_graph'), "primary", "🚀")
        self.test_button = create_styled_button(t('test_run'), "secondary", "🧪")
        self.cancel_button = create_styled_button(t('cancel'), "danger", "❌")
        self.clear_log_button = create_styled_button(t('clear_logs'), "secondary", "🧹")

        layout.addWidget(self.build_button)
        layout.addWidget(self.test_button)
        layout.addStretch()
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.clear_log_button)


class LogTextWidget(QTextEdit):
    """Лог выполнения (только чтение)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumHeight(120)


class ResultsTableWidget(QTableWidget):
    """Таблица результатов по этапам."""

    def __init__(self, parent=None):
        super().__init__(0, 3, parent)
        t = translations.get_text
        self.setHorizontalHeaderLabels([
            "📄 {0}".format(t('col_stage')),
            "📊 {0}".format(t('col_status')),
            "💬 {0}".format(t('col_message')),
        ])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)


class PlaceholderTab(QWidget):
    """Плейсхолдер вкладки этапа (Фаза 0): иконка, заголовок, пояснение."""

    def __init__(self, icon, title, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 30)
        layout.setSpacing(12)

        head = QLabel("{0}  {1}".format(icon, title))
        head.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #2c3e50;")

        notice = create_info_label(translations.get_text('phase0_notice'))
        badge = QLabel("🚧 {0}".format(translations.get_text('coming_soon')))
        badge.setStyleSheet(
            "color: #e67e22; font-weight: bold; background: #fef5e7; "
            "border: 1px solid #f5cba7; border-radius: 6px; padding: 6px 10px;")
        badge.setAlignment(Qt.AlignLeft)

        layout.addWidget(head)
        layout.addWidget(badge)
        layout.addWidget(notice)
        layout.addStretch()


class DependenciesWidget(QWidget):
    """Вкладка «Зависимости»: статус библиотек, способ установки, кнопки."""

    def __init__(self, parent=None):
        super().__init__(parent)
        t = translations.get_text
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.intro_label = create_info_label(t('deps_intro'))

        # Способ установки
        method_group = QGroupBox()
        method_layout = QHBoxLayout(method_group)
        method_layout.addWidget(QLabel(t('deps_install_method')))
        self.method_combo = QComboBox()
        for key, code in (('deps_method_auto', 'auto'),
                          ('deps_method_pip', 'pip'),
                          ('deps_method_wheels', 'wheels'),
                          ('deps_method_folder', 'folder')):
            self.method_combo.addItem(t(key), code)
        method_layout.addWidget(self.method_combo)
        method_layout.addStretch()

        # Таблица пакетов
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([
            t('deps_col_package'), t('deps_col_purpose'), t('deps_col_status')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        # Кнопки
        buttons = QHBoxLayout()
        self.install_button = create_styled_button(
            t('deps_install_selected'), "primary", "⬇️")
        self.recheck_button = create_styled_button(
            t('deps_recheck'), "secondary", "🔄")
        buttons.addWidget(self.install_button)
        buttons.addWidget(self.recheck_button)
        buttons.addStretch()

        layout.addWidget(self.intro_label)
        layout.addWidget(method_group)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)

        self.refresh()

    def refresh(self):
        """Перечитать статус пакетов и перерисовать таблицу."""
        from ..core.deps import installer
        t = translations.get_text
        rows = installer.package_status()
        self.table.setRowCount(len(rows))
        for r, (name, _import_name, purpose_key, installed) in enumerate(rows):
            name_item = _Item(name)
            # чекбокс для выбора устанавливаемых
            name_item.setFlags(name_item.flags() | Qt.ItemIsUserCheckable)
            name_item.setCheckState(Qt.Unchecked if installed else Qt.Checked)
            name_item.setData(Qt.UserRole, name)

            purpose_item = QTableWidgetItem(t(purpose_key))
            status_text = (t('deps_status_installed') if installed
                           else t('deps_status_missing'))
            status_item = QTableWidgetItem(
                ("✅ " if installed else "⬜ ") + status_text)
            status_item.setForeground(
                QColor('#27ae60') if installed else QColor('#e67e22'))

            self.table.setItem(r, 0, name_item)
            self.table.setItem(r, 1, purpose_item)
            self.table.setItem(r, 2, status_item)

    def selected_packages(self):
        """Список pip-спецификаторов отмеченных пакетов."""
        from ..core.deps import installer
        specs = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item is not None and item.checkState() == Qt.Checked:
                name = item.data(Qt.UserRole)
                cfg = installer.PACKAGES.get(name)
                if cfg:
                    specs.append((name, cfg))
        return specs

    def selected_method(self):
        return self.method_combo.currentData()
