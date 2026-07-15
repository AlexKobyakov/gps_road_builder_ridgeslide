# -*- coding: utf-8 -*-
"""
Background build task (QgsTask) for GPS Road Builder.
Фоновая задача построения графа дорог поверх конвейера (core/pipeline): чтение
данных из папки/файлов, весь MVP-конвейер, прогресс/сообщения и кооперативная
отмена — без блокировки интерфейса QGIS.

Правила QgsTask (docs/PLAN_REALIZACII.md §5):
- никаких GUI-операций/print из run(); связь с UI — только через сигналы;
- кооперативная отмена через isCanceled().

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsTask, QgsMessageLog, Qgis

MESSAGE_CATEGORY = 'GPS Road Builder'


class BuildRoadGraphTask(QgsTask):
    """Фоновая задача построения графа дорог.

    params поддерживает:
        'dataframe'      — уже загруженный нормализованный DataFrame; ИЛИ
        'input_paths'    — список файлов; ИЛИ
        'input_folder'   — корневая папка (рекурсивно);
        'pipeline_params'— параметры core.pipeline.
    """

    # (доля 0..1, ключ шага) — транслируется в лог main-thread
    progressMessage = pyqtSignal(float, str)

    def __init__(self, description, params=None):
        super().__init__(description, QgsTask.CanCancel)
        self.params = dict(params or {})
        self.result_payload = None
        self.exception = None

    def _is_resuming(self):
        pp = self.params.get('pipeline_params') or {}
        return bool(pp.get('start_stage') in ('points', 'tracks')
                    and pp.get('cache_dir'))

    def _load_dataframe(self):
        df = self.params.get('dataframe')
        if df is not None:
            return df
        from ..core.io import csv_reader
        # §WS-L: при резюме с чекпоинта НЕ читаем вход (pipeline берёт данные из
        # кэша по start_stage) — экономит минуты на повторном чтении.
        if self._is_resuming():
            return csv_reader._empty_frame()
        paths = self.params.get('input_paths')
        if paths:
            return csv_reader.load_dataset(list(paths))
        folder = self.params.get('input_folder')
        if folder:
            return csv_reader.load_dataset(folder)
        return csv_reader._empty_frame()

    def _input_desc(self):
        if self._is_resuming():
            pp = self.params.get('pipeline_params') or {}
            return 'resume from stage {0!r} (cache {1})'.format(
                pp.get('start_stage'), pp.get('cache_dir'))
        paths = self.params.get('input_paths')
        if paths:
            return '{0} file(s)'.format(len(paths))
        folder = self.params.get('input_folder')
        if folder:
            return 'folder {0}'.format(folder)
        return 'dataframe'

    @staticmethod
    def _plugin_version():
        try:
            import configparser
            import os
            path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'metadata.txt')
            cfg = configparser.ConfigParser()
            cfg.read(path, encoding='utf-8')
            return cfg['general'].get('version', '?')
        except Exception:
            return '?'

    @staticmethod
    def _active_libs():
        try:
            from ..core.deps import installer
            return [name for name, _imp, _pk, ok in installer.package_status()
                    if ok]
        except Exception:
            return []

    def run(self):
        """Тяжёлая работа в фоновом потоке."""
        try:
            from ..core import pipeline, run_log
            from ..core.logging_setup import get_logger, runs_manifest_path
            logger = get_logger()

            import time
            t0 = time.time()
            self._last_t = t0
            logger.info('=== build started ===')
            for line in run_log.format_header(
                    self._plugin_version(), self._input_desc(),
                    self._active_libs()):
                logger.info(line)
            self.progressMessage.emit(0.0, 'read')
            df = self._load_dataframe()
            logger.info('stage | read | rows=%d | Δ %.1fs',
                        len(df), time.time() - t0)
            if self.isCanceled():
                return False

            def _progress(frac, message):
                self.setProgress(max(0.0, min(100.0, frac * 100.0)))
                self.progressMessage.emit(float(frac), str(message))
                now = time.time()
                logger.info('step %s (%.0f%%, +%.1fs, Δ%.1fs)', message,
                            frac * 100.0, now - t0, now - self._last_t)
                self._last_t = now

            result = pipeline.build_road_graph(
                df, params=self.params.get('pipeline_params'),
                progress=_progress, is_cancelled=self.isCanceled,
                log=logger.info)
            if result is None:
                logger.info('build cancelled after %.1fs', time.time() - t0)
                return False   # отменено
            self.result_payload = result
            logger.info('build finished in %.1fs; stats=%s',
                        time.time() - t0, result.get('stats'))
            # §WS-L: компактная запись «параметры→метрики» для диффа прогонов.
            try:
                with open(runs_manifest_path(), 'a', encoding='utf-8') as fh:
                    fh.write(run_log.manifest_line(
                        self._plugin_version(), result.get('params'),
                        result.get('stats')) + '\n')
            except Exception:  # pragma: no cover - defensive
                pass
            return True
        except Exception as exc:  # pragma: no cover - defensive
            self.exception = exc
            try:
                from ..core.logging_setup import get_logger
                get_logger().exception('Build task failed')
            except Exception:
                pass
            return False

    def finished(self, result):
        """Вызывается в main-thread по завершении run() (логирование)."""
        if self.exception is not None:
            QgsMessageLog.logMessage(
                'Build failed: {0}'.format(self.exception),
                MESSAGE_CATEGORY, Qgis.Critical)
        elif not result:
            QgsMessageLog.logMessage('Build cancelled', MESSAGE_CATEGORY, Qgis.Info)
        else:
            QgsMessageLog.logMessage('Build finished', MESSAGE_CATEGORY, Qgis.Info)
