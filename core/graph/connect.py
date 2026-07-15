# -*- coding: utf-8 -*-
"""
Graph connectivity operations (WS-Conn / WS-Post).
Приёмы для получения НЕРАЗРЫВНОГО графа и чистки компонент:

- `connect_dangling_ends` — сшивка разрывов: висячие концы (узлы степени 1)
  соединяются прямым ребром с ближайшим другим узлом в радиусе R. Это «устранить
  разрывы» из записки ФГИС ЛК на уровне графа.
- `components` / `largest_component` / `remove_small_components` — работа со
  связными компонентами (убрать изолированные ошмётки, оставить крупнейшую сеть).

Работает с графом в МИРОВЫХ координатах (nodes: id -> (x, y); рёбра 'u','v',
'coords','length','frequency'). Новые связующие рёбра получают frequency=0 (их
пометит `attributes.annotate` как reconstructed). Чистый numpy/scipy.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from collections import defaultdict

import numpy as np

from .to_graph import RoadGraph


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


def _degrees(graph):
    deg = defaultdict(int)
    for e in graph.edges:
        deg[e['u']] += 1
        deg[e['v']] += 1
    return deg


def _neighbors(graph):
    """Множество соседних узлов для каждого узла (по рёбрам)."""
    nb = defaultdict(set)
    for e in graph.edges:
        nb[e['u']].add(e['v'])
        nb[e['v']].add(e['u'])
    return nb


def connect_dangling_ends(graph, radius):
    """Соединить висячие концы (узлы степени 1) с ближайшим узлом в радиусе.

    Для каждого узла степени 1 ищется ближайший другой узел (кроме уже соседнего)
    в пределах `radius` метров; добавляется прямое связующее ребро. Пары не
    дублируются. Возвращает (graph, added_count); граф меняется на месте.
    """
    if not radius or radius <= 0 or not graph.edges:
        return graph, 0
    from scipy.spatial import cKDTree

    deg = _degrees(graph)
    nb = _neighbors(graph)
    ids = list(graph.nodes)
    if len(ids) < 2:
        return graph, 0
    index = {nid: k for k, nid in enumerate(ids)}
    coords = np.array([graph.nodes[nid] for nid in ids], dtype=float)
    tree = cKDTree(coords)

    dangling = [nid for nid in ids if deg.get(nid, 0) == 1]
    added_pairs = set()
    added = 0
    for n in dangling:
        cand = tree.query_ball_point(coords[index[n]], radius)
        # ближайшие сначала
        cand.sort(key=lambda k: np.hypot(*(coords[k] - coords[index[n]])))
        for k in cand:
            m = ids[k]
            if m == n or m in nb[n]:
                continue
            pair = frozenset((n, m))
            if pair in added_pairs:
                continue
            xy_n = graph.nodes[n]
            xy_m = graph.nodes[m]
            dist = float(np.hypot(xy_m[0] - xy_n[0], xy_m[1] - xy_n[1]))
            graph.edges.append({
                'u': n, 'v': m,
                'coords': np.array([xy_n, xy_m], dtype=float),
                'length': dist, 'frequency': 0})
            added_pairs.add(pair)
            nb[n].add(m)
            nb[m].add(n)
            added += 1
            break                       # один мост на висячий конец
    return graph, added


def _proj_point_seg(p, a, b):
    """Проекция точки p на отрезок [a,b]: (точка, t в [0,1], расстояние)."""
    ab = b - a
    denom = float(ab @ ab)
    t = 0.0 if denom == 0.0 else float(np.clip((p - a) @ ab / denom, 0.0, 1.0))
    proj = a + t * ab
    return proj, t, float(np.hypot(proj[0] - p[0], proj[1] - p[1]))


def _polyline_len(coords):
    c = np.asarray(coords, dtype=float)
    if len(c) < 2:
        return 0.0
    d = np.diff(c, axis=0)
    return float(np.hypot(d[:, 0], d[:, 1]).sum())


def _split_polyline(coords, cuts):
    """Разрезать полилинию в точках проекций.

    Args:
        coords: (N,2) вершины ребра.
        cuts: отсортированный список (arc_key, seg_j, t, P) — точки разреза.

    Returns:
        (pieces, cut_points): список под-полилиний и точки разреза по порядку.
    """
    pieces, cut_points = [], []
    cur = [coords[0]]
    ci = 0
    for j in range(len(coords) - 1):
        while ci < len(cuts) and cuts[ci][1] == j:
            _key, _j, _t, pt = cuts[ci]
            cur.append(pt)
            pieces.append(np.array(cur, dtype=float))
            cut_points.append(pt)
            cur = [pt]
            ci += 1
        cur.append(coords[j + 1])
    pieces.append(np.array(cur, dtype=float))
    return pieces, cut_points


def snap_dangling_to_edges(graph, radius, step=None):
    """Привязать висячие концы к ближайшей ТОЧКЕ НА РЕБРЕ в радиусе (T-разрывы).

    Для каждого узла степени 1 ищется ближайшее чужое ребро; если проекция конца
    на это ребро ближе `radius`, ребро разрезается в точке проекции (новый узел —
    T-перекрёсток), а конец соединяется прямым ребром с этой точкой. Это сшивает
    разрывы «тупик рядом с серединой дороги», которые `connect_dangling_ends`
    (конец-в-конец) не видит.

    Returns:
        (graph, snapped_count) — новый RoadGraph.
    """
    if not radius or radius <= 0 or not graph.edges:
        return graph, 0
    from scipy.spatial import cKDTree

    edges = graph.edges
    deg = _degrees(graph)
    incident = defaultdict(set)
    for ei, e in enumerate(edges):
        incident[e['u']].add(ei)
        incident[e['v']].add(ei)

    # Плотная выборка точек рёбер для поиска кандидатов (шаг ≈ radius/2).
    step = step or max(radius * 0.5, 1.0)
    s_pts, s_edge = [], []
    for ei, e in enumerate(edges):
        c = np.asarray(e['coords'], dtype=float)
        for j in range(len(c) - 1):
            a, b = c[j], c[j + 1]
            nsub = max(1, int(np.hypot(b[0] - a[0], b[1] - a[1]) / step))
            for k in range(nsub + 1):
                s_pts.append(a + (b - a) * (k / nsub))
                s_edge.append(ei)
    if not s_pts:
        return graph, 0
    s_pts = np.array(s_pts, dtype=float)
    s_edge = np.array(s_edge, dtype=int)
    tree = cKDTree(s_pts)

    dangling = [nid for nid in graph.nodes if deg.get(nid, 0) == 1]
    snaps = defaultdict(list)                 # ei -> [(arc_key, seg_j, t, P, n)]
    for n in dangling:
        p = np.asarray(graph.nodes[n], dtype=float)
        cand = tree.query_ball_point(p, radius)
        if not cand:
            continue
        # ближайшее ребро, не инцидентное узлу n
        best_ei, best_d = None, None
        for si in cand:
            ei = int(s_edge[si])
            if ei in incident[n]:
                continue
            d = float(np.hypot(s_pts[si][0] - p[0], s_pts[si][1] - p[1]))
            if best_d is None or d < best_d:
                best_ei, best_d = ei, d
        if best_ei is None:
            continue
        # точная проекция на ближайший сегмент выбранного ребра
        c = np.asarray(edges[best_ei]['coords'], dtype=float)
        pick = None
        for j in range(len(c) - 1):
            proj, t, d = _proj_point_seg(p, c[j], c[j + 1])
            if pick is None or d < pick[2]:
                pick = (j, t, d, proj)
        j, t, d, proj = pick
        if d > radius:
            continue
        snaps[best_ei].append((j + t, j, t, proj, n))

    if not snaps:
        return graph, 0

    result = RoadGraph()
    result.nodes = dict(graph.nodes)
    next_id = (max(graph.nodes) + 1) if graph.nodes else 0
    snapped = 0
    for ei, e in enumerate(edges):
        if ei not in snaps:
            result.edges.append(e)
            continue
        cuts = sorted(snaps[ei])
        coords = np.asarray(e['coords'], dtype=float)
        pieces, cut_points = _split_polyline(coords, [c[:4] for c in cuts])
        # граничные узлы: u, <новые в точках разреза>, v
        boundary = [e['u']]
        cut_node_ids = []
        for pt in cut_points:
            result.nodes[next_id] = (float(pt[0]), float(pt[1]))
            boundary.append(next_id)
            cut_node_ids.append(next_id)
            next_id += 1
        boundary.append(e['v'])
        freq = int(e.get('frequency', 0))
        for k, piece in enumerate(pieces):
            result.edges.append({
                'u': boundary[k], 'v': boundary[k + 1],
                'coords': piece, 'length': _polyline_len(piece),
                'frequency': freq})
        # коннекторы: висячий конец n -> его точка проекции
        for (_key, _j, _t, pt, n), node_id in zip(cuts, cut_node_ids):
            xy_n = graph.nodes[n]
            result.edges.append({
                'u': n, 'v': node_id,
                'coords': np.array([xy_n, (float(pt[0]), float(pt[1]))],
                                   dtype=float),
                'length': float(np.hypot(pt[0] - xy_n[0], pt[1] - xy_n[1])),
                'frequency': 0})
            snapped += 1
    return result, snapped


def _seg_cross(a1, a2, b1, b2, margin=1e-6):
    """Точка СОБСТВЕННОГО пересечения отрезков [a1,a2] и [b1,b2].

    Returns (t, u, P) с margin<t<1-margin и margin<u<1-margin (внутреннее
    пересечение) либо None для параллельных/коллинеарных/касающихся в концах.
    """
    r = a2 - a1
    s = b2 - b1
    rxs = r[0] * s[1] - r[1] * s[0]
    if abs(rxs) < 1e-12:
        return None                               # параллельны/коллинеарны
    qp = b1 - a1
    t = (qp[0] * s[1] - qp[1] * s[0]) / rxs
    u = (qp[0] * r[1] - qp[1] * r[0]) / rxs
    if margin < t < 1.0 - margin and margin < u < 1.0 - margin:
        return t, u, a1 + t * r
    return None


def break_at_crossings(graph, min_split_m=0.0):
    """Разрезать геометрически пересекающиеся, но топологически разорванные
    рёбра в точке пересечения — настоящий перекрёсток (GRASS `v.clean break`).

    Для каждой пары НЕсмежных рёбер, чьи сегменты собственно пересекаются,
    создаётся ОБЩИЙ новый узел в точке пересечения, и оба ребра разрезаются в
    нём. Важно для связности «крестом» пересекающихся, но разорванных дорог.

    Осторожно: корректно на планарной сети; для мостов/эстакад (дорога над
    дорогой) создаст ложный перекрёсток — поэтому это опция, а не всегда-вкл.

    Args:
        graph: RoadGraph (мировые координаты).
        min_split_m: не резать, если точка ближе этого к концу ребра (0 = не
            ограничивать) — защита от микро-огрызков у существующих узлов.

    Returns:
        (graph, crossings_count) — новый RoadGraph с общими узлами-перекрёстками.
    """
    edges = graph.edges
    if len(edges) < 2:
        return graph, 0

    node_of = [frozenset((e['u'], e['v'])) for e in edges]
    segs = []                                     # (ei, seg_j, a, b)
    for ei, e in enumerate(edges):
        c = np.asarray(e['coords'], dtype=float)
        for j in range(len(c) - 1):
            segs.append((ei, j, c[j], c[j + 1]))
    if not segs:
        return graph, 0

    # Пространственный хэш по ячейкам ≈ медианной длине сегмента — кандидаты
    # только среди сегментов в общих ячейках (не O(E²)).
    lengths = [np.hypot(b[0] - a[0], b[1] - a[1]) for _ei, _j, a, b in segs]
    cell = max(float(np.median(lengths)), 1.0)
    grid = defaultdict(list)
    for si, (_ei, _j, a, b) in enumerate(segs):
        cx0, cx1 = int(min(a[0], b[0]) // cell), int(max(a[0], b[0]) // cell)
        cy0, cy1 = int(min(a[1], b[1]) // cell), int(max(a[1], b[1]) // cell)
        if (cx1 - cx0 + 1) * (cy1 - cy0 + 1) > 10000:
            continue                              # патологически длинный сегмент
        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1):
                grid[(cx, cy)].append(si)

    crossings = defaultdict(list)   # ei -> [(arc_key, seg_j, t, P, node_id)]
    new_nodes = {}
    next_id = (max(graph.nodes) + 1) if graph.nodes else 0
    tested = set()
    for bucket in grid.values():
        for ii in range(len(bucket)):
            for jj in range(ii + 1, len(bucket)):
                si, sj = bucket[ii], bucket[jj]
                if si > sj:
                    si, sj = sj, si
                if (si, sj) in tested:
                    continue
                tested.add((si, sj))
                ei, segi, a1, a2 = segs[si]
                ej, segj, b1, b2 = segs[sj]
                if ei == ej or (node_of[ei] & node_of[ej]):
                    continue                      # тот же/смежные — уже связаны
                hit = _seg_cross(a1, a2, b1, b2)
                if hit is None:
                    continue
                t, u, P = hit
                if min_split_m > 0:
                    ci = np.asarray(edges[ei]['coords'], dtype=float)
                    cj = np.asarray(edges[ej]['coords'], dtype=float)
                    if min(np.hypot(*(P - ci[0])), np.hypot(*(P - ci[-1])),
                           np.hypot(*(P - cj[0])), np.hypot(*(P - cj[-1]))
                           ) < min_split_m:
                        continue
                node_id = next_id
                next_id += 1
                new_nodes[node_id] = (float(P[0]), float(P[1]))
                crossings[ei].append((segi + t, segi, t, P, node_id))
                crossings[ej].append((segj + u, segj, u, P, node_id))

    if not new_nodes:
        return graph, 0

    result = RoadGraph()
    result.nodes = dict(graph.nodes)
    result.nodes.update(new_nodes)
    for ei, e in enumerate(edges):
        if ei not in crossings:
            result.edges.append(e)
            continue
        cuts = sorted(crossings[ei])
        coords = np.asarray(e['coords'], dtype=float)
        pieces, _pts = _split_polyline(coords, [c[:4] for c in cuts])
        boundary = [e['u']] + [c[4] for c in cuts] + [e['v']]
        freq = int(e.get('frequency', 0))
        for k, piece in enumerate(pieces):
            result.edges.append({
                'u': boundary[k], 'v': boundary[k + 1],
                'coords': piece, 'length': _polyline_len(piece),
                'frequency': freq})
    return result, len(new_nodes)


def _incident_edge_index(graph):
    """node -> индекс первого инцидентного ребра (для направления конца)."""
    inc = {}
    for ei, e in enumerate(graph.edges):
        inc.setdefault(e['u'], ei)
        inc.setdefault(e['v'], ei)
    return inc


def _end_direction(graph, n, inc):
    """Единичный вектор «продолжения дороги» наружу из тупика n."""
    ei = inc.get(n)
    if ei is None:
        return np.zeros(2)
    c = np.asarray(graph.edges[ei]['coords'], dtype=float)
    if len(c) < 2:
        return np.zeros(2)
    xy = np.asarray(graph.nodes[n], dtype=float)
    # ориентируем так, чтобы последняя точка была у узла n
    if np.hypot(c[0][0] - xy[0], c[0][1] - xy[1]) < \
            np.hypot(c[-1][0] - xy[0], c[-1][1] - xy[1]):
        c = c[::-1]
    v = c[-1] - c[-2]
    nrm = float(np.hypot(v[0], v[1]))
    return v / nrm if nrm > 0 else np.zeros(2)


def bridge_facing_ends(graph, max_dist, max_angle_deg=35.0):
    """Направленный мост: соединить тупики, «смотрящие» друг на друга.

    Для двух узлов степени 1 в пределах `max_dist` (может быть больше обычного
    радиуса сшивки) проверяется, что продолжение дороги каждого направлено на
    другой (углы < max_angle_deg). Если да — добавляется прямое ребро. Это
    восстанавливает дорогу, разорванную на большом промежутке, не соединяя
    случайные близкие тупики под большим углом.

    Returns:
        (graph, added_count) — граф меняется на месте.
    """
    if not max_dist or max_dist <= 0 or not graph.edges:
        return graph, 0
    from scipy.spatial import cKDTree

    deg = _degrees(graph)
    nb = _neighbors(graph)
    inc = _incident_edge_index(graph)
    dangling = [nid for nid in graph.nodes if deg.get(nid, 0) == 1]
    if len(dangling) < 2:
        return graph, 0
    coords = np.array([graph.nodes[n] for n in dangling], dtype=float)
    dirs = {n: _end_direction(graph, n, inc) for n in dangling}
    tree = cKDTree(coords)
    cos_thr = float(np.cos(np.radians(max_angle_deg)))
    added_pairs = set()
    added = 0
    for i, n in enumerate(dangling):
        pn = coords[i]
        dn = dirs[n]
        if not dn.any():
            continue
        best = None
        for j in tree.query_ball_point(pn, max_dist):
            m = dangling[j]
            if m == n or m in nb[n]:
                continue
            v = coords[j] - pn
            dist = float(np.hypot(v[0], v[1]))
            if dist < 1e-9:
                continue
            vhat = v / dist
            dm = dirs[m]
            if dn @ vhat < cos_thr or dm @ (-vhat) < cos_thr:
                continue
            if best is None or dist < best[1]:
                best = (m, dist)
        if best is None:
            continue
        m, dist = best
        pair = frozenset((n, m))
        if pair in added_pairs:
            continue
        graph.edges.append({
            'u': n, 'v': m,
            'coords': np.array([graph.nodes[n], graph.nodes[m]], dtype=float),
            'length': dist, 'frequency': 0})
        added_pairs.add(pair)
        nb[n].add(m)
        nb[m].add(n)
        added += 1
    return graph, added


def stitch_components(graph, max_dist):
    """Сшить связные компоненты в одну сеть по ближайшим узлам (гарантия
    связности в пределах max_dist).

    Boruvka/Kruskal по k ближайшим соседям: соединяются ближайшие узлы РАЗНЫХ
    компонент, пока сеть не станет связной или ближайший зазор не превысит
    max_dist. Returns (graph, added_count).
    """
    if not max_dist or max_dist <= 0 or not graph.edges:
        return graph, 0
    from scipy.spatial import cKDTree

    ids = list(graph.nodes)
    if len(ids) < 2:
        return graph, 0
    index = {nid: i for i, nid in enumerate(ids)}
    coords = np.array([graph.nodes[nid] for nid in ids], dtype=float)
    uf = _UnionFind(len(ids))
    for e in graph.edges:
        if e['u'] in index and e['v'] in index:
            uf.union(index[e['u']], index[e['v']])
    tree = cKDTree(coords)
    k = min(8, len(ids))
    dists, idxs = tree.query(coords, k=k)
    if idxs.ndim == 1:
        idxs = idxs[:, None]
        dists = dists[:, None]
    cands = []
    for a in range(len(ids)):
        for kk in range(1, idxs.shape[1]):
            b = int(idxs[a, kk])
            d = float(dists[a, kk])
            if d <= max_dist and a < b:
                cands.append((d, a, b))
    cands.sort()
    added = 0
    for d, a, b in cands:
        if uf.find(a) != uf.find(b):
            uf.union(a, b)
            na, nb_ = ids[a], ids[b]
            graph.edges.append({
                'u': na, 'v': nb_,
                'coords': np.array([graph.nodes[na], graph.nodes[nb_]],
                                   dtype=float),
                'length': d, 'frequency': 0})
            added += 1
    return graph, added


def components(graph):
    """Список связных компонент как множеств id узлов (union-find по рёбрам)."""
    parent = {nid: nid for nid in graph.nodes}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for e in graph.edges:
        if e['u'] in parent and e['v'] in parent:
            union(e['u'], e['v'])
    groups = defaultdict(set)
    for nid in graph.nodes:
        groups[find(nid)].add(nid)
    return list(groups.values())


def _component_length(graph, node_set):
    total = 0.0
    for e in graph.edges:
        if e['u'] in node_set and e['v'] in node_set:
            total += float(e.get('length', 0.0))
    return total


def _keep_nodes(graph, keep):
    """Оставить только узлы из `keep` и рёбра между ними (новый граф)."""
    result = RoadGraph()
    result.nodes = {nid: xy for nid, xy in graph.nodes.items() if nid in keep}
    result.edges = [e for e in graph.edges
                    if e['u'] in keep and e['v'] in keep]
    return result


def largest_component(graph):
    """Оставить только компоненту с наибольшей суммарной длиной рёбер."""
    comps = components(graph)
    if len(comps) <= 1:
        return graph
    best = max(comps, key=lambda s: _component_length(graph, s))
    return _keep_nodes(graph, best)


def remove_small_components(graph, min_length_m):
    """Удалить компоненты, суммарная длина рёбер которых < min_length_m.

    Returns:
        (graph, removed_components_count) — новый граф.
    """
    if not min_length_m or min_length_m <= 0:
        return graph, 0
    comps = components(graph)
    keep = set()
    removed = 0
    for comp in comps:
        if _component_length(graph, comp) >= min_length_m:
            keep |= comp
        else:
            removed += 1
    return _keep_nodes(graph, keep), removed
