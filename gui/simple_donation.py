# -*- coding: utf-8 -*-
"""
Support / donation dialog for GPS Road Builder.
Диалог поддержки (идентичен референсному плагину garmin_export).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QFrame

from ..translation_manager import translations


class SimpleDonationDialog(QDialog):
    """Простой диалог поддержки разработки."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translations.get_text('donation_title'))
        self.setFixedSize(500, 400)
        self.setModal(True)
        self.setupUi()

    def setupUi(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        title = QLabel(translations.get_text('donation_window_title'))
        title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                padding: 10px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)

        description = QLabel(translations.get_text('donation_description'))
        description.setWordWrap(True)
        description.setTextFormat(Qt.RichText)
        description.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                color: #495057;
            }
        """)

        buttons_frame = QFrame()
        buttons_layout = QVBoxLayout(buttons_frame)
        buttons_layout.setSpacing(10)

        kofi_button = QPushButton(translations.get_text('donation_kofi'))
        kofi_button.setStyleSheet(self._button_style('#f45d22', '#e55a1f', 'white'))
        kofi_button.clicked.connect(self.openKofi)

        tbank_button = QPushButton(translations.get_text('donation_tbank'))
        tbank_button.setStyleSheet(self._button_style('#ffdd2d', '#f5d000', '#333'))
        tbank_button.clicked.connect(self.openTBank)

        github_button = QPushButton(translations.get_text('donation_github'))
        github_button.setStyleSheet(self._button_style('#24292e', '#1b1f23', 'white'))
        github_button.clicked.connect(self.openGitHub)

        buttons_layout.addWidget(kofi_button)
        buttons_layout.addWidget(tbank_button)
        buttons_layout.addWidget(github_button)

        # Кнопка «может позже» убрана (ADD4 п.6): пользователь либо жертвует, либо
        # закрывает окно системным крестиком.
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(buttons_frame)
        layout.addStretch()

        self.setStyleSheet("QDialog { background-color: white; border-radius: 10px; }")

    @staticmethod
    def _button_style(bg, hover, fg):
        return """
            QPushButton {{
                background-color: {0};
                color: {2};
                border: none;
                border-radius: 8px;
                padding: 15px 20px;
                font-weight: bold;
                font-size: 14px;
                min-height: 20px;
            }}
            QPushButton:hover {{ background-color: {1}; }}
        """.format(bg, hover, fg)

    def openKofi(self):
        QDesktopServices.openUrl(QUrl("https://ko-fi.com/kobyakov"))
        self.accept()

    def openTBank(self):
        QDesktopServices.openUrl(
            QUrl("https://www.tinkoff.ru/rm/r_nCoENhHIfi.KBsuiKmOgJ/ggPSE72306"))
        self.accept()

    def openGitHub(self):
        QDesktopServices.openUrl(QUrl("https://github.com/sponsors/AlexKobyakov"))
        self.accept()


# Совместимость имён
DonationDialog = SimpleDonationDialog
__all__ = ['SimpleDonationDialog', 'DonationDialog']
