# -*- coding: utf-8 -*-
"""Runtime checks; executed by a QGIS Python test runner when available."""

import pytest


qgis_core = pytest.importorskip('qgis.core', reason='requires a QGIS Python runtime')


def test_provider_registers_once_and_unregisters_cleanly():
    """Exercise the registry contract without a GUI dialog or project layer."""
    from gps_road_builder.processing_provider.ids import ALGORITHM_IDS, PROVIDER_ID
    from gps_road_builder.processing_provider.provider import GpsRoadBuilderProvider

    registry = qgis_core.QgsApplication.processingRegistry()
    existing = registry.providerById(PROVIDER_ID)
    if existing is not None:
        pytest.skip('provider is already registered by the running plugin')
    provider = GpsRoadBuilderProvider()
    assert registry.addProvider(provider)
    try:
        assert registry.providerById(PROVIDER_ID) is provider
        assert tuple(algorithm.name() for algorithm in provider.algorithms()) == ALGORITHM_IDS
    finally:
        registry.removeProvider(provider)
    assert registry.providerById(PROVIDER_ID) is None
