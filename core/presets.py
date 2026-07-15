# -*- coding: utf-8 -*-
"""
Parameter presets and settings→pipeline mapping for GPS Road Builder.
Пресеты под типовые сценарии ДВ и сборка параметров пайплайна из настроек
(значения UI/QSettings → аргументы core.pipeline). Чистый Python — тестируется
без QGIS.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

# Пресеты задают частичные наборы настроек (ключи settings_manager.DEFAULTS).
PRESETS = {
    'mixed': {
        'min_point_dist': 10.0,
        'cell_tau': 5.0, 'sigma1': 5.0, 'sigma2': 3.0, 'sharpness': 1.5,
        'eps_mode': 'otsu', 'edge_f_min': 2, 'edge_l_min': 30.0,
        'protect_long_edges': True,
    },
    'highway': {
        'min_point_dist': 10.0,
        'cell_tau': 8.0, 'sigma1': 5.0, 'sigma2': 3.0, 'sharpness': 1.0,
        'eps_mode': 'otsu', 'edge_f_min': 3, 'edge_l_min': 50.0,
        'protect_long_edges': False,
    },
    'spurs': {
        'min_point_dist': 5.0,
        'cell_tau': 4.0, 'sigma1': 6.0, 'sigma2': 4.0, 'sharpness': 2.0,
        'eps_mode': 'adaptive', 'edge_f_min': 1, 'edge_l_min': 20.0,
        'protect_long_edges': True,
    },
    # --- Сценарные пресеты (Спринт 10): движок метод-агностичен, эти наборы —
    # стартовые предположения о данных для нелесных сценариев. Значения ОРИЕНТИРЫ,
    # почти всегда требуют подгонки (см. «не отчаивайся» в USER_GUIDE). ---
    #
    # Плотные треки бега/вело/пешие: фиксы 1–5 с, треки густо перекрываются →
    # поверхность после Slide бимодальна, Otsu работает. Мелкая ячейка под узкие
    # тропы, короткий ресэмпл (данные и так плотные — раздутия точек нет).
    'dense_tracks': {
        'method': 'slide', 'slide_backend': 'auto', 'min_point_dist': 5.0,
        'gap_dt_min': 5.0, 'gap_ds_m': 300.0, 'resample_k': 5.0,
        'cell_tau': 4.0, 'sigma1': 4.0, 'sigma2': 2.0, 'sharpness': 1.5,
        'eps_mode': 'otsu', 'edge_f_min': 2, 'edge_l_min': 20.0,
        'protect_long_edges': True, 'smooth_iters': 1,
    },
    # Городской транспорт/логистика: авто по улицам, есть склады/стоянки (горячие
    # точки) → перцентильный порог устойчивее Otsu; выше f_min отсекает единичные
    # объезды и оставляет оживлённые дороги. Средняя ячейка.
    'urban_logistics': {
        'method': 'slide', 'slide_backend': 'auto', 'min_point_dist': 10.0,
        'gap_dt_min': 10.0, 'gap_ds_m': 500.0, 'resample_k': 15.0,
        'cell_tau': 6.0, 'sigma1': 5.0, 'sigma2': 3.0, 'sharpness': 1.5,
        'eps_mode': 'percentile', 'eps_percentile': 50.0,
        'edge_f_min': 4, 'edge_l_min': 30.0,
        'protect_long_edges': False, 'spur_min_m': 30.0, 'smooth_iters': 1,
    },
    # OSM-трейсы: публичные GPS-треки разной плотности и качества → перцентильный
    # порог для устойчивости к разнородности; умеренные ячейка и ресэмпл.
    'osm_traces': {
        'method': 'slide', 'slide_backend': 'auto', 'min_point_dist': 8.0,
        'gap_dt_min': 10.0, 'gap_ds_m': 700.0, 'resample_k': 20.0,
        'cell_tau': 6.0, 'sigma1': 5.0, 'sigma2': 3.0, 'sharpness': 1.5,
        'eps_mode': 'percentile', 'eps_percentile': 45.0,
        'edge_f_min': 2, 'edge_l_min': 30.0,
        'protect_long_edges': True, 'smooth_iters': 1,
    },
    # Разрежённые данные (ФГИС ЛК, фикс 15 мин / 5 км) методом Slide —
    # рекомендуемый путь: Slide накапливает плотность по всем точкам в связные
    # гребни дорог (в отличие от KDE, где Otsu режет выше дорог). ВАЖНО:
    # бэкенд numba (не numpy!) и КРУПНЫЙ ресэмпл — иначе мелкий K раздувает
    # разрежённые точки в десятки млн (грабли §3) и прогон идёт часами.
    'sparse_slide': {
        'method': 'slide', 'slide_backend': 'auto', 'min_point_dist': 15.0,
        'gap_dt_min': 20.0, 'gap_ds_m': 700.0, 'resample_k': 50.0,
        'cell_tau': 10.0, 'sigma1': 6.0, 'sigma2': 3.0, 'sharpness': 1.5,
        # Перцентильный порог, а НЕ Otsu: per-tile Otsu «выбивается» на горячих
        # точках (склады/посёлки) и теряет дороги в таких тайлах. Перцентиль
        # адаптивен к масштабу тайла. Ниже перцентиль = гуще сеть (больше дорог).
        'eps_mode': 'percentile', 'eps_percentile': 40.0,
        'edge_f_min': 1, 'edge_l_min': 50.0,
        'protect_long_edges': True, 'spur_min_m': 30.0, 'smooth_iters': 2,
    },
    # Разрежённые данные методом Slide, но ТОЧНЕЕ (ближе к эталону) ценой
    # времени: мельче ячейка/ресэмпл, меньше сглаживания, чистка микро-петель.
    # Заметно дольше обычного sparse — обязательно numba (ADD4 п.3).
    'sparse_slide_accurate': {
        'method': 'slide', 'slide_backend': 'auto', 'min_point_dist': 15.0,
        'gap_dt_min': 20.0, 'gap_ds_m': 700.0, 'resample_k': 20.0,
        'cell_tau': 6.0, 'sigma1': 6.0, 'sigma2': 3.0, 'sharpness': 1.5,
        'eps_mode': 'percentile', 'eps_percentile': 40.0,
        'loop_min_m': 40.0, 'edge_f_min': 1, 'edge_l_min': 50.0,
        'protect_long_edges': True, 'spur_min_m': 30.0, 'smooth_iters': 1,
    },
    # Разрежённые суда/AIS: отчёты редки, судоходные коридоры широкие и покрывают
    # огромные акватории → крупные ячейка/ресэмпл и большие гэпы сегментации,
    # перцентильный порог. Как sparse_slide, но крупнее по масштабу.
    'sparse_ais': {
        'method': 'slide', 'slide_backend': 'auto', 'min_point_dist': 20.0,
        'gap_dt_min': 30.0, 'gap_ds_m': 2000.0, 'resample_k': 100.0,
        'cell_tau': 20.0, 'sigma1': 6.0, 'sigma2': 3.0, 'sharpness': 1.5,
        'eps_mode': 'percentile', 'eps_percentile': 50.0,
        'edge_f_min': 1, 'edge_l_min': 100.0,
        'protect_long_edges': True, 'spur_min_m': 50.0, 'smooth_iters': 2,
    },
    # Разрежённые данные методом KDE — ЭКСПЕРИМЕНТАЛЬНЫЙ (лучше sparse_slide).
    # Порог по перцентилю (Otsu режет выше дорог), заполнение дыр маски и
    # удаление микро-петель против «перекрестий» скелета (§WS-KDE).
    'fgis_kde': {
        'method': 'kde', 'min_point_dist': 10.0,
        'cell_tau': 10.0, 'kde_radius': 50.0, 'gap_buffer_m': 40.0,
        'eps_mode': 'percentile', 'eps_percentile': 75.0,
        'fill_holes_m': 30.0, 'loop_min_m': 40.0,
        'edge_f_min': 1, 'edge_l_min': 50.0,
        'protect_long_edges': True, 'smooth_iters': 2,
    },
}

PRESET_ORDER = ('mixed', 'highway', 'spurs',
                'dense_tracks', 'urban_logistics', 'osm_traces',
                'sparse_slide', 'sparse_slide_accurate', 'sparse_ais',
                'fgis_kde')


def preset_settings(name):
    """Вернуть словарь настроек пресета (копию)."""
    return dict(PRESETS.get(name, PRESETS['mixed']))


def save_preset(path, values):
    """Сохранить пользовательский пресет (набор настроек) в JSON-файл."""
    import json
    serializable = {k: (list(v) if isinstance(v, tuple) else v)
                    for k, v in values.items()}
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(serializable, fh, ensure_ascii=False, indent=2)
    return path


def load_preset(path):
    """Загрузить пользовательский пресет из JSON-файла (dict настроек)."""
    import json
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _get(s, key, default):
    value = s.get(key, default)
    return default if value is None else value


def build_pipeline_params(s):
    """Собрать параметры core.pipeline из словаря настроек.

    Args:
        s: dict со значениями настроек (settings_manager ключи).

    Returns:
        dict параметров для pipeline.build_road_graph.
    """
    protect_long = bool(_get(s, 'protect_long_edges', True))
    edge_l_min = float(_get(s, 'edge_l_min', 30.0))
    # «Порог адаптивный» пока сводим к Otsu (адаптивная бинаризация — Фаза 5+).
    eps_mode = str(_get(s, 'eps_mode', 'otsu'))
    if eps_mode == 'adaptive':
        eps_mode = 'otsu'

    params = {
        'v_max_kmh': float(_get(s, 'v_max_kmh', 70.0)),
        'a_max': float(_get(s, 'a_max', 4.0)),
        'reb_enabled': bool(_get(s, 'reb_enabled', False)),
        'min_point_dist': float(_get(s, 'min_point_dist', 10.0)),
        'gap_dt_s': float(_get(s, 'gap_dt_min', 5.0)) * 60.0,
        'gap_ds_m': float(_get(s, 'gap_ds_m', 500.0)),
        'resample_k': float(_get(s, 'resample_k', 5.0)),
        'cell_tau': float(_get(s, 'cell_tau', 5.0)),
        'sigma1': float(_get(s, 'sigma1', 5.0)),
        'sigma2': float(_get(s, 'sigma2', 3.0)),
        'sharpness': float(_get(s, 'sharpness', 1.5)),
        'slide_min_loops': int(_get(s, 'slide_min_loops', 100)),
        'slide_max_loops': int(_get(s, 'slide_max_loops', 4000)),
        'eps_mode': eps_mode,
        'eps_value': float(_get(s, 'eps_value', 0.0)),
        'eps_percentile': float(_get(s, 'eps_percentile', 80.0)),
        'fill_holes_m': float(_get(s, 'fill_holes_m', 0.0)),
        'loop_min_m': float(_get(s, 'loop_min_m', 0.0)),
        'dp_tolerance': float(_get(s, 'dp_tolerance', 2.0)),
        'edge_f_min': int(_get(s, 'edge_f_min', 2)),
        'edge_l_min': edge_l_min,
        'spur_min_m': float(_get(s, 'spur_min_m', 0.0)),
        'smooth_iters': int(_get(s, 'smooth_iters', 0)),
        'protect_long_m': (max(200.0, 5.0 * edge_l_min) if protect_long
                           else None),
        'split_mode': str(_get(s, 'split_mode', 'auto')),
        'method': str(_get(s, 'method', 'slide')),
        'kde_radius': float(_get(s, 'kde_radius', 50.0)),
        'gap_buffer_m': float(_get(s, 'gap_buffer_m', 30.0)),
        'slide_close_gaps_m': float(_get(s, 'slide_close_gaps_m', 0.0)),
        'connect_gap_m': float(_get(s, 'connect_gap_m', 0.0)),
        'bridge_facing_m': float(_get(s, 'bridge_facing_m', 0.0)),
        'stitch_max_m': float(_get(s, 'stitch_max_m', 0.0)),
        'break_crossings': bool(_get(s, 'break_crossings', False)),
        'junction_m': float(_get(s, 'junction_m', 0.0)),
        'min_component_m': float(_get(s, 'min_component_m', 0.0)),
        'keep_largest': bool(_get(s, 'keep_largest', False)),
        'backend': str(_get(s, 'slide_backend', 'auto')),
        'skeleton_backend': str(_get(s, 'skeleton_backend', 'auto')),
    }
    return params
