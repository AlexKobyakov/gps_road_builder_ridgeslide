# -*- coding: utf-8 -*-
"""
Working CRS selection for GPS Road Builder (§4.6 of the plan).
Выбор внутреннего метрического кадра под данные. По умолчанию — data-centered
Transverse Mercator (снимает вопрос швов UTM-зон), у полюсов — азимутальная.

Геометрия экстента (центроид/размах) считается на сфере с корректной
обработкой антимеридиана. Математика — чистый numpy (тестируется без pyproj);
сам `Projector` использует pyproj (входит в QGIS).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

# За этой широтой TM/UTM вырождаются → азимутальная проекция.
POLAR_LAT = 80.0


def circular_mean_deg(lons):
    """Циркулярное среднее долгот (градусы), корректно у антимеридиана."""
    r = np.radians(np.asarray(lons, dtype=float))
    s = np.mean(np.sin(r))
    c = np.mean(np.cos(r))
    return float(np.degrees(np.arctan2(s, c)))


def _covering_arc(lons):
    """Наименьшая дуга (градусы), покрывающая все долготы, и флаг пересечения
    антимеридиана."""
    lons = np.asarray(lons, dtype=float)
    if len(lons) < 2:
        return 0.0, False
    v = np.sort(np.mod(lons, 360.0))
    gaps = np.diff(v)
    wrap = (v[0] + 360.0) - v[-1]
    max_gap = max(float(gaps.max()) if len(gaps) else 0.0, wrap)
    span = 360.0 - max_gap
    naive = float(lons.max() - lons.min())
    crosses = span < naive - 1e-9
    return span, crosses


def data_extent(lons, lats):
    """Сводка по протяжённости данных.

    Returns dict: center_lon, center_lat, lon_span, lat_span,
    crosses_antimeridian, lat_min, lat_max.
    """
    lons = np.asarray(lons, dtype=float)
    lats = np.asarray(lats, dtype=float)
    lon_span, crosses = _covering_arc(lons)
    return {
        'center_lon': circular_mean_deg(lons),
        'center_lat': float(np.mean(lats)),
        'lon_span': lon_span,
        'lat_span': float(lats.max() - lats.min()) if len(lats) else 0.0,
        'crosses_antimeridian': crosses,
        'lat_min': float(lats.min()) if len(lats) else 0.0,
        'lat_max': float(lats.max()) if len(lats) else 0.0,
    }


def working_crs_proj4(center_lon, center_lat, kind='tmerc'):
    """Proj4-строка рабочего кадра, центрированного на данных."""
    if kind == 'aeqd':
        return ('+proj=aeqd +lat_0={0:.8f} +lon_0={1:.8f} +x_0=0 +y_0=0 '
                '+datum=WGS84 +units=m +no_defs').format(center_lat, center_lon)
    # Transverse Mercator: центральный меридиан — по центру данных, k=1
    # (нулевое искажение на центральном меридиане).
    return ('+proj=tmerc +lat_0=0 +lon_0={0:.8f} +k=1 +x_0=0 +y_0=0 '
            '+datum=WGS84 +units=m +no_defs').format(center_lon)


def choose_working_crs(lons, lats):
    """Выбрать рабочую CRS под данные.

    Returns:
        (proj4_string, meta): meta содержит данные экстента и выбранный kind.
    """
    meta = data_extent(lons, lats)
    kind = 'aeqd' if abs(meta['center_lat']) >= POLAR_LAT else 'tmerc'
    meta['kind'] = kind
    proj4 = working_crs_proj4(meta['center_lon'], meta['center_lat'], kind)
    meta['proj4'] = proj4
    return proj4, meta


class Projector:
    """Преобразование между EPSG:4326 и рабочим метрическим кадром (pyproj)."""

    def __init__(self, proj4):
        from pyproj import CRS, Transformer
        self.proj4 = proj4
        self.crs = CRS.from_proj4(proj4)
        wgs84 = CRS.from_epsg(4326)
        self._fwd = Transformer.from_crs(wgs84, self.crs, always_xy=True)
        self._inv = Transformer.from_crs(self.crs, wgs84, always_xy=True)
        self.meta = {}

    def forward(self, lon, lat):
        """lon/lat (градусы) → x/y (метры). Принимает скаляры и массивы."""
        x, y = self._fwd.transform(lon, lat)
        return np.asarray(x, dtype=float), np.asarray(y, dtype=float)

    def inverse(self, x, y):
        """x/y (метры) → lon/lat (градусы)."""
        lon, lat = self._inv.transform(x, y)
        return np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)

    @classmethod
    def for_data(cls, lons, lats):
        """Построить Projector под облако точек (авто-выбор CRS)."""
        proj4, meta = choose_working_crs(lons, lats)
        projector = cls(proj4)
        projector.meta = meta
        return projector
