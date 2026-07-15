# -*- coding: utf-8 -*-
"""Offline tests for splitmerge (tiling + node/graph merging)."""

from collections import defaultdict

import numpy as np

from gps_road_builder.core.splitmerge import splitter, merger
from gps_road_builder.core.graph.to_graph import RoadGraph


# --- splitter ---

def test_plan_tiles_grid_and_overlap():
    tiles = splitter.plan_tiles((0.0, 0.0, 100.0, 100.0),
                                tile_size=50.0, overlap=5.0)
    assert len(tiles) == 4                       # 2x2
    # cores tile the bounds without gaps
    assert tiles[0]['core'] == (0.0, 0.0, 50.0, 50.0)
    # rects extend by the overlap
    assert tiles[0]['rect'] == (-5.0, -5.0, 55.0, 55.0)


def test_assign_tracks_splits_across_tiles():
    tiles = splitter.plan_tiles((0.0, 0.0, 100.0, 100.0),
                                tile_size=50.0, overlap=2.0)
    track = np.column_stack([np.linspace(0, 100, 21), np.full(21, 25.0)])
    per_tile = splitter.assign_tracks_to_tiles([track], tiles)
    # horizontal track at y=25 hits the two bottom tiles (i=0 and i=1, j=0)
    hit = [len(t) for t in per_tile]
    assert sum(1 for h in hit if h > 0) == 2


def _assign_bruteforce(tracks, tiles):
    """Эталон: перебор всех тайлов (старая логика) для проверки быстрой."""
    per_tile = [[] for _ in tiles]
    for k, tile in enumerate(tiles):
        rx0, ry0, rx1, ry1 = tile['rect']
        for tr in tracks:
            tr = np.asarray(tr, dtype=float)
            if len(tr) < 2:
                continue
            inside = ((tr[:, 0] >= rx0) & (tr[:, 0] <= rx1)
                      & (tr[:, 1] >= ry0) & (tr[:, 1] <= ry1))
            for s, e in splitter._runs(inside):
                if e - s >= 2:
                    per_tile[k].append(tr[s:e])
    return per_tile


def _canon(per_tile):
    return [sorted(tuple(map(tuple, sub)) for sub in bucket) for bucket in per_tile]


def test_fast_assign_matches_bruteforce():
    tiles = splitter.plan_tiles((0.0, 0.0, 100.0, 100.0),
                                tile_size=25.0, overlap=3.0)   # 4x4 = 16 tiles
    rng = np.random.default_rng(0)
    tracks = []
    for _ in range(40):
        start = rng.uniform(0, 90, size=2)
        pts = start + np.cumsum(rng.uniform(-8, 8, size=(6, 2)), axis=0)
        tracks.append(pts)
    fast = _canon(splitter.assign_tracks_to_tiles(tracks, tiles))
    brute = _canon(_assign_bruteforce(tracks, tiles))
    assert fast == brute


def test_choose_tiling_modes():
    b = (0.0, 0.0, 1000.0, 1000.0)
    assert len(splitter.choose_tiling(b, 10, tau=3.0, split_mode='off')) == 1
    assert len(splitter.choose_tiling(b, 10, tau=3.0, split_mode='auto',
                                      max_points_per_tile=1000)) == 1
    forced = splitter.choose_tiling(b, 10, tau=3.0, split_mode='forced',
                                    tile_grid=(2, 2))
    assert len(forced) == 4


# --- merger ---

def _degrees(graph):
    deg = defaultdict(int)
    for e in graph.edges:
        deg[e['u']] += 1
        deg[e['v']] += 1
    return deg


def test_merge_close_nodes_collapses_cluster():
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (0.5, 0.0), 2: (0.0, 0.4), 3: (10.0, 0.0)}
    g.edges = [
        {'u': 0, 'v': 3, 'length': 10.0, 'frequency': 2},
        {'u': 1, 'v': 2, 'length': 0.6, 'frequency': 1},   # stub inside cluster
    ]
    merged = merger.merge_close_nodes(g, dist=1.0)
    assert merged.node_count() == 2       # {0,1,2} -> 1, {3} -> 1
    assert merged.edge_count() == 1       # stub dropped, long edge kept
    assert merged.edges[0]['length'] == 10.0


def test_merge_close_nodes_dedups_parallel_overlap_edges():
    g = RoadGraph()
    g.nodes = {0: (0.0, 0.0), 1: (10.0, 0.0)}
    g.edges = [
        {'u': 0, 'v': 1, 'length': 10.0, 'frequency': 1},
        {'u': 0, 'v': 1, 'length': 10.0, 'frequency': 3},   # duplicate (overlap)
    ]
    merged = merger.merge_close_nodes(g, dist=0.5)
    assert merged.edge_count() == 1
    assert merged.edges[0]['frequency'] == 4                # frequencies summed


def test_merge_graphs_stitches_boundary():
    g1 = RoadGraph()
    g1.nodes = {0: (0.0, 0.0), 1: (5.0, 0.0)}
    g1.edges = [{'u': 0, 'v': 1, 'length': 5.0, 'frequency': 1,
                 'coords': np.array([[0.0, 0.0], [5.0, 0.0]])}]
    g2 = RoadGraph()
    g2.nodes = {0: (5.1, 0.0), 1: (10.0, 0.0)}
    g2.edges = [{'u': 0, 'v': 1, 'length': 4.9, 'frequency': 1,
                 'coords': np.array([[5.1, 0.0], [10.0, 0.0]])}]
    merged = merger.merge_graphs([g1, g2], lambda_dis=1.0)
    assert merged.node_count() == 3        # 0, merged(5/5.1), 10
    assert merged.edge_count() == 2
    assert max(_degrees(merged).values()) == 2   # middle node connects both
