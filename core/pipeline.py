# -*- coding: utf-8 -*-
"""
End-to-end pipeline for GPS Road Builder (Guo 2020, four steps + split-merge).
Оркестратор: нормализованные точки → очистка → сегментация → проекция →
ресэмплинг → (тайлинг) → компактификация Slide → бинаризация → скелет → граф →
упрощение → веса рёбер → фильтрация → слияние узлов/тайлов → география (4326).

Чистое ядро (numpy/scipy/pyproj). Прогресс и отмена — через колбэки, чтобы
обёртка QgsTask (tasks/build_task.py) оставалась отзывчивой (§5).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

from .io import schema
from .preprocess import clean as clean_mod
from .preprocess import segmentize
from .preprocess import resample as resample_mod
from .preprocess import thin as thin_mod
from .preprocess import aoi as aoi_mod
from .preprocess.segmentize import TRACK_ID
from .density import projection, blur, kde, grid as grid_mod
from .ridgeslide import refine as slide_mod
from .graph import (binarize, skeletonize, to_graph, simplify, edge_weights,
                    postops)
from .splitmerge import splitter, merger
from . import checkpoint
from . import run_log

# Порядок и ориентировочные «веса» длительности шагов (для списка шагов и ETA).
STEPS = ('read', 'clean', 'thin', 'segmentize', 'project', 'resample',
         'extract', 'merge', 'cleanup', 'reproject', 'done')

# Верхний предел ячеек растра на тайл (защита от OOM, §A6).
MAX_TILE_CELLS = 120_000_000


def default_params():
    """Стартовые параметры (согласуются с §8 плана)."""
    return {
        'v_max_kmh': 70.0, 'a_max': 4.0,
        'min_point_dist': 10.0,          # near-dup прореживание (0 = выкл), §A3
        'gap_dt_s': 300.0, 'gap_ds_m': 500.0,
        'resample_k': 5.0,
        'cell_tau': 5.0, 'sigma1': 5.0, 'sigma2': 3.0, 'sharpness': 1.5,
        'weights': (0.5, 0.2, 0.1, 0.7),
        'slide_min_loops': 100, 'slide_max_loops': 4000,
        'eps_mode': 'otsu', 'eps_value': 0.0,
        'eps_percentile': 80.0,    # порог по перцентилю плотности (§WS-KDE)
        'fill_holes_m': 0.0,       # заполнять дыры маски < размера, м (0 = выкл)
        'loop_min_m': 0.0,         # удалять микро-петли короче, м (0 = выкл)
        'compute_devices': True,   # считать n_devices (если есть метки устройств)
        'dp_tolerance': 2.0,
        'edge_f_min': 2, 'edge_l_min': 30.0, 'protect_long_m': 200.0,
        'reb_enabled': False,      # REB/anti-spoofing фильтр (§WS-G)
        'spur_min_m': 0.0,         # удаление висячих усов < этой длины (0 = выкл)
        'smooth_iters': 0,         # сглаживание рёбер Chaikin (0 = выкл), §WS-Smooth
        'slide_close_gaps_m': 0.0,  # закрытие маски дилатацией для Slide (§WS-Conn)
        'connect_gap_m': 0.0,      # сшивка висячих концов в радиусе (0 = выкл)
        'bridge_facing_m': 0.0,    # направленный мост встречных тупиков (0 = выкл)
        'stitch_max_m': 0.0,       # сшивка компонент в одну сеть (0 = выкл)
        'min_component_m': 0.0,    # удалять компоненты короче (0 = выкл)
        'keep_largest': False,     # оставить только крупнейшую компоненту
        'aoi_polygon': None,       # полигон AOI: список колец (lon,lat) или None
        'backend': 'auto',            # бэкенд ядра Slide: auto|numba|numpy
        'skeleton_backend': 'auto',   # auto|skimage|zhang_suen
        # метод: 'slide' (плотные треки, Guo) | 'kde' (разрежённые, ФГИС ЛК)
        'method': 'slide',
        'kde_radius': 50.0,           # радиус KDE-ядра, м
        'gap_buffer_m': 30.0,         # морфологическое закрытие разрывов, м
        # масштаб / split-and-merge
        'split_mode': 'auto', 'tile_grid': None,
        'max_points_per_tile': 400_000, 'overlap_cells': 15,
        'node_merge_dist': None,   # None → 1.5·τ
        # чекпоинты / пошаговый режим (§WS-D/F)
        'cache_dir': '',           # папка промежуточных результатов ('' = выкл)
        'start_stage': '',         # '' | 'points' | 'tracks' — начать с этапа
        'stop_after': '',          # '' | 'points' | 'tracks' — остановиться после
    }


def _emit(progress, frac, message):
    if progress is not None:
        progress(float(frac), message)


def _cancelled(is_cancelled):
    return is_cancelled is not None and is_cancelled()


def _guard_cells(tracks, p):
    non_empty = [t for t in tracks if len(t) >= 2]
    if non_empty:
        b = grid_mod.bounds_of_tracks(non_empty)
        if grid_mod.estimate_cells(b, p['cell_tau']) > MAX_TILE_CELLS:
            raise ValueError(
                'Density raster too large for a tile (cell={0} m). Reduce '
                '"max points per tile" or increase cell size.'.format(
                    p['cell_tau']))


def _binarize_by_mode(values, p):
    """Бинаризация по выбранному режиму порога (otsu | manual | percentile)."""
    if p['eps_mode'] == 'manual':
        return binarize.binarize(values, eps=p['eps_value'], method='manual')
    if p['eps_mode'] == 'percentile':
        return binarize.binarize(values, method='percentile',
                                 percentile=p.get('eps_percentile', 80.0))
    return binarize.binarize(values, method='otsu')


def _graph_from_density(grid, coverage_tracks, mask, p):
    """Общий хвост: маска → скелет → граф → веса → упрощение → фильтр → мир."""
    # §WS-KDE: заполнить мелкие дыры маски (иначе скелет даёт петли-«перекрестья»).
    fill_m = float(p.get('fill_holes_m', 0.0) or 0.0)
    if fill_m > 0:
        area_px = (fill_m / float(p['cell_tau'])) ** 2
        mask = binarize.fill_small_holes(mask, area_px)
    skeleton = skeletonize.skeletonize(mask, backend=p['skeleton_backend'])
    graph = to_graph.to_graph(skeleton)
    edge_weights.compute_frequencies(graph, coverage_tracks, grid)
    simplify.simplify_graph(graph, grid, epsilon_m=p['dp_tolerance'])
    graph, removed = edge_weights.filter_edges(
        graph, f_min=p['edge_f_min'], l_min=p['edge_l_min'],
        protect_long_m=(p['protect_long_m'] or None))
    world = merger.to_world_graph(graph, grid)
    node_merge_dist = p['node_merge_dist'] or (1.5 * p['cell_tau'])
    world = merger.merge_close_nodes(world, dist=node_merge_dist)
    return world, removed


def _extract_slide(tracks, p):
    """Метод «Плотность + Slide» (Guo) — для плотных треков."""
    _guard_cells(tracks, p)
    compact = slide_mod.compact_density(
        tracks, cell=p['cell_tau'], sigma1=p['sigma1'], sigma2=p['sigma2'],
        sharpness=p['sharpness'], weights=p['weights'],
        min_iter=p['slide_min_loops'], max_iter=p['slide_max_loops'],
        backend=p['backend'])
    adjusted = compact['adjusted_tracks']
    grid = compact['density']
    if grid is None or not adjusted:
        return to_graph.RoadGraph(), {'threshold': 0.0, 'edges_removed': 0}
    smoothed = blur.smooth_density(grid.values, p['sigma2'],
                                   sharpness=p['sharpness'])
    mask, threshold = _binarize_by_mode(smoothed, p)
    # §WS-Conn: опц. морфологическое закрытие маски и для Slide (мостит разрывы).
    close_m = float(p.get('slide_close_gaps_m', 0.0) or 0.0)
    if close_m > 0:
        mask = binarize.close_gaps(mask, close_m / float(p['cell_tau']))
    world, removed = _graph_from_density(grid, adjusted, mask, p)
    return world, {'threshold': threshold, 'edges_removed': removed}


def _extract_kde(tracks, p):
    """Метод «KDE + буфер + centerline» (ФГИС ЛК) — для разрежённых данных."""
    _guard_cells(tracks, p)
    # §WS-KDE: KDE — плотность ПО ТОЧКАМ, поэтому кормим все точки, включая
    # одиночные (len>=1), а не только ≥2-точечные сегменты.
    non_empty = [t for t in tracks if len(t) >= 1]
    if not non_empty:
        return to_graph.RoadGraph(), {'threshold': 0.0, 'edges_removed': 0}
    grid = kde.build_kde(non_empty, cell=p['cell_tau'],
                         radius_m=p['kde_radius'])
    mask, threshold = _binarize_by_mode(grid.values, p)
    # мостим разрывы там, где сигналы редки (буферизация записки)
    buffer_px = float(p['gap_buffer_m']) / float(p['cell_tau'])
    mask = binarize.close_gaps(mask, buffer_px)
    world, removed = _graph_from_density(grid, non_empty, mask, p)
    return world, {'threshold': threshold, 'edges_removed': removed}


def _extract_region_graph(tracks, p):
    """Извлечь граф одного региона (тайла) в мировых координатах по методу p."""
    if p.get('method') == 'kde':
        return _extract_kde(tracks, p)
    return _extract_slide(tracks, p)


def build_road_graph(df, params=None, progress=None, is_cancelled=None,
                     log=None):
    """Построить граф дорог из нормализованного набора точек.

    Args:
        df: DataFrame с колонками device/time/lat/lon (io.schema).
        params: словарь параметров (см. default_params()).
        progress: callable(fraction: float, message: str).
        is_cancelled: callable() -> bool.
        log: callable(str) для подробного лога (настройки/метрики этапов, §WS-L).

    Returns:
        dict с ключами graph, projector, stats, params; либо None при отмене.
    """
    p = default_params()
    if params:
        p.update(params)
    cache = p.get('cache_dir') or ''
    start = p.get('start_stage') or ''
    stop = p.get('stop_after') or ''

    def _lg(msg):
        if log is not None:
            log(msg)

    device_pts = None   # §WS-Dev: (x, y, device) исходных точек; None при резюме

    # §WS-L: пишем резолвнутые настройки прогона (связать результат с параметрами).
    for line in run_log.format_params(p):
        _lg(line)
    # Реально выбранный бэкенд Slide (setting → resolved) — снимает путаницу
    # «numba установлена, но считает numpy».
    if p.get('method') != 'kde':
        from .ridgeslide.kernel import HAVE_NUMBA
        resolved = ('numba' if (p['backend'] in ('numba', 'auto') and HAVE_NUMBA)
                    else 'numpy')
        _lg('run | Slide backend: setting={0} -> using={1} '
            '(numba_available={2})'.format(p['backend'], resolved, HAVE_NUMBA))

    if start == 'tracks' and checkpoint.has_tracks(cache):
        # Резюме с сохранённых треков (пропускаем очистку/проекцию/ресэмпл).
        _emit(progress, 0.25, 'load-tracks')
        tracks, proj4, meta = checkpoint.load_tracks(cache)
        if not tracks:
            raise ValueError('Cached tracks are empty')
        projector = projection.Projector(proj4)
        clean_stats = meta.get('clean_stats', {})
        thin_removed = int(meta.get('near_dup_removed', 0))
    else:
        if start == 'points' and checkpoint.has_points(cache):
            _emit(progress, 0.06, 'load-points')
            thinned, meta = checkpoint.load_points(cache)
            clean_stats = meta.get('clean_stats', {})
            thin_removed = int(meta.get('near_dup_removed', 0))
        else:
            # §WS-AOI: обрезка точек по полигону области интереса (до очистки).
            aoi_removed = 0
            if p.get('aoi_polygon'):
                df, aoi_removed = aoi_mod.clip_points(df, p['aoi_polygon'])
                _lg(run_log.format_stage('aoi-clip', {
                    'removed': aoi_removed, 'kept': len(df)}))
            _emit(progress, 0.02, 'clean')
            cleaned, clean_stats = clean_mod.clean(
                df, v_max_kmh=p['v_max_kmh'], a_max=p['a_max'],
                reb=p.get('reb_enabled', False))
            clean_stats = dict(clean_stats)
            clean_stats['aoi_removed'] = aoi_removed
            if _cancelled(is_cancelled):
                return None
            _emit(progress, 0.06, 'thin')
            thinned, thin_removed = thin_mod.thin_near_duplicates(
                cleaned, min_dist_m=p['min_point_dist'], backend=p['backend'])
            if _cancelled(is_cancelled):
                return None
            if cache:
                checkpoint.save_points(cache, thinned, {
                    'clean_stats': clean_stats, 'near_dup_removed': thin_removed})
        if stop == 'points':
            return _partial(progress, 'points', p, clean_stats, thin_removed)
        if _cancelled(is_cancelled):
            return None

        _emit(progress, 0.10, 'segmentize')
        segmented = segmentize.assign_segments(
            thinned, gap_dt_s=p['gap_dt_s'], gap_ds_m=p['gap_ds_m'])
        if segmented.empty:
            raise ValueError('No usable points after cleaning/segmentation')

        # A2: проецируем ВСЕ точки одним векторным вызовом (не по одному треку).
        _emit(progress, 0.15, 'project')
        projector = projection.Projector.for_data(
            segmented[schema.LON].to_numpy(), segmented[schema.LAT].to_numpy())
        x_all, y_all = projector.forward(
            segmented[schema.LON].to_numpy(), segmented[schema.LAT].to_numpy())

        # §WS-Dev: сохраняем исходные точки с метками устройств для n_devices.
        device_pts = (x_all, y_all, segmented[schema.DEVICE].to_numpy())

        _emit(progress, 0.20, 'resample')
        # KDE строит плотность по точкам → сохраняем и одиночные (min_points=1).
        min_pts = 1 if p.get('method') == 'kde' else 2
        raw_tracks = _split_tracks(segmented, x_all, y_all, min_points=min_pts)
        pts_before = int(sum(len(t) for t in raw_tracks))
        if p.get('method') == 'kde':
            # KDE: без ресэмпла (интерполяция между редкими фиксами вредна)
            tracks = raw_tracks
        else:
            tracks = []
            for tr in raw_tracks:
                rs = resample_mod.resample_polyline(tr, p['resample_k'])
                if len(rs) >= 2:
                    tracks.append(rs)
        if not tracks:
            raise ValueError('No tracks with >= 2 points after resampling')
        pts_after = int(sum(len(t) for t in tracks))
        # §WS-L: явно показать «взрыв» точек ресэмплом (грабли §3 — раздувание
        # разрежённых данных мелким K).
        _lg(run_log.format_stage('resample', {
            'tracks': len(tracks), 'points_before': pts_before,
            'points_after': pts_after,
            'ratio': round(pts_after / max(1, pts_before), 1)}))
        if _cancelled(is_cancelled):
            return None
        if cache:
            checkpoint.save_tracks(cache, tracks, projector.proj4, {
                'clean_stats': clean_stats, 'near_dup_removed': thin_removed})
        if stop == 'tracks':
            return _partial(progress, 'tracks', p, clean_stats, thin_removed,
                            tracks=tracks, projector=projector)

    bounds = grid_mod.bounds_of_tracks(tracks)
    n_points = int(sum(len(t) for t in tracks))
    tiles = splitter.choose_tiling(
        bounds, n_points, p['cell_tau'], split_mode=p['split_mode'],
        tile_grid=p.get('tile_grid'),
        max_points_per_tile=p['max_points_per_tile'],
        overlap_cells=p['overlap_cells'])
    _lg(run_log.format_stage('tiling', {
        'tiles': len(tiles), 'tracks': len(tracks), 'points': n_points}))

    # §WS-Perf: защита от многочасового прогона. Метод Slide на numpy-бэкенде
    # (эталон, без JIT/параллелизма) при десятках млн точек считается часами —
    # это почти всегда ошибка настроек (не выбран numba / раздут ресэмпл).
    from .ridgeslide.kernel import HAVE_NUMBA
    slide_on_numpy = (p.get('method') != 'kde'
                      and not (p['backend'] in ('numba', 'auto') and HAVE_NUMBA))
    if slide_on_numpy and n_points > 15_000_000:
        raise ValueError(
            'Slide on the numpy backend with {0:.0f}M points across {1} tiles '
            'would take hours. Select the numba Slide backend, or reduce the '
            'point count (larger "resample step K" / "distance gap", or coarser '
            'cell).'.format(n_points / 1e6, len(tiles)))
    if slide_on_numpy and HAVE_NUMBA:
        _lg('WARNING: Slide runs on the numpy backend (slow) while numba is '
            'available — select the numba Slide backend for a big speed-up.')

    if len(tiles) == 1:
        _emit(progress, 0.35, 'extract')
        final, rstats = _extract_region_graph(tracks, p)
        _lg(run_log.format_stage('extract', {
            'threshold': round(float(rstats['threshold']), 4),
            'edges': final.edge_count(),
            'edges_removed': rstats['edges_removed']}))
        stats_extra = {'tiles': 1, 'threshold': rstats['threshold'],
                       'edges_removed': rstats['edges_removed']}
    else:
        per_tile = splitter.assign_tracks_to_tiles(tracks, tiles)
        world_graphs = []
        thresholds = []
        n = len(per_tile)
        for ti, tile_tracks in enumerate(per_tile):
            if _cancelled(is_cancelled):
                return None
            _emit(progress, 0.30 + 0.55 * ti / max(1, n),
                  'tile {0}/{1}'.format(ti + 1, n))
            if tile_tracks:
                wg, _rs = _extract_region_graph(tile_tracks, p)
                world_graphs.append(wg)
                thresholds.append(float(_rs['threshold']))
                _lg(run_log.format_stage('tile {0}/{1}'.format(ti + 1, n), {
                    'threshold': round(float(_rs['threshold']), 4),
                    'edges': wg.edge_count()}))
        # Сводка по порогам тайлов — ключевой сигнал для подбора (§WS-L).
        if thresholds:
            arr = np.asarray(thresholds, dtype=float)
            _lg(run_log.format_stage('tiles-threshold', {
                'min': round(float(arr.min()), 4),
                'median': round(float(np.median(arr)), 4),
                'max': round(float(arr.max()), 4)}))
        _emit(progress, 0.88, 'merge')
        lambda_dis = 3.0 * p['cell_tau'] * p['sigma2']
        final = merger.merge_graphs(world_graphs, lambda_dis)
        _lg(run_log.format_stage('merge', {
            'lambda_dis': round(lambda_dis, 1),
            'edges': final.edge_count(), 'nodes': final.node_count()}))
        stats_extra = {'tiles': len(tiles), 'threshold': 0.0,
                       'edges_removed': 0}

    if _cancelled(is_cancelled):
        return None

    # Пост-обработка: склейка узлов степени 2 + усы + сшивка концов + чистка
    # компонент + сглаживание + атрибуты (§WS-G/WS-Conn/WS-Smooth, DRY с вкладкой
    # «Постобработка»).
    _emit(progress, 0.94, 'cleanup')
    final, post_stats = postops.apply(final, p)
    _lg(run_log.format_stage('cleanup', {
        'edges': '{0}->{1}'.format(post_stats['edges_before'],
                                   post_stats['edges']),
        'nodes': '{0}->{1}'.format(post_stats['nodes_before'],
                                   post_stats['nodes']),
        'bridged': post_stats.get('bridged', 0),
        'snapped': post_stats.get('snapped', 0),
        'comp_dropped': post_stats.get('components_dropped', 0),
        'loops_dropped': post_stats.get('loops_dropped', 0),
        'smooth': int(p.get('smooth_iters', 0))}))

    # §WS-Dev: число уникальных устройств на ребро (если есть исходные точки).
    if p.get('compute_devices', True) and device_pts is not None:
        dpx, dpy, ddev = device_pts
        edge_weights.count_devices(
            final, dpx, dpy, ddev, max_dist_m=3.0 * p['cell_tau'])
        _lg(run_log.format_stage('devices', {'points': len(ddev)}))

    _emit(progress, 0.97, 'reproject')
    _attach_lonlat(final, projector)

    stats = dict(clean_stats)
    stats.update({'near_dup_removed': thin_removed,
                  'tracks': len(tracks), 'points': n_points,
                  'edges': final.edge_count(), 'nodes': final.node_count()})
    stats.update(stats_extra)
    _emit(progress, 1.0, 'done')
    return {'graph': final, 'projector': projector, 'stats': stats,
            'params': p}


def _partial(progress, stage, p, clean_stats, thin_removed,
             tracks=None, projector=None):
    """Частичный результат при остановке после этапа (пошаговый режим, §WS-F)."""
    stats = dict(clean_stats)
    stats.update({'near_dup_removed': thin_removed, 'stage': stage})
    if tracks is not None:
        stats['tracks'] = len(tracks)
        stats['points'] = int(sum(len(t) for t in tracks))
    _emit(progress, 1.0, 'done')
    return {'graph': None, 'projector': projector, 'tracks': tracks,
            'stats': stats, 'params': p, 'partial': True, 'stage': stage}


def _split_tracks(segmented, x_all, y_all, min_points=2):
    """Нарезать спроецированные точки по под-трекам (без ресэмпла).

    Треки в `segmented` идут непрерывными блоками (assign_segments), поэтому
    границы находим по смене track_id за один проход — без groupby и без
    пер-трекового вызова pyproj (§A1/A2). `min_points` — минимум точек в
    под-треке (2 для Slide; 1 для KDE, чтобы учесть одиночные фиксы).
    """
    tid = segmented[TRACK_ID].to_numpy()
    n = len(tid)
    if n == 0:
        return []
    xy = np.column_stack([np.asarray(x_all, dtype=float),
                          np.asarray(y_all, dtype=float)])
    change = np.nonzero(tid[1:] != tid[:-1])[0] + 1
    starts = np.concatenate(([0], change))
    ends = np.concatenate((change, [n]))
    return [xy[s:e] for s, e in zip(starts, ends) if e - s >= min_points]


def _attach_lonlat(graph, projector):
    """Добавить географическую геометрию (EPSG:4326): рёбрам 'coords_lonlat',
    узлам — graph.node_lonlat."""
    for edge in graph.edges:
        coords = edge.get('coords')
        if coords is None or len(coords) == 0:
            edge['coords_lonlat'] = np.zeros((0, 2))
            continue
        lon, lat = projector.inverse(coords[:, 0], coords[:, 1])
        edge['coords_lonlat'] = np.column_stack([lon, lat])

    node_lonlat = {}
    for nid, (x, y) in graph.nodes.items():
        lon, lat = projector.inverse(x, y)
        node_lonlat[nid] = (float(lon), float(lat))
    graph.node_lonlat = node_lonlat
