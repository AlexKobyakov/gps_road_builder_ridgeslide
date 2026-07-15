# -*- coding: utf-8 -*-
"""
Graph merging and boundary fixing (Guo 2020 §4).
Слияние близких узлов (одновременно чистит кластеры узлов на перекрёстках —
следствие 8-связности — и сшивает графы соседних тайлов) и объединение графов
тайлов. Работает с графом в МИРОВЫХ координатах.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from collections import defaultdict

import numpy as np

from ..graph.to_graph import RoadGraph
from ..graph import simplify as simplify_mod


def to_world_graph(graph, grid):
    """Преобразовать граф с пиксельными узлами в граф с мировыми координатами.

    Рёбра уже несут мировую геометрию 'coords'/'length'/'frequency' (после
    simplify_graph); переносятся как есть. Узлы переводятся в мир по grid.
    """
    world = RoadGraph()
    for nid, rc in graph.nodes.items():
        xy = simplify_mod.pixels_to_world(np.array([rc], dtype=float), grid)[0]
        world.nodes[nid] = (float(xy[0]), float(xy[1]))
    world.edges = graph.edges
    return world


class _UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, a):
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def merge_close_nodes(graph, dist, dedup_length_tol=5.0):
    """Слить узлы графа (мировые координаты) в пределах `dist` метров.

    - кластеры близких узлов заменяются одним узлом в центроиде;
    - рёбра перецепляются к новым узлам;
    - короткие самопетли (обе вершины слились, length < 2·dist) удаляются как
      артефакты «кустистых» перекрёстков;
    - дубликаты рёбер (одна пара вершин, близкая длина) объединяются с суммой
      частот (устраняет двойной учёт в полосах перекрытия).

    Returns:
        новый RoadGraph.
    """
    from scipy.spatial import cKDTree

    ids = list(graph.nodes)
    if not ids:
        return graph
    index = {nid: k for k, nid in enumerate(ids)}
    coords = np.array([graph.nodes[nid] for nid in ids], dtype=float)

    uf = _UnionFind(len(ids))
    if len(ids) > 1 and dist > 0:
        tree = cKDTree(coords)
        for a, b in tree.query_pairs(dist):
            uf.union(a, b)

    members = defaultdict(list)
    for k in range(len(ids)):
        members[uf.find(k)].append(k)

    rep_to_new = {}
    result = RoadGraph()
    for new_id, (rep, mem) in enumerate(members.items()):
        pts = coords[mem]
        result.nodes[new_id] = (float(pts[:, 0].mean()), float(pts[:, 1].mean()))
        rep_to_new[rep] = new_id

    def new_node(old_id):
        return rep_to_new[uf.find(index[old_id])]

    seen = defaultdict(list)
    for edge in graph.edges:
        if edge['u'] not in index or edge['v'] not in index:
            continue
        u = new_node(edge['u'])
        v = new_node(edge['v'])
        length = float(edge.get('length', 0.0))
        if u == v and length < 2.0 * dist:
            continue                                   # артефакт-стаб
        key = frozenset((u, v))
        merged = False
        for existing in seen[key]:
            if abs(existing.get('length', 0.0) - length) <= dedup_length_tol:
                existing['frequency'] = (existing.get('frequency', 0)
                                         + edge.get('frequency', 0))
                merged = True
                break
        if not merged:
            ne = dict(edge)
            ne['u'], ne['v'] = u, v
            result.edges.append(ne)
            seen[key].append(ne)
    return result


def merge_graphs(world_graphs, lambda_dis):
    """Объединить графы тайлов в один с последующим слиянием границ.

    Args:
        world_graphs: список RoadGraph в общем мировом кадре.
        lambda_dis: порог слияния узлов на границах (обычно 3·τ·σ).
    """
    combined = RoadGraph()
    offset = 0
    for g in world_graphs:
        if g is None:
            continue
        idmap = {}
        for nid, xy in g.nodes.items():
            combined.nodes[offset] = xy
            idmap[nid] = offset
            offset += 1
        for edge in g.edges:
            if edge['u'] not in idmap or edge['v'] not in idmap:
                continue
            ne = dict(edge)
            ne['u'] = idmap[edge['u']]
            ne['v'] = idmap[edge['v']]
            combined.edges.append(ne)
    return merge_close_nodes(combined, lambda_dis)
