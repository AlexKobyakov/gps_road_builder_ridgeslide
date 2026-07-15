# -*- coding: utf-8 -*-
"""
Settings Manager for GPS Road Builder
Хранение настроек плагина между сеансами (QSettings).

Ключи соответствуют параметрам плана (docs/PLAN_REALIZACII.md, §8). В Фазе 0
используется каркас; значения по умолчанию — стартовые под лесные дороги.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from qgis.PyQt.QtCore import QSettings

GROUP = 'gps_road_builder'

# Ключ: значение по умолчанию
DEFAULTS = {
    # Интерфейс
    'language': '',              # пусто = авто/локаль QGIS

    # Данные / вывод
    'input_source': 'files',     # files | layer | vfile (§WS-Input)
    'input_vfile': '',           # путь к файлу GPX/KML/SHP (для input_source=vfile)
    'input_folder': '',
    'output_folder': '',
    'output_crs': 'EPSG:4326',   # решение заказчика (§12)
    'split_seasons': False,      # по умолчанию всё вместе (§12)

    # Предобработка
    'min_point_dist': 10.0,      # near-dup прореживание, м (0 = выкл), §A3
    'resample_k': 5.0,           # шаг ресэмпла, м
    'v_max_kmh': 70.0,           # физфильтр скорости
    'a_max': 4.0,                # физфильтр ускорения, м/с²
    'reb_enabled': False,        # REB/anti-spoofing фильтр (§WS-G)
    'gap_dt_min': 5.0,           # гэп сегментации по времени, мин
    'gap_ds_m': 500.0,           # гэп сегментации по расстоянию, м

    # Плотность / Slide
    'cell_tau': 5.0,             # размер ячейки, м (крупнее = быстрее/меньше память)
    'sigma1': 5.0,               # размытие до Slide, px
    'sigma2': 3.0,               # размытие после Slide, px
    'sharpness': 1.5,            # заострённость ядра (0 = чистый гаусс)
    'slide_min_loops': 100,
    'slide_max_loops': 4000,

    # Граф
    'eps_mode': 'manual',        # auto | manual | adaptive | percentile
    'eps_value': 0.0,
    'eps_percentile': 80.0,      # перцентиль порога плотности (§WS-KDE)
    'fill_holes_m': 0.0,         # заполнять дыры маски < размера, м (§WS-KDE)
    'loop_min_m': 0.0,           # удалять микро-петли короче, м (§WS-KDE)
    'dp_tolerance': 2.0,         # Douglas-Peucker, м
    'edge_f_min': 2,             # мин. частота ребра
    'edge_l_min': 30.0,          # мин. длина ребра, м
    'spur_min_m': 0.0,           # удаление висячих усов < длины (0 = выкл), §WS-G
    'smooth_iters': 0,           # сглаживание рёбер Chaikin (0 = выкл), §WS-Smooth
    'protect_long_edges': True,  # не резать длинные редкие усы (§4.4)

    # Метод и бэкенды (§WS-B/WS-H)
    'method': 'slide',           # slide (плотные) | kde (разрежённые, ФГИС ЛК)
    'kde_radius': 50.0,          # радиус KDE-ядра, м
    'gap_buffer_m': 30.0,        # закрытие разрывов (KDE), м
    'slide_close_gaps_m': 0.0,   # закрытие маски дилатацией для Slide (§WS-Conn)
    'slide_backend': 'auto',     # auto | numba | numpy
    'skeleton_backend': 'auto',  # auto | skimage | zhang_suen

    # Связность / постобработка (§WS-Conn/WS-Post)
    'connect_gap_m': 0.0,        # сшивка висячих концов в радиусе, м (0 = выкл)
    'bridge_facing_m': 0.0,      # направленный мост встречных тупиков, м (0=выкл)
    'stitch_max_m': 0.0,         # сшивка компонент в одну сеть, м (0 = выкл)
    'break_crossings': False,    # разрез пересечений без узла (GRASS break, §WS-Break)
    'junction_m': 0.0,           # junction-консолидация кластеров узлов, м (0=выкл)
    'min_component_m': 0.0,      # удалять компоненты короче, м (0 = выкл)
    'keep_largest': False,       # оставить только крупнейшую компоненту

    # Область интереса (§WS-AOI)
    'aoi_source': '',            # '' | 'file' | 'layer'
    'aoi_path': '',              # путь к файлу полигона (для aoi_source='file')

    # Масштаб (split-and-merge)
    'split_mode': 'auto',        # auto | forced | off

    # Зависимости
    'deps_install_method': 'auto',   # auto | pip | wheels | folder
}

_BOOL_KEYS = {'split_seasons', 'protect_long_edges', 'reb_enabled',
              'keep_largest', 'break_crossings'}
_INT_KEYS = {'slide_min_loops', 'slide_max_loops', 'edge_f_min', 'smooth_iters'}
_FLOAT_KEYS = {
    'min_point_dist', 'resample_k', 'v_max_kmh', 'a_max', 'gap_dt_min',
    'gap_ds_m', 'cell_tau', 'sigma1', 'sigma2', 'sharpness', 'eps_value',
    'dp_tolerance', 'edge_l_min', 'spur_min_m', 'kde_radius', 'gap_buffer_m',
    'slide_close_gaps_m', 'connect_gap_m', 'min_component_m',
    'eps_percentile', 'fill_holes_m', 'loop_min_m',
    'bridge_facing_m', 'stitch_max_m', 'junction_m',
}


class SettingsManager:
    """Чтение и запись настроек плагина с приведением типов."""

    def __init__(self):
        self._settings = QSettings()

    def _key(self, name):
        return '{0}/{1}'.format(GROUP, name)

    def get(self, name):
        default = DEFAULTS.get(name, '')
        value = self._settings.value(self._key(name), default)

        if name in _BOOL_KEYS:
            if isinstance(value, bool):
                return value
            return str(value).lower() in ('true', '1', 'yes')
        if name in _INT_KEYS:
            try:
                return int(value)
            except (TypeError, ValueError):
                return int(default)
        if name in _FLOAT_KEYS:
            try:
                return float(value)
            except (TypeError, ValueError):
                return float(default)
        return '' if value is None else str(value)

    def set(self, name, value):
        self._settings.setValue(self._key(name), value)

    def get_all(self):
        return {name: self.get(name) for name in DEFAULTS}

    def set_many(self, values):
        for name, value in values.items():
            if name in DEFAULTS:
                self.set(name, value)
