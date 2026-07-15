# -*- coding: utf-8 -*-
"""
Edge weights and artifact filtering (Guo 2020 §3.5).
Сопоставление точек скорректированных треков с пикселями скелета (KD-Tree),
подсчёт частоты рёбер (число треков, покрывающих ≥ половины пикселей ребра) и
удаление артефактов по (частота f, длина l) с защитой длинных редких дорог.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from collections import defaultdict

import numpy as np


def _edge_label_pixels(graph):
    """Собрать помеченные пиксели рёбер (интерьер) для сопоставления.

    Returns:
        coords (M,2) float (row,col), labels (M,) edge index,
        pixel_count (E,) число помеченных пикселей на ребро.
    """
    coords = []
    labels = []
    for e, edge in enumerate(graph.edges):
        px = edge['pixels']
        interior = px[1:-1] if len(px) >= 3 else px
        for rc in interior:
            coords.append((float(rc[0]), float(rc[1])))
            labels.append(e)
    if not coords:
        return (np.zeros((0, 2)), np.zeros(0, dtype=int),
                np.zeros(len(graph.edges), dtype=int))
    coords = np.array(coords)
    labels = np.array(labels, dtype=int)
    pixel_count = np.bincount(labels, minlength=len(graph.edges))
    return coords, labels, pixel_count


def compute_frequencies(graph, tracks, grid, half_ratio=0.5, max_dist_px=2.0):
    """Посчитать частоту каждого ребра и записать в edge['frequency'].

    Частота ребра = число треков, у которых ≥ half_ratio пикселей ребра
    оказались ближайшими к точкам трека.
    """
    from scipy.spatial import cKDTree

    coords, labels, pixel_count = _edge_label_pixels(graph)
    freq = np.zeros(len(graph.edges), dtype=int)
    if len(coords) == 0:
        for edge in graph.edges:
            edge['frequency'] = 0
        return freq

    tree = cKDTree(coords)
    for tr in tracks:
        tr = np.asarray(tr, dtype=float)
        if len(tr) == 0:
            continue
        px, py = grid.world_to_pixel(tr[:, 0], tr[:, 1])
        query = np.column_stack([py, px])   # (row, col)
        dist, idx = tree.query(query, distance_upper_bound=max_dist_px)
        hits = defaultdict(set)
        for d, gi in zip(dist, idx):
            if np.isfinite(d) and gi < len(labels):
                hits[labels[gi]].add(gi)
        for e, gis in hits.items():
            if len(gis) >= max(1, half_ratio * pixel_count[e]):
                freq[e] += 1

    for e, edge in enumerate(graph.edges):
        edge['frequency'] = int(freq[e])
    return freq


def count_devices(graph, px, py, devices, max_dist_m):
    """Проставить рёбрам 'n_devices' — число уникальных устройств рядом с ребром.

    Матчит исходные (мировые) точки с метками устройств к ближайшей вершине
    ребра в пределах max_dist_m метров и накапливает множество устройств на
    ребро (§WS-Dev). Рёбра без совпадений получают 0.
    """
    from scipy.spatial import cKDTree

    for edge in graph.edges:
        edge['n_devices'] = 0
    coords, labels = [], []
    for e, edge in enumerate(graph.edges):
        c = edge.get('coords')
        if c is None or len(c) == 0:
            continue
        for xy in np.asarray(c, dtype=float):
            coords.append((float(xy[0]), float(xy[1])))
            labels.append(e)
    if not coords:
        return
    coords = np.asarray(coords)
    labels = np.asarray(labels, dtype=int)
    tree = cKDTree(coords)
    query = np.column_stack([np.asarray(px, dtype=float),
                             np.asarray(py, dtype=float)])
    dist, idx = tree.query(query, distance_upper_bound=float(max_dist_m))
    dev = np.asarray(devices)
    per_edge = defaultdict(set)
    for d, gi, dv in zip(dist, idx, dev):
        if np.isfinite(d) and gi < len(labels):
            per_edge[labels[gi]].add(dv)
    for e, devset in per_edge.items():
        graph.edges[e]['n_devices'] = len(devset)


def filter_edges(graph, f_min=2, l_min=30.0, protect_long_m=None):
    """Удалить артефакты: рёбра с частотой < f_min И длиной < l_min.

    Длинные редкие дороги сохраняются, если length >= protect_long_m
    (защита усов/волоков, §4.4). Возвращает (graph, removed_count).
    """
    survivors = []
    removed = 0
    for edge in graph.edges:
        length = edge.get('length', 0.0)
        freq = edge.get('frequency', 0)
        protected = (protect_long_m is not None and length >= protect_long_m)
        drop = (freq < f_min and length < l_min) and not protected
        if drop:
            removed += 1
        else:
            survivors.append(edge)
    graph.edges = survivors
    _prune_orphan_nodes(graph)
    return graph, removed


def _prune_orphan_nodes(graph):
    """Убрать узлы, не участвующие ни в одном ребре."""
    used = set()
    for edge in graph.edges:
        used.add(edge['u'])
        used.add(edge['v'])
    graph.nodes = {nid: rc for nid, rc in graph.nodes.items() if nid in used}
