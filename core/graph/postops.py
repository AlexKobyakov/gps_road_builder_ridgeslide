# -*- coding: utf-8 -*-
"""
Post-processing orchestrator over a world graph (WS-Post / WS-Conn / WS-Smooth).
Единая последовательность доводки графа, переиспользуемая И в конце пайплайна, И
в отдельной вкладке «Постобработка» (над уже готовым графом):

  склейка проходных узлов + усы → сшивка висячих концов → чистка компонент →
  сглаживание → атрибуты.

Работает с графом в МЕТРИЧЕСКИХ мировых координатах (nodes (x,y), рёбра 'coords').
Чистое ядро — тестируется офлайн.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from . import postprocess, connect, smoothing, attributes


def apply(graph, params):
    """Применить пост-обработку к графу в метрических координатах.

    Args:
        graph: RoadGraph (nodes (x,y), рёбра с 'coords','length','frequency').
        params: dict с ключами spur_min_m, connect_gap_m, keep_largest,
            min_component_m, smooth_iters.

    Returns:
        (graph, stats): новый граф + метрики (bridged, components_dropped,
        edges_before/after, nodes).
    """
    stats = {'edges_before': graph.edge_count(),
             'nodes_before': graph.node_count()}

    graph = postprocess.postprocess_graph(
        graph, spur_min_m=float(params.get('spur_min_m', 0.0) or 0.0))

    # §WS-KDE: убрать микро-петли-«перекрестья» скелета.
    loop_min = float(params.get('loop_min_m', 0.0) or 0.0)
    if loop_min > 0:
        graph, dropped_loops = postprocess.remove_small_loops(graph, loop_min)
        stats['loops_dropped'] = dropped_loops

    connect_r = float(params.get('connect_gap_m', 0.0) or 0.0)
    if connect_r > 0:
        # 1) конец-в-конец, 2) конец-к-ребру (T-разрывы) — вместе дают связность.
        graph, bridged = connect.connect_dangling_ends(graph, connect_r)
        stats['bridged'] = bridged
        graph, snapped = connect.snap_dangling_to_edges(graph, connect_r)
        stats['snapped'] = snapped

    # Направленный мост: тупики «навстречу» друг другу дальше обычного радиуса.
    facing = float(params.get('bridge_facing_m', 0.0) or 0.0)
    if facing > 0:
        graph, faced = connect.bridge_facing_ends(graph, facing)
        stats['faced'] = faced

    # Сшивка компонент в одну сеть (гарантия связности в пределах max).
    stitch = float(params.get('stitch_max_m', 0.0) or 0.0)
    if stitch > 0:
        graph, stitched = connect.stitch_components(graph, stitch)
        stats['stitched'] = stitched

    # Топология: разрезать геом. пересечения без общего узла (GRASS break) —
    # ДО junction-консолидации (сначала создать узлы на пересечениях).
    if params.get('break_crossings'):
        graph, broken = connect.break_at_crossings(graph)
        stats['broken'] = broken

    # Junction-консолидация: слить кластеры близких перекрёстков в один узел
    # (OSMnx-подобно; переиспользуем merge_close_nodes).
    junction = float(params.get('junction_m', 0.0) or 0.0)
    if junction > 0:
        from ..splitmerge.merger import merge_close_nodes
        before_n = graph.node_count()
        graph = merge_close_nodes(graph, junction)
        stats['junctions_merged'] = before_n - graph.node_count()

    if params.get('keep_largest'):
        graph = connect.largest_component(graph)

    min_comp = float(params.get('min_component_m', 0.0) or 0.0)
    if min_comp > 0:
        graph, dropped = connect.remove_small_components(graph, min_comp)
        stats['components_dropped'] = dropped

    smoothing.smooth_graph(graph, iterations=int(params.get('smooth_iters', 0)))
    attributes.annotate(graph)

    stats['edges'] = graph.edge_count()
    stats['nodes'] = graph.node_count()
    return graph, stats
