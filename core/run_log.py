# -*- coding: utf-8 -*-
"""
Run logging helpers for parameter tuning (WS-L).
Чистое форматирование строк лога и run-manifest — без Qt/QGIS, тестируется
офлайн. Задача: связать РЕЗУЛЬТАТ прогона с его НАСТРОЙКАМИ и метриками этапов,
чтобы можно было рекурсивно подбирать параметры (сравнивать прогоны).

Строки лога компактны и «грепабельны» (`params | ...`, `stage | ...`).
Манифест — одна JSON-строка на прогон (диффабельно).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import json


def _g(p, key, default=''):
    v = p.get(key, default)
    return default if v is None else v


def format_params(params):
    """Сгруппированный компактный дамп резолвнутых параметров пайплайна.

    Returns:
        список строк вида 'params | <группа>: k=v ...'.
    """
    p = dict(params or {})
    lines = [
        'params | method={0} backend={1} skeleton={2} kde_radius={3} '
        'gap_buffer={4}'.format(
            _g(p, 'method'), _g(p, 'backend'), _g(p, 'skeleton_backend'),
            _g(p, 'kde_radius'), _g(p, 'gap_buffer_m')),
        'params | preprocess: v_max={0} a_max={1} reb={2} thin={3} '
        'gap_dt={4}s gap_ds={5} resample={6}'.format(
            _g(p, 'v_max_kmh'), _g(p, 'a_max'), _g(p, 'reb_enabled'),
            _g(p, 'min_point_dist'), _g(p, 'gap_dt_s'), _g(p, 'gap_ds_m'),
            _g(p, 'resample_k')),
        'params | density: cell={0} sigma1={1} sigma2={2} sharp={3} '
        'loops={4}..{5} weights={6}'.format(
            _g(p, 'cell_tau'), _g(p, 'sigma1'), _g(p, 'sigma2'),
            _g(p, 'sharpness'), _g(p, 'slide_min_loops'),
            _g(p, 'slide_max_loops'), _g(p, 'weights')),
        'params | graph: eps={0}({1}) dp={2} fmin={3} lmin={4} protect={5} '
        'spur={6} smooth={7}'.format(
            _g(p, 'eps_mode'), _g(p, 'eps_value'), _g(p, 'dp_tolerance'),
            _g(p, 'edge_f_min'), _g(p, 'edge_l_min'), _g(p, 'protect_long_m'),
            _g(p, 'spur_min_m'), _g(p, 'smooth_iters')),
        'params | scale: split={0} grid={1} maxpts={2} overlap={3} '
        'node_merge={4}'.format(
            _g(p, 'split_mode'), _g(p, 'tile_grid'),
            _g(p, 'max_points_per_tile'), _g(p, 'overlap_cells'),
            _g(p, 'node_merge_dist')),
        'params | checkpoint: cache={0!r} start={1!r} stop={2!r}'.format(
            _g(p, 'cache_dir'), _g(p, 'start_stage'), _g(p, 'stop_after')),
    ]
    return lines


def format_header(version, input_desc, libs):
    """Шапка прогона: версия, вход, доступные библиотеки."""
    return [
        'run | GPS Road Builder v{0}'.format(version),
        'run | input: {0}'.format(input_desc),
        'run | libs: {0}'.format(', '.join(libs) if libs else '—'),
    ]


def format_stage(name, metrics=None, seconds=None):
    """Строка метрик этапа: 'stage | <name> | k=v ... | Δ Xs'."""
    parts = ['stage | {0}'.format(name)]
    if metrics:
        kv = ' '.join('{0}={1}'.format(k, v) for k, v in metrics.items())
        parts.append(kv)
    if seconds is not None:
        parts.append('Δ {0:.1f}s'.format(float(seconds)))
    return ' | '.join(parts)


def manifest_line(version, params, stats):
    """Одна JSON-строка «прогон → параметры + итоговые метрики» (для диффа)."""
    record = {
        'version': version,
        'params': {k: _jsonable(v) for k, v in dict(params or {}).items()},
        'stats': {k: _jsonable(v) for k, v in dict(stats or {}).items()},
    }
    return json.dumps(record, ensure_ascii=False, sort_keys=True)


def _jsonable(value):
    """Привести значение к JSON-совместимому (кортежи→списки и т.п.)."""
    if isinstance(value, tuple):
        return list(value)
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)
