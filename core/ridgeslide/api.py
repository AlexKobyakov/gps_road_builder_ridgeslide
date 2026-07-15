# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
Public API façade for RidgeSlide.

A small, stable surface over the density-ridge pipeline so the algorithm can be
used as a library — from the QGIS plugin, plain Python, notebooks or a CLI —
without touching the internal modules. The QGIS plugin's own pipeline stays a
client of these lower-level pieces and will migrate onto this façade gradually.

Contract: ``fit`` takes ``tracks`` as a list of ``(n, 2)`` arrays in **planar,
projected, metric** coordinates (metres). RidgeSlide does NOT accept geographic
longitude/latitude — the cell size τ, smoothing σ and edge lengths only make
sense in linear units. Project first (the plugin uses a data-centered Transverse
Mercator; see core/density/projection.py).

Author: Alexander Kobyakov (kobyakov@lesburo.ru), 2026
"""

import numpy as np

from . import refine
from ..density import blur
from ..graph import (binarize, skeletonize, to_graph, edge_weights,
                     simplify as simplify_mod)
from ..splitmerge import merger


class RidgeSlideConfig:
    """Parameters of the RidgeSlide method (density-ridge road inference).

    Attributes mirror the plugin's density/graph settings but are decoupled from
    QGIS/QSettings. All distances are in the planar metric unit of the input.
    """

    def __init__(self, cell=5.0, sigma1=5.0, sigma2=3.0, sharpness=1.5,
                 min_loops=100, max_loops=4000, backend='auto',
                 eps_mode='otsu', eps_value=0.0, eps_percentile=80.0,
                 skeleton_backend='auto', dp_tolerance=2.0,
                 edge_f_min=1, edge_l_min=0.0, node_merge_m=None):
        self.cell = float(cell)
        self.sigma1 = float(sigma1)
        self.sigma2 = float(sigma2)
        self.sharpness = float(sharpness)
        self.min_loops = int(min_loops)
        self.max_loops = int(max_loops)
        self.backend = str(backend)
        self.eps_mode = str(eps_mode)
        self.eps_value = float(eps_value)
        self.eps_percentile = float(eps_percentile)
        self.skeleton_backend = str(skeleton_backend)
        self.dp_tolerance = float(dp_tolerance)
        self.edge_f_min = int(edge_f_min)
        self.edge_l_min = float(edge_l_min)
        self.node_merge_m = (None if node_merge_m is None
                             else float(node_merge_m))


class RidgeSlideResult:
    """Result of :meth:`RidgeSlide.fit`.

    Attributes:
        graph: RoadGraph in planar coordinates (nodes ``(x, y)``; edges carry
            ``coords`` (N, 2), ``length``, ``frequency``).
        threshold: the density threshold used for binarization.
        density: the compacted density surface (Grid) or None for empty input.
        edges / nodes: counts, for convenience/diagnostics.
    """

    def __init__(self, graph, threshold, density):
        self.graph = graph
        self.threshold = float(threshold)
        self.density = density
        self.edges = graph.edge_count()
        self.nodes = graph.node_count()


def _validate_planar(tracks):
    """Проверить контракт входа: список массивов (n, 2). Возвращает список
    непустых треков как float64."""
    out = []
    for t in tracks:
        a = np.asarray(t, dtype=np.float64)
        if a.ndim != 2 or a.shape[1] != 2:
            raise ValueError(
                'RidgeSlide expects tracks as a list of (n, 2) planar arrays; '
                'got an array with shape {0}'.format(a.shape))
        if len(a) > 0:
            out.append(a)
    return out


def _binarize(values, cfg):
    if cfg.eps_mode == 'manual':
        return binarize.binarize(values, eps=cfg.eps_value, method='manual')
    if cfg.eps_mode == 'percentile':
        return binarize.binarize(values, method='percentile',
                                 percentile=cfg.eps_percentile)
    return binarize.binarize(values, method='otsu')


class RidgeSlide:
    """Density-ridge road-centerline inference.

    Example:
        >>> model = RidgeSlide(RidgeSlideConfig(cell=5.0))
        >>> result = model.fit(tracks)          # tracks: list of (n, 2) metres
        >>> result.graph.edge_count()
    """

    def __init__(self, config=None):
        self.config = config or RidgeSlideConfig()

    def fit(self, tracks):
        """Reconstruct a road network from planar tracks.

        Args:
            tracks: list of ``(n, 2)`` arrays in planar metric coordinates.

        Returns:
            RidgeSlideResult.
        """
        cfg = self.config
        non_empty = _validate_planar(tracks)
        empty = RidgeSlideResult(to_graph.RoadGraph(), 0.0, None)
        if not non_empty:
            return empty

        # 1) compact trajectories onto density ridges (Slide/refine)
        compact = refine.compact_density(
            non_empty, cell=cfg.cell, sigma1=cfg.sigma1, sigma2=cfg.sigma2,
            sharpness=cfg.sharpness, min_iter=cfg.min_loops,
            max_iter=cfg.max_loops, backend=cfg.backend)
        adjusted = compact['adjusted_tracks']
        grid = compact['density']
        if grid is None or not adjusted:
            return empty

        # 2) density surface → mask → centerline skeleton → graph
        smoothed = blur.smooth_density(grid.values, cfg.sigma2,
                                       sharpness=cfg.sharpness)
        mask, threshold = _binarize(smoothed, cfg)
        skeleton = skeletonize.skeletonize(mask, backend=cfg.skeleton_backend)
        graph = to_graph.to_graph(skeleton)

        # 3) weight, simplify, filter, world-project, merge junction clusters
        edge_weights.compute_frequencies(graph, adjusted, grid)
        simplify_mod.simplify_graph(graph, grid, epsilon_m=cfg.dp_tolerance)
        graph, _removed = edge_weights.filter_edges(
            graph, f_min=cfg.edge_f_min, l_min=cfg.edge_l_min,
            protect_long_m=None)
        world = merger.to_world_graph(graph, grid)
        node_merge = cfg.node_merge_m or (1.5 * cfg.cell)
        world = merger.merge_close_nodes(world, dist=node_merge)
        return RidgeSlideResult(world, threshold, grid)
