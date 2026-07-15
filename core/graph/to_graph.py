# -*- coding: utf-8 -*-
"""
Skeleton → graph for GPS Road Builder (Guo 2020 §3.4).
Преобразование пиксельного скелета в граф (узлы + рёбра с пиксельными путями).
Чистый numpy — не зависит от sknw. Узлы = пиксели скелета со степенью ≠ 2
(концы и развилки); рёбра — пути через пиксели степени 2 между узлами. Замкнутые
петли без узлов замыкаются в самопетли.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
            (0, 1), (1, -1), (1, 0), (1, 1)]


class RoadGraph:
    """Граф дорожной сети.

    Attributes:
        nodes: dict id -> (row, col) — пиксельные координаты узла.
        edges: список dict с ключами:
            'u', 'v'    — id узлов-концов (self-loop: u == v);
            'pixels'    — массив (K, 2) пиксельных координат пути (row, col);
            (позже) 'coords' — мировая геометрия (N, 2), 'length', 'frequency'.
    """

    def __init__(self):
        self.nodes = {}
        self.edges = []

    def edge_count(self):
        return len(self.edges)

    def node_count(self):
        return len(self.nodes)


def _neighbor_count(sk):
    """Число 8-соседей-скелетных пикселей для каждого пикселя."""
    h, w = sk.shape
    padded = np.pad(sk.astype(np.uint8), 1)
    count = np.zeros((h, w), dtype=np.uint8)
    for dr, dc in _OFFSETS:
        count += padded[1 + dr:1 + dr + h, 1 + dc:1 + dc + w]
    return count


def _neighbors(sk, r, c):
    h, w = sk.shape
    res = []
    for dr, dc in _OFFSETS:
        rr, cc = r + dr, c + dc
        if 0 <= rr < h and 0 <= cc < w and sk[rr, cc]:
            res.append((rr, cc))
    return res


def to_graph(skeleton):
    """Построить RoadGraph из бинарного скелета (1 пиксель шириной)."""
    sk = np.asarray(skeleton) > 0
    count = _neighbor_count(sk)

    graph = RoadGraph()
    node_pixels = list(zip(*np.where(sk & (count != 2) & (count > 0))))
    node_id = {p: i for i, p in enumerate(node_pixels)}
    for p, i in node_id.items():
        graph.nodes[i] = p

    used = set()   # направленные полурёбра (node, first_step)
    for p in node_pixels:
        for nb in _neighbors(sk, *p):
            if (p, nb) in used:
                continue
            used.add((p, nb))
            path = [p, nb]
            prev, cur = p, nb
            while cur not in node_id:
                nxts = [q for q in _neighbors(sk, *cur) if q != prev]
                if not nxts:
                    break
                prev, cur = cur, nxts[0]
                path.append(cur)
            if cur in node_id and len(path) >= 2:
                used.add((cur, path[-2]))
            graph.edges.append({
                'u': node_id[p],
                'v': node_id.get(cur, -1),
                'pixels': np.array(path, dtype=int),
            })

    _trace_loops(sk, count, graph)
    return graph


def _trace_loops(sk, count, graph):
    """Замкнуть петли из пикселей степени 2, не покрытые рёбрами."""
    visited = set()
    for edge in graph.edges:
        for px in edge['pixels']:
            visited.add((int(px[0]), int(px[1])))
    loop_set = {p for p in zip(*np.where(sk & (count == 2)))
                if p not in visited}
    while loop_set:
        s = next(iter(loop_set))
        loop_set.discard(s)
        nbs = _neighbors(sk, *s)
        if not nbs:
            continue
        nid = len(graph.nodes)
        graph.nodes[nid] = s
        prev, cur = s, nbs[0]
        path = [s, cur]
        while cur != s and cur in loop_set:
            loop_set.discard(cur)
            nxts = [q for q in _neighbors(sk, *cur) if q != prev]
            if not nxts:
                break
            prev, cur = cur, nxts[0]
            path.append(cur)
        graph.edges.append({
            'u': nid, 'v': nid, 'pixels': np.array(path, dtype=int)})
