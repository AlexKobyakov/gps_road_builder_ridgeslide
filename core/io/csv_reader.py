# -*- coding: utf-8 -*-
"""
Robust reader for heterogeneous GPS exports (CSV / XLSX).
Устойчивое чтение разнородных выгрузок: авто-определение разделителя и формата
даты, рекурсивный обход папок-месяцев, чтение чанками, нормализация в
канонический набор колонок (device, time, lat, lon).

Форматы из образцов заказчика: разделители ';' и '/', даты '2025-08-13 02:28:54'
и '12.04.2025 8:21', заголовок иногда в кавычках. См. §4.0 плана.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import os

from . import schema

# Кандидаты-разделители в порядке приоритета при равенстве частоты.
DELIMITER_CANDIDATES = (';', '/', '\t', '|', ',')

# Явные форматы даты (пробуются по очереди перед гибким разбором).
DATETIME_FORMATS = (
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%dT%H:%M:%S',
    '%d.%m.%Y %H:%M:%S',
    '%d.%m.%Y %H:%M',
    '%d.%m.%Y',
)

DATA_EXTENSIONS = ('.csv', '.xlsx', '.xls')
DEFAULT_CHUNKSIZE = 250_000


# ---------------------------------------------------------------------------
# Обнаружение файлов
# ---------------------------------------------------------------------------

def iter_data_files(root):
    """Рекурсивно обойти дерево и вернуть файлы данных.

    Yields:
        (month, path): month — имя папки-контейнера (для группировки по месяцам
        и инкрементального режима, §4.0); path — полный путь к файлу.
    Результат отсортирован по (month, path) для детерминизма.
    """
    found = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.lower().endswith(DATA_EXTENSIONS):
                month = os.path.basename(dirpath.rstrip(os.sep))
                found.append((month, os.path.join(dirpath, name)))
    found.sort(key=lambda item: (item[0], item[1]))
    return found


# ---------------------------------------------------------------------------
# Определение формата
# ---------------------------------------------------------------------------

def sniff_delimiter(header_line):
    """Определить разделитель по строке заголовка (без дат — надёжно).

    Returns:
        символ-разделитель; при неоднозначности — по приоритету
        DELIMITER_CANDIDATES; по умолчанию ';'.
    """
    line = (header_line or '').strip()
    best, best_count = ';', 0
    for cand in DELIMITER_CANDIDATES:
        count = line.count(cand)
        if count > best_count:
            best, best_count = cand, count
    return best


def _read_first_line(path, encoding='utf-8'):
    with open(path, 'r', encoding=encoding, errors='replace') as fh:
        for line in fh:
            if line.strip():
                return line.rstrip('\r\n')
    return ''


def parse_datetimes(series):
    """Разобрать столбец времени, подобрав формат (pandas).

    Пытается явные форматы (быстро/однозначно), берёт тот, что покрывает
    >80% значений; иначе — гибкий разбор с dayfirst=True.
    """
    import pandas as pd

    best = None
    best_ratio = 0.0
    for fmt in DATETIME_FORMATS:
        parsed = pd.to_datetime(series, format=fmt, errors='coerce')
        ratio = float(parsed.notna().mean()) if len(parsed) else 0.0
        if ratio > best_ratio:
            best, best_ratio = parsed, ratio
        if ratio >= 0.99:
            break
    if best is None or best_ratio < 0.8:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            best = pd.to_datetime(series, errors='coerce', dayfirst=True)
    return best


# ---------------------------------------------------------------------------
# Чтение и нормализация
# ---------------------------------------------------------------------------

def _normalize_frame(df, mapping):
    """Привести прочитанный кадр к каноническим колонкам и типам."""
    import pandas as pd

    out = pd.DataFrame()
    out[schema.DEVICE] = df[mapping[schema.DEVICE]].astype(str).str.strip()
    out[schema.LAT] = pd.to_numeric(df[mapping[schema.LAT]], errors='coerce')
    out[schema.LON] = pd.to_numeric(df[mapping[schema.LON]], errors='coerce')
    out[schema.TIME] = parse_datetimes(df[mapping[schema.TIME]])
    # Отбрасываем полностью нечитаемые строки (мусор), без диапазон-проверки —
    # диапазон и дубликаты обрабатываются в preprocess.clean.
    out = out.dropna(subset=[schema.LAT, schema.LON, schema.TIME])
    out = out[list(schema.CANONICAL_COLUMNS)]  # канонический порядок колонок
    return out.reset_index(drop=True)


def _resolve_mapping(columns, mapping):
    """Определить/проверить маппинг колонок для конкретного файла."""
    resolved = dict(mapping) if mapping else schema.detect_columns(list(columns))
    if not schema.mapping_is_complete(resolved):
        raise ValueError(
            'Cannot map required columns {0}; found columns: {1}'.format(
                schema.missing_roles(resolved), list(columns)))
    return resolved


def iter_normalized_chunks(path, mapping=None, chunksize=DEFAULT_CHUNKSIZE,
                           encoding='utf-8'):
    """Читать файл нормализованными чанками (генератор DataFrame).

    CSV читается чанками; XLSX — целиком (pandas не поддерживает chunksize).
    """
    import pandas as pd

    ext = os.path.splitext(path)[1].lower()

    if ext in ('.xlsx', '.xls'):
        df = pd.read_excel(path, dtype=str)
        resolved = _resolve_mapping(df.columns, mapping)
        yield _normalize_frame(df, resolved)
        return

    delimiter = sniff_delimiter(_read_first_line(path, encoding))
    reader = pd.read_csv(
        path, sep=delimiter, dtype=str, encoding=encoding,
        chunksize=chunksize, skip_blank_lines=True, on_bad_lines='skip')
    resolved = None
    for chunk in reader:
        if resolved is None:
            resolved = _resolve_mapping(chunk.columns, mapping)
        yield _normalize_frame(chunk, resolved)


def read_normalized(path, mapping=None, encoding='utf-8'):
    """Прочитать файл целиком в нормализованный DataFrame."""
    import pandas as pd

    chunks = list(iter_normalized_chunks(path, mapping=mapping,
                                         encoding=encoding))
    if not chunks:
        return _empty_frame()
    return pd.concat(chunks, ignore_index=True)


def load_dataset(root_or_paths, mapping=None, encoding='utf-8'):
    """Загрузить и объединить все файлы данных в один нормализованный кадр.

    Args:
        root_or_paths: путь к корневой папке (рекурсивно) ИЛИ список файлов.
    """
    import pandas as pd

    if isinstance(root_or_paths, (list, tuple)):
        paths = list(root_or_paths)
    else:
        paths = [p for _month, p in iter_data_files(root_or_paths)]

    frames = []
    for path in paths:
        frames.append(read_normalized(path, mapping=mapping, encoding=encoding))
    if not frames:
        return _empty_frame()
    return pd.concat(frames, ignore_index=True)


def _empty_frame():
    import pandas as pd
    empty = pd.DataFrame(columns=list(schema.CANONICAL_COLUMNS))
    return empty
