# -*- coding: utf-8 -*-
"""
Qt worker for background dependency installation.
Фоновая установка зависимостей (обёртка над installer, без блокировки UI).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from qgis.PyQt.QtCore import QObject, pyqtSignal

from . import installer


class InstallWorker(QObject):
    """Устанавливает выбранные пакеты в отдельном потоке."""

    # received_bytes, total_bytes (для индикатора; при pip total=0 → бесконечный)
    progress = pyqtSignal(int, int)
    # строка статуса (имя пакета / строка вывода pip)
    status = pyqtSignal(str)
    # success, message_or_target
    finished = pyqtSignal(bool, str)

    def __init__(self, specs, method='auto', wheel_urls=None, folder=None):
        super().__init__()
        self.specs = list(specs)
        self.method = method
        self.wheel_urls = list(wheel_urls or [])
        self.folder = folder
        self.is_cancelled = False

    def run(self):
        """Выполняется в рабочем потоке."""
        try:
            method = self._resolve_method()
            if method == 'pip':
                target = installer.install_via_pip(
                    self.specs, progress_cb=self._on_progress,
                    cancelled_cb=self._cancelled)
            elif method == 'wheels':
                target = installer.install_via_wheels(
                    self.specs, self.wheel_urls, progress_cb=self._on_progress,
                    cancelled_cb=self._cancelled)
            elif method == 'folder':
                target = installer.install_from_folder(
                    self.specs, self.folder, progress_cb=self._on_progress,
                    cancelled_cb=self._cancelled)
            else:
                raise RuntimeError('Unknown install method: {0}'.format(method))
            self.finished.emit(True, target)
        except InterruptedError:
            self.finished.emit(False, 'cancelled')
        except Exception as exc:
            self.finished.emit(False, str(exc))

    def _resolve_method(self):
        """Разрешить 'auto' в конкретный бэкенд."""
        if self.method != 'auto':
            return self.method
        if installer.pip_available():
            return 'pip'
        if self.wheel_urls:
            return 'wheels'
        if self.folder:
            return 'folder'
        return 'pip'  # пусть pip честно сообщит об ошибке, если недоступен

    def _on_progress(self, received, total, status_text):
        if status_text:
            self.status.emit(status_text)
        self.progress.emit(int(received), int(total))

    def _cancelled(self):
        return self.is_cancelled

    def cancel(self):
        self.is_cancelled = True
