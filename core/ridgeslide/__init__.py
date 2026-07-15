# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
RidgeSlide — density-ridge trajectory consolidation and road-centerline
inference (the engine behind GPS Road Builder).

RidgeSlide is an independent Python/NumPy/Numba reimplementation of the Slide
trajectory-refinement approach (paulmach/slide, MIT), with the corrections of
Guo et al. (2020) and original additions (percentile thresholding,
post-processing, diagnostics, parallel Numba execution). Conceived, generalized,
developed and completed by Alexander Kobyakov.

This subpackage is licensed under the MIT License (see LICENSE / NOTICE in this
folder); the surrounding QGIS plugin is GPLv3. The package is QGIS-agnostic — it
must never import ``qgis`` or ``PyQt`` (enforced by tests/test_core_no_qgis.py).

Public API:
    RidgeSlide, RidgeSlideConfig, RidgeSlideResult
"""

from .api import RidgeSlide, RidgeSlideConfig, RidgeSlideResult

__all__ = ['RidgeSlide', 'RidgeSlideConfig', 'RidgeSlideResult']
