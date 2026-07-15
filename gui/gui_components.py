# -*- coding: utf-8 -*-
"""
GUI components for GPS Road Builder (ported from garmin_export).
Переиспользуемые стилизованные виджеты и глобальные стили.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QGroupBox, QPushButton, QProgressBar, QLabel


class ModernGroupBox(QGroupBox):
    """Стилизованная группа с современным дизайном."""

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 5px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: white;
                border-radius: 4px;
            }
        """)


class ModernButton(QPushButton):
    """Стилизованная кнопка. button_type: primary | secondary | danger | success."""

    _COLORS = {
        'primary': ('#3498db', '#2980b9', '#5dade2', '#21618c'),
        'danger': ('#e74c3c', '#c0392b', '#ec7063', '#922b21'),
        'success': ('#2ecc71', '#27ae60', '#58d68d', '#1e8449'),
    }

    def __init__(self, text="", button_type="primary", parent=None):
        super().__init__(text, parent)
        self.button_type = button_type
        self.setMinimumHeight(40)
        self.setFont(QFont("Segoe UI", 10, QFont.Medium))
        self.apply_style()

    def apply_style(self):
        colors = self._COLORS.get(self.button_type)
        if colors:
            top, bottom, hover_top, pressed_bottom = colors
            self.setStyleSheet("""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 {0}, stop:1 {1});
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 {2}, stop:1 {0});
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 {1}, stop:1 {3});
                }}
                QPushButton:disabled {{
                    background: #bdc3c7;
                    color: #7f8c8d;
                }}
            """.format(top, bottom, hover_top, pressed_bottom))
        else:  # secondary
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #ecf0f1, stop:1 #d5dbdb);
                    color: #2c3e50;
                    border: 1px solid #bdc3c7;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #f8f9fa, stop:1 #ecf0f1);
                    border: 1px solid #95a5a6;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #d5dbdb, stop:1 #bdc3c7);
                }
            """)


class ModernProgressBar(QProgressBar):
    """Стилизованный прогресс-бар."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                color: white;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #3498db, stop:1 #2ecc71);
                border-radius: 6px;
            }
        """)
        self.setMinimumHeight(25)


def apply_global_styles():
    """Глобальные стили для главного диалога."""
    return """
        QDialog {
            background-color: #f8f9fa;
        }
        QLineEdit {
            padding: 8px;
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            background-color: white;
            selection-background-color: #3498db;
        }
        QLineEdit:focus { border-color: #3498db; }
        QTextEdit {
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            background-color: white;
            padding: 8px;
        }
        QTextEdit:focus { border-color: #3498db; }
        QComboBox {
            padding: 6px 12px;
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            background-color: white;
        }
        QComboBox:focus { border-color: #3498db; }
        QComboBox::drop-down { border: none; width: 20px; }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #7f8c8d;
        }
        QSpinBox, QDoubleSpinBox {
            padding: 6px;
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            background-color: white;
        }
        QSpinBox:focus, QDoubleSpinBox:focus { border-color: #3498db; }
        QCheckBox { spacing: 8px; }
        QCheckBox::indicator {
            width: 18px; height: 18px;
            border: 2px solid #bdc3c7; border-radius: 4px;
            background-color: white;
        }
        QCheckBox::indicator:checked {
            background-color: #3498db; border-color: #3498db;
        }
        QRadioButton { spacing: 8px; }
        QRadioButton::indicator {
            width: 18px; height: 18px;
            border: 2px solid #bdc3c7; border-radius: 9px;
            background-color: white;
        }
        QRadioButton::indicator:checked {
            background-color: #3498db; border-color: #3498db;
        }
        QScrollArea { border: none; background-color: transparent; }
        QScrollBar:vertical {
            background: #ecf0f1; width: 12px; border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #bdc3c7; border-radius: 6px; min-height: 20px;
        }
        QScrollBar::handle:vertical:hover { background: #95a5a6; }
    """


def create_styled_button(text, button_class="primary", icon_text=""):
    """Создать стилизованную кнопку с иконкой."""
    label = "{0} {1}".format(icon_text, text) if icon_text else text
    return ModernButton(label, button_class)


def create_info_label(text):
    """Информационная метка с переносом строк."""
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("color: #7f8c8d;")
    return label
