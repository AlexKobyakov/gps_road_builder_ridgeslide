# -*- coding: utf-8 -*-
"""Offline tests for histogram log-scale binning (WS-G)."""

import numpy as np

from gps_road_builder.core import histogram


def test_log_scale_counts_all_values():
    # Heavily skewed: many zeros/small + a few large. Log bins must count all.
    values = [0, 0, 0, 0, 1, 2, 3, 50, 100]
    counts, edges = histogram.compute_histogram(values, bins=6, scale='log')
    assert counts.sum() == len(values)
    assert len(edges) == 7
    # edges are returned as real values (shifted back): starts at 0, ends ~max
    assert abs(edges[0] - 0.0) < 1e-6
    assert abs(edges[-1] - 100.0) < 1e-6


def test_log_scale_spreads_skew_better_than_linear():
    # With a dominant zero-bin, linear puts almost everything in one bin;
    # log spreads the large tail into its own bins.
    values = np.concatenate([np.zeros(100), [1000.0]])
    lin_counts, _ = histogram.compute_histogram(values, bins=8, scale='linear')
    log_counts, _ = histogram.compute_histogram(values, bins=8, scale='log')
    # linear: one bin ~100, others empty; log: the 1000 lands in the last bin
    assert log_counts[-1] >= 1
    assert lin_counts.max() == 100


def test_log_scale_empty():
    counts, edges = histogram.compute_histogram([], scale='log')
    assert counts.size == 0 and edges.size == 0


def test_linear_still_default():
    counts, edges = histogram.compute_histogram([1, 1, 2, 3, 3, 3], bins=3)
    assert counts.sum() == 6
