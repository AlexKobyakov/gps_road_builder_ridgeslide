# -*- coding: utf-8 -*-
"""
Data schema and column mapping for GPS Road Builder.
Схема данных: канонические колонки, распознавание колонок по заголовку,
валидация координат. Чистый Python (без pandas/qgis) — легко тестируется.

Канонические колонки нормализованного набора:
    device : идентификатор устройства/машины (строка)
    time   : метка времени (datetime)
    lat    : широта (float, градусы)
    lon    : долгота (float, градусы)

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

# Канонические имена ролей
DEVICE, TIME, LAT, LON = 'device', 'time', 'lat', 'lon'
CANONICAL_COLUMNS = (DEVICE, TIME, LAT, LON)

# Синонимы имён колонок во входных файлах (в нижнем регистре).
COLUMN_ALIASES = {
    DEVICE: ('device_id', 'device', 'deviceid', 'id', 'unit', 'unit_id',
             'imei', 'object', 'object_id', 'track_fid', 'track_seg_id',
             'машина', 'устройство'),
    TIME: ('navigation_dttm', 'time', 'datetime', 'timestamp', 'dttm',
           'date_time', 'dt', 'время', 'дата'),
    LAT: ('lat', 'latitude', 'y', 'широта'),
    LON: ('lon', 'lng', 'long', 'longitude', 'x', 'долгота'),
}

LAT_MIN, LAT_MAX = -90.0, 90.0
LON_MIN, LON_MAX = -180.0, 180.0


def _norm(name):
    """Нормализовать имя колонки для сопоставления."""
    return str(name).strip().strip('"\'').strip().lower()


def detect_columns(header_fields):
    """Сопоставить заголовок входного файла каноническим ролям.

    Args:
        header_fields: список имён колонок из первой строки файла.

    Returns:
        dict role -> имя_колонки_как_в_файле. Роли, которые не удалось
        сопоставить, отсутствуют в словаре.
    """
    normalized = {_norm(h): h for h in header_fields}
    mapping = {}
    for role, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[role] = normalized[alias]
                break
    return mapping


def mapping_is_complete(mapping):
    """Все ли обязательные роли (device, time, lat, lon) распознаны."""
    return all(role in mapping for role in CANONICAL_COLUMNS)


def missing_roles(mapping):
    """Список нераспознанных обязательных ролей."""
    return [role for role in CANONICAL_COLUMNS if role not in mapping]


def valid_lat(value):
    try:
        return LAT_MIN <= float(value) <= LAT_MAX
    except (TypeError, ValueError):
        return False


def valid_lon(value):
    try:
        return LON_MIN <= float(value) <= LON_MAX
    except (TypeError, ValueError):
        return False
