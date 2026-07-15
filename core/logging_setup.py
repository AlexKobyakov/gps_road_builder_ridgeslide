# -*- coding: utf-8 -*-
"""
Logging setup for GPS Road Builder.
Ротируемый файловый лог в профиле QGIS (для отладки/сбора информации, §12 ТЗ).
Работает и без QGIS (fallback в домашний каталог) — тестируется офлайн.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_LOGGER_NAME = 'gps_road_builder'


def log_dir(base_dir=None):
    """Каталог для лог-файла (профиль QGIS либо fallback)."""
    if base_dir is None:
        try:
            from qgis.core import QgsApplication
            base_dir = QgsApplication.qgisSettingsDirPath()
        except Exception:
            base_dir = None
    if not base_dir:
        base_dir = os.path.join(os.path.expanduser('~'), '.gps_road_builder')
    path = os.path.join(base_dir, 'gps_road_builder')
    os.makedirs(path, exist_ok=True)
    return path


def log_path(base_dir=None):
    return os.path.join(log_dir(base_dir), 'gps_road_builder.log')


def runs_manifest_path(base_dir=None):
    """Путь к JSONL-манифесту прогонов (одна строка «параметры→метрики» на
    прогон) — для сравнения/подбора настроек (§WS-L)."""
    return os.path.join(log_dir(base_dir), 'gps_road_builder_runs.jsonl')


def get_logger(base_dir=None):
    """Вернуть настроенный логгер (идемпотентно)."""
    logger = logging.getLogger(_LOGGER_NAME)
    if getattr(logger, '_grb_configured', False):
        return logger
    logger.setLevel(logging.INFO)
    try:
        handler = RotatingFileHandler(
            log_path(base_dir), maxBytes=5_000_000, backupCount=3,
            encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s'))
        logger.addHandler(handler)
    except Exception:
        # Не удалось открыть файл — не блокируем работу плагина
        logger.addHandler(logging.NullHandler())
    logger._grb_configured = True
    return logger
