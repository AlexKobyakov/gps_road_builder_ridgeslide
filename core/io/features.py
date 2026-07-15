# -*- coding: utf-8 -*-
"""
Road-graph → feature records for GPS Road Builder.
Преобразование графа (рёбра с географической геометрией) в простые записи-фичи,
пригодные для сборки слоя QGIS или экспорта. Чистый Python — тестируется без
QGIS.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np


def road_graph_features(graph):
    """Список фич по рёбрам графа.

    Каждая фича: dict с ключами id, frequency, length, coords_lonlat (N×2).
    Рёбра без валидной географической геометрии пропускаются.
    """
    features = []
    for i, edge in enumerate(graph.edges):
        ll = edge.get('coords_lonlat')
        if ll is None:
            continue
        ll = np.asarray(ll, dtype=float)
        if len(ll) < 2:
            continue
        features.append({
            'id': i,
            'frequency': int(edge.get('frequency', 0)),
            'length': float(edge.get('length', 0.0)),
            'road_class': str(edge.get('road_class', '')),
            'reconstructed': int(edge.get('reconstructed', 0)),
            'n_devices': int(edge.get('n_devices', 0)),
            'coords_lonlat': ll,
        })
    return features


def features_to_geojson(features):
    """Собрать FeatureCollection (dict) в WGS84 из списка фич."""
    gj = {'type': 'FeatureCollection', 'features': []}
    for f in features:
        coords = [[float(x), float(y)] for x, y in f['coords_lonlat']]
        gj['features'].append({
            'type': 'Feature',
            'geometry': {'type': 'LineString', 'coordinates': coords},
            'properties': {'id': f['id'], 'frequency': f['frequency'],
                           'length': round(f['length'], 3),
                           'road_class': f.get('road_class', ''),
                           'reconstructed': f.get('reconstructed', 0),
                           'n_devices': f.get('n_devices', 0)},
        })
    return gj


def frequency_values(features):
    """Массив частот рёбер (для гистограммы/стилизации)."""
    return np.array([f['frequency'] for f in features], dtype=float)


def length_values(features):
    """Массив длин рёбер (метры)."""
    return np.array([f['length'] for f in features], dtype=float)
