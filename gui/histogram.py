# -*- coding: utf-8 -*-
"""
Lightweight histogram widget (QPainter, no matplotlib).
Компактная гистограмма для обзора распределения частот/длин рёбер (§8.1).
Расчёт — в core.histogram (чистый numpy), отрисовка — здесь.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QPainter, QColor, QBrush
from qgis.PyQt.QtWidgets import QWidget

from ..core import histogram as hist_core


class HistogramWidget(QWidget):
    """Простой бар-график распределения значений."""

    def __init__(self, title='', parent=None):
        super().__init__(parent)
        self._title = title
        self._counts = []
        self._edges = []
        self.setMinimumHeight(120)

    def sizeHint(self):
        return QSize(280, 140)

    def set_title(self, title):
        self._title = title
        self.update()

    def set_values(self, values, bins=12, scale='log'):
        counts, edges = hist_core.compute_histogram(
            values, bins=bins, scale=scale)
        self._counts = list(counts)
        self._edges = list(edges)
        self.update()

    def clear(self):
        self._counts = []
        self._edges = []
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, QColor('#ffffff'))

        pad = 8
        top = 22 if self._title else pad
        painter.setPen(QColor('#2c3e50'))
        if self._title:
            painter.drawText(pad, 16, self._title)

        if not self._counts:
            painter.setPen(QColor('#95a5a6'))
            painter.drawText(pad, h // 2, '—')
            return

        n = len(self._counts)
        max_c = max(self._counts) or 1
        avail_w = w - 2 * pad
        label_h = 12 if self._edges else 0
        avail_h = h - top - pad - label_h
        bar_w = max(1.0, avail_w / n)
        painter.setBrush(QBrush(QColor('#3498db')))
        painter.setPen(Qt.NoPen)
        for i, c in enumerate(self._counts):
            bh = (c / max_c) * avail_h
            x = pad + i * bar_w
            painter.drawRect(int(x), int(top + avail_h - bh),
                             int(max(1, bar_w - 1)), int(bh))

        # Подписи диапазона значений (корзины могут быть лог-растянутыми).
        if self._edges:
            painter.setPen(QColor('#95a5a6'))
            baseline = top + avail_h + label_h - 2
            painter.drawText(pad, int(baseline), self._fmt(self._edges[0]))
            right = self._fmt(self._edges[-1])
            painter.drawText(w - pad - 8 * len(right), int(baseline), right)

    @staticmethod
    def _fmt(value):
        value = float(value)
        if value >= 1000:
            return '{0:.0f}k'.format(value / 1000.0)
        if value >= 10 or value == int(value):
            return '{0:.0f}'.format(value)
        return '{0:.1f}'.format(value)
