# -*- coding: utf-8 -*-
"""
Dialogs for GPS Road Builder: About, install progress, error.
Диалоги «Об авторе», прогресс установки зависимостей и ошибки.

Диалоги «Об авторе»/«Поддержка» повторяют дизайн референсного плагина
garmin_export.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QGroupBox
)

from .gui_components import create_styled_button, ModernProgressBar
from ..translation_manager import translations
from ..qgis_compat import qt_enum


class AuthorInfoDialog(QDialog):
    """Стильное окно «Об авторе» в едином ключе с диалогом «Поддержка»;
    выделяет наш алгоритм RidgeSlide (ADD4 п.5)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            from ..plugin import GpsRoadBuilderPlugin
            self._info = GpsRoadBuilderPlugin.get_plugin_info()
        except Exception:
            self._info = {
                'name': 'GPS Road Builder',
                'version': 'Unknown',
                'author': 'Кобяков Александр Викторович',
                'email': 'kobyakov@lesburo.ru',
            }
        t = translations.get_text
        self.setWindowTitle('👤 {0}'.format(t('header_about_author')))
        self.setMinimumSize(560, 640)
        self.resize(560, 640)
        self.setModal(True)
        self.setWindowFlags(
            qt_enum('WindowType', 'Dialog')
            | qt_enum('WindowType', 'WindowTitleHint')
            | qt_enum('WindowType', 'WindowCloseButtonHint'))
        self.setupUi()
        self.retranslateUi()

    def setupUi(self):
        t = translations.get_text
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(14)

        self.title_label = QLabel()
        self.title_label.setAlignment(qt_enum('AlignmentFlag', 'AlignCenter'))
        self.title_label.setStyleSheet(
            'color: #2c3e50; font-size: 20px; font-weight: bold;')

        self.subtitle_label = QLabel()
        self.subtitle_label.setAlignment(qt_enum('AlignmentFlag', 'AlignCenter'))
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet('color: #7f8c8d; font-size: 12px;')

        self.version_label = QLabel()
        self.version_label.setAlignment(qt_enum('AlignmentFlag', 'AlignCenter'))
        self.version_label.setStyleSheet('color: #95a5a6; font-size: 11px;')

        self.algo_label = QLabel()
        self.algo_label.setWordWrap(True)
        self.algo_label.setTextFormat(qt_enum('TextFormat', 'RichText'))
        self.algo_label.setStyleSheet(self._card('#eaf4fb', '#bfe0f5'))

        self.contact_label = QLabel()
        self.contact_label.setWordWrap(True)
        self.contact_label.setTextFormat(qt_enum('TextFormat', 'RichText'))
        self.contact_label.setOpenExternalLinks(True)
        self.contact_label.setStyleSheet(self._card('#f8f9fa', '#dee2e6'))

        self.close_button = create_styled_button(t('close'), 'secondary', '✖️')
        self.close_button.clicked.connect(self.accept)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.version_label)
        layout.addWidget(self.algo_label)
        layout.addWidget(self.contact_label)
        layout.addStretch()
        layout.addWidget(
            self.close_button, 0, qt_enum('AlignmentFlag', 'AlignCenter'))
        self.setStyleSheet(
            'QDialog { background-color: white; border-radius: 10px; }')

    def retranslateUi(self):
        t = translations.get_text
        info = self._info
        self.setWindowTitle('👤 ' + t('header_about_author'))
        self.title_label.setText('🛰️ ' + info['name'])
        self.subtitle_label.setText(t('about_subtitle'))
        self.version_label.setText('📜 {0}: v{1}'.format(t('version'), info['version']))
        self.algo_label.setText('<b style="color:#2980b9;">🧠 {0}</b><br>{1}'.format(
            t('about_algorithm_title'), t('about_algorithm_text')))
        self.contact_label.setText(
            '<b>👨‍💻 {author_l}:</b> {author} <i>(Alex Kobyakov)</i><br>'
            '<b>📧 {contact_l}:</b> <a href="mailto:{email}">{email}</a><br>'
            '<b>💬 Telegram:</b> <a href="https://t.me/AKobyakov">@AKobyakov</a><br>'
            '<b>🏢 {org_l}:</b> Lesburo &nbsp;·&nbsp; <b>📅 {year_l}:</b> 2026<br>'
            '<span style="color:#7f8c8d;">{multi}</span>'.format(
                author_l=t('author'), author=info['author'], contact_l=t('contact'),
                email=info['email'], org_l=t('organization'), year_l=t('year'),
                multi=t('multilingual_support')))
        self.close_button.setText('✖️ ' + t('close'))

    @staticmethod
    def _card(bg, border):
        return ('QLabel {{ background-color: {0}; border: 1px solid {1}; '
                'border-radius: 8px; padding: 15px; color: #2c3e50; }}'
                .format(bg, border))


AuthorDialog = AuthorInfoDialog


class InstallProgressDialog(QDialog):
    """Диалог прогресса установки зависимостей."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._title = title
        self.is_cancelled = False
        self.setWindowTitle(title)
        self.setMinimumSize(500, 220)
        self.resize(500, 220)
        self.setModal(True)
        self.setWindowFlags(
            qt_enum('WindowType', 'Dialog')
            | qt_enum('WindowType', 'WindowTitleHint'))
        self.setupUi(title)
        self.retranslateUi()

    def setupUi(self, title):
        t = translations.get_text
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        header_layout = QHBoxLayout()
        icon_label = QLabel("📥")
        icon_label.setStyleSheet("font-size: 28px;")
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.status_label = QLabel(t('installing'))
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 11px; color: #7f8c8d;")

        self.progress_bar = ModernProgressBar()
        self.progress_bar.setRange(0, 0)  # бесконечный до первого прогресса

        self.cancel_button = create_styled_button(t('cancel'), "danger", "❌")
        self.cancel_button.clicked.connect(self.on_cancel)

        layout.addLayout(header_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(
            self.cancel_button, 0, qt_enum('AlignmentFlag', 'AlignCenter'))

    def on_cancel(self):
        self.is_cancelled = True
        self.cancel_button.setEnabled(False)

    def update_progress(self, received, total):
        if total > 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(int(received * 100 / total))
        # при pip (total=0) оставляем «бегущий» индикатор

    def set_status(self, text):
        # показываем последнюю строку вывода, обрезая слишком длинные
        self.status_label.setText(text if len(text) < 90 else text[:87] + '…')

    def retranslateUi(self):
        self.setWindowTitle(self._title)
        self.title_label.setText(self._title)
        if not self.status_label.text():
            self.status_label.setText(translations.get_text('installing'))
        self.cancel_button.setText('❌ ' + translations.get_text('cancel'))


class ErrorDialog(QDialog):
    """Диалог отображения ошибки с деталями."""

    def __init__(self, title, message, details="", parent=None):
        super().__init__(parent)
        self._title = title
        self._message = message
        self._details = details
        self.setupUi()
        self.retranslateUi()

    def setupUi(self):
        t = translations.get_text
        self.setWindowTitle(self._title)
        self.setMinimumSize(460, 280)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        header_layout = QHBoxLayout()
        icon_label = QLabel("❌")
        icon_label.setStyleSheet("font-size: 32px;")
        self.title_label = QLabel(self._title)
        self.title_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #e74c3c;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.message_label = QLabel(self._message)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("""
            QLabel {
                background-color: #fdeded;
                border: 2px solid #f5c6cb;
                border-radius: 8px;
                padding: 15px;
                color: #721c24;
            }
        """)

        layout.addLayout(header_layout)
        layout.addWidget(self.message_label)

        if self._details:
            self.details_group = QGroupBox()
            details_layout = QVBoxLayout(self.details_group)
            details_text = QTextEdit()
            details_text.setPlainText(self._details)
            details_text.setReadOnly(True)
            details_text.setMaximumHeight(150)
            details_text.setFont(QFont("Consolas", 9))
            details_layout.addWidget(details_text)
            layout.addWidget(self.details_group)
        else:
            self.details_group = None

        self.close_button = create_styled_button(t('close'), "danger", "❌")
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button)

    def retranslateUi(self):
        t = translations.get_text
        self.setWindowTitle(self._title)
        self.title_label.setText(self._title)
        self.message_label.setText(self._message)
        if self.details_group is not None:
            self.details_group.setTitle('📋 ' + t('details'))
        self.close_button.setText('❌ ' + t('close'))
