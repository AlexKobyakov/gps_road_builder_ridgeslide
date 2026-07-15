# -*- coding: utf-8 -*-
"""
Graph post-cleaning against fragmentation (WS-G).
Пост-обработка мирового графа для борьбы с фрагментацией результата (у Guo/skeleton
типично много коротких кусков: узлов ≈ рёбер). Два приёма:

1. `merge_degree2_chains` — склейка проходных узлов (степень 2): цепочка коротких
   рёбер между двумя развилками/концами превращается в одно ребро-полилинию.
   Геометрия сохраняется (полилиния уже несёт форму), поэтому склейка безопасна и
   всегда полезна. Резко сокращает число узлов/рёбер.
2. `remove_short_spurs` — удаление висячих коротышей (ребро с концом степени 1 и
   длиной меньше порога): типичные усы-артефакты скелетизации.

Работает с графом в МИРОВЫХ координатах (nodes: id -> (x, y); рёбра с ключами
'u','v','coords' (N×2), 'length', 'frequency'). Self-loop (u == v) сохраняется.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from collections import defaultdict

import numpy as np

from .to_graph import RoadGraph


def _orient(coords, start_xy):
    """Развернуть полилинию так, чтобы её начало было ближе к точке start_xy."""
    coords = np.asarray(coords, dtype=float)
    if len(coords) < 2:
        return coords
    d0 = (coords[0, 0] - start_xy[0]) ** 2 + (coords[0, 1] - start_xy[1]) ** 2
    d1 = (coords[-1, 0] - start_xy[0]) ** 2 + (coords[-1, 1] - start_xy[1]) ** 2
    return coords[::-1] if d1 < d0 else coords


def _concat(parts):
    """Склеить ориентированные полилинии, убирая дублирующую точку стыка."""
    out = [np.asarray(parts[0], dtype=float)]
    for p in parts[1:]:
        p = np.asarray(p, dtype=float)
        if len(p) == 0:
            continue
        out.append(p[1:] if len(p) >= 1 else p)
    return np.vstack(out)


def merge_degree2_chains(graph):
    """Склеить рёбра, проходящие через узлы степени 2, в цельные полилинии.

    Returns:
        новый RoadGraph (id узлов-развилок/концов сохраняются).
    """
    edges = graph.edges
    nodes = graph.nodes
    if not edges:
        return graph

    incid = defaultdict(list)
    for i, e in enumerate(edges):
        incid[e['u']].append(i)
        incid[e['v']].append(i)

    def is_pass_through(n):
        lst = incid[n]
        return len(lst) == 2 and lst[0] != lst[1]

    def other_end(e, n):
        return e['v'] if e['u'] == n else e['u']

    visited = [False] * len(edges)
    new_edges = []

    def _walk(start, ei):
        """Пройти цепочку от узла start по ребру ei до ближайшей развилки."""
        visited[ei] = True
        parts = [_orient(edges[ei]['coords'], nodes[start])]
        length = float(edges[ei].get('length', 0.0))
        freqs = [int(edges[ei].get('frequency', 0))]
        cur_edge = ei
        cur = other_end(edges[ei], start)
        while is_pass_through(cur):
            a, b = incid[cur]
            nxt = b if a == cur_edge else a
            if visited[nxt]:
                break
            visited[nxt] = True
            parts.append(_orient(edges[nxt]['coords'], nodes[cur]))
            length += float(edges[nxt].get('length', 0.0))
            freqs.append(int(edges[nxt].get('frequency', 0)))
            cur = other_end(edges[nxt], cur)
            cur_edge = nxt
        return {
            'u': start, 'v': cur, 'coords': _concat(parts),
            'length': length, 'frequency': max(freqs) if freqs else 0,
        }

    # 1) Цепочки, начинающиеся у развилок/концов (не проходных узлов).
    for start in list(incid.keys()):
        if is_pass_through(start):
            continue
        for ei in incid[start]:
            if not visited[ei]:
                new_edges.append(_walk(start, ei))

    # 2) Чистые циклы (все узлы проходные): непосещённые рёбра образуют петли.
    for i in range(len(edges)):
        if visited[i]:
            continue
        start = edges[i]['u']
        new_edges.append(_walk(start, i))

    result = RoadGraph()
    result.edges = new_edges
    used = set()
    for e in new_edges:
        used.add(e['u'])
        used.add(e['v'])
    for nid in used:
        if nid in nodes:
            result.nodes[nid] = nodes[nid]
    return result


def remove_short_spurs(graph, min_len):
    """Удалить висячие короткие рёбра (конец степени 1, длина < min_len).

    Итеративно: удаление одного уса может сделать соседний узел висячим.
    Returns:
        (graph, removed_count) — граф изменяется на месте.
    """
    if not min_len or min_len <= 0:
        return graph, 0
    removed_total = 0
    changed = True
    while changed:
        changed = False
        deg = defaultdict(int)
        for e in graph.edges:
            deg[e['u']] += 1
            deg[e['v']] += 1
        survivors = []
        for e in graph.edges:
            u, v = e['u'], e['v']
            length = float(e.get('length', 0.0))
            dangling = (u != v) and (deg[u] == 1 or deg[v] == 1)
            if dangling and length < min_len:
                removed_total += 1
                changed = True
            else:
                survivors.append(e)
        graph.edges = survivors
    _prune_orphans(graph)
    return graph, removed_total


def remove_small_loops(graph, min_len):
    """Удалить короткие самопетли (u == v, length < min_len).

    Такие микро-петли — паразитные «перекрестья» от скелетизации толстой маски.
    Returns:
        (graph, removed_count) — граф меняется на месте.
    """
    if not min_len or min_len <= 0:
        return graph, 0
    survivors = []
    removed = 0
    for e in graph.edges:
        if e['u'] == e['v'] and float(e.get('length', 0.0)) < min_len:
            removed += 1
        else:
            survivors.append(e)
    graph.edges = survivors
    _prune_orphans(graph)
    return graph, removed


def _prune_orphans(graph):
    used = set()
    for e in graph.edges:
        used.add(e['u'])
        used.add(e['v'])
    graph.nodes = {nid: xy for nid, xy in graph.nodes.items() if nid in used}


def postprocess_graph(graph, spur_min_m=0.0):
    """Полная пост-чистка: склейка проходных узлов (+ опц. удаление коротышей).

    Args:
        graph: RoadGraph в мировых координатах.
        spur_min_m: порог длины висячих усов (0 = не удалять).

    Returns:
        новый RoadGraph.
    """
    g = merge_degree2_chains(graph)
    if spur_min_m and spur_min_m > 0:
        remove_short_spurs(g, spur_min_m)
        g = merge_degree2_chains(g)   # усы могли открыть новые проходные цепочки
    return g
