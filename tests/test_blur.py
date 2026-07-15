# -*- coding: utf-8 -*-
"""Offline tests for density.blur."""

import numpy as np

from gps_road_builder.core.density import blur


def test_kernel_normalized_and_symmetric():
    k = blur.build_kernel(3.0, sharpness=1.5)
    assert abs(k.sum() - 1.0) < 1e-12
    assert np.allclose(k, k[::-1])
    assert k.argmax() == len(k) // 2  # peak in the centre


def test_kernel_zero_sigma():
    assert np.array_equal(blur.build_kernel(0.0), np.array([1.0]))


def test_kernel_sharpness_zero_is_gaussian_like():
    k = blur.build_kernel(3.0, sharpness=0.0)
    # monotonic decrease from centre outward
    half = k[len(k) // 2:]
    assert np.all(np.diff(half) <= 1e-12)


def test_separable_smooth_preserves_mass_interior():
    arr = np.zeros((41, 41))
    arr[20, 20] = 100.0
    k = blur.build_kernel(3.0, sharpness=1.0)
    out = blur.separable_smooth(arr, k)
    assert abs(out.sum() - 100.0) < 1e-6      # mass preserved (spike far from edge)
    assert out[20, 20] < 100.0                # spike spread out
    assert out[20, 21] > 0.0


def test_gradient_of_ramp():
    # values increasing along x (columns): gx ≈ const, gy ≈ 0
    xs = np.arange(10, dtype=float)
    arr = np.tile(xs, (10, 1))               # each row is 0..9
    gx, gy = blur.gradient(arr)
    assert np.allclose(gx, 1.0)
    assert np.allclose(gy, 0.0)
