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

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QGroupBox
)

from .gui_components import create_styled_button, ModernProgressBar
from ..translation_manager import translations


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
        self.setFixedSize(560, 640)
        self.setModal(True)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setupUi()

    def setupUi(self):
        t = translations.get_text
        info = self._info
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(14)

        title = QLabel('🛰️ {0}'.format(info['name']))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            'color: #2c3e50; font-size: 20px; font-weight: bold;')

        subtitle = QLabel(t('about_subtitle'))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet('color: #7f8c8d; font-size: 12px;')

        version = QLabel('📜 {0}: v{1}'.format(t('version'), info['version']))
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet('color: #95a5a6; font-size: 11px;')

        algo = QLabel('<b style="color:#2980b9;">🧠 {0}</b><br>{1}'.format(
            t('about_algorithm_title'), t('about_algorithm_text')))
        algo.setWordWrap(True)
        algo.setTextFormat(Qt.RichText)
        algo.setStyleSheet(self._card('#eaf4fb', '#bfe0f5'))

        contact = QLabel(
            '<b>👨‍💻 {author_l}:</b> {author} <i>(Alex Kobyakov)</i><br>'
            '<b>📧 {contact_l}:</b> <a href="mailto:{email}">{email}</a><br>'
            '<b>💬 Telegram:</b> '
            '<a href="https://t.me/AKobyakov">@AKobyakov</a><br>'
            '<b>🏢 {org_l}:</b> Lesburo &nbsp;·&nbsp; '
            '<b>📅 {year_l}:</b> 2026<br>'
            '<span style="color:#7f8c8d;">{multi}</span>'.format(
                author_l=t('author'), author=info['author'],
                contact_l=t('contact'), email=info['email'],
                org_l=t('organization'), year_l=t('year'),
                multi=t('multilingual_support')))
        contact.setWordWrap(True)
        contact.setTextFormat(Qt.RichText)
        contact.setOpenExternalLinks(True)
        contact.setStyleSheet(self._card('#f8f9fa', '#dee2e6'))

        close_button = create_styled_button(t('close'), 'secondary', '✖️')
        close_button.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(version)
        layout.addWidget(algo)
        layout.addWidget(contact)
        layout.addStretch()
        layout.addWidget(close_button, 0, Qt.AlignCenter)
        self.setStyleSheet(
            'QDialog { background-color: white; border-radius: 10px; }')

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
        self.is_cancelled = False
        self.setWindowTitle(title)
        self.setFixedSize(500, 220)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        self.setupUi(title)

    def setupUi(self, title):
        t = translations.get_text
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        header_layout = QHBoxLayout()
        icon_label = QLabel("📥")
        icon_label.setStyleSheet("font-size: 28px;")
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
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
        layout.addWidget(self.cancel_button, 0, Qt.AlignCenter)

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


class ErrorDialog(QDialog):
    """Диалог отображения ошибки с деталями."""

    def __init__(self, title, message, details="", parent=None):
        super().__init__(parent)
        self._title = title
        self._message = message
        self._details = details
        self.setupUi()

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
        title_label = QLabel(self._title)
        title_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #e74c3c;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        message_label = QLabel(self._message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            QLabel {
                background-color: #fdeded;
                border: 2px solid #f5c6cb;
                border-radius: 8px;
                padding: 15px;
                color: #721c24;
            }
        """)

        layout.addLayout(header_layout)
        layout.addWidget(message_label)

        if self._details:
            details_group = QGroupBox('📋 {0}'.format(t('details')))
            details_layout = QVBoxLayout(details_group)
            details_text = QTextEdit()
            details_text.setPlainText(self._details)
            details_text.setReadOnly(True)
            details_text.setMaximumHeight(150)
            details_text.setFont(QFont("Consolas", 9))
            details_layout.addWidget(details_text)
            layout.addWidget(details_group)

        close_button = create_styled_button(t('close'), "danger", "❌")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
