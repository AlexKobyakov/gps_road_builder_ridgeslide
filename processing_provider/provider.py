# -*- coding: utf-8 -*-
"""Provider registration class for GPS Road Builder Processing algorithms."""

from qgis.core import QgsProcessingProvider

from ..translation_manager import translations
from .algorithms import (
    BuildNetworkFromFolderAlgorithm, BuildNetworkFromLayerAlgorithm,
    PostprocessNetworkAlgorithm,
)
from .ids import PROVIDER_ID


class GpsRoadBuilderProvider(QgsProcessingProvider):
    """Expose the three stable public GPS Road Builder workflows."""

    def loadAlgorithms(self):
        self.addAlgorithm(BuildNetworkFromLayerAlgorithm())
        self.addAlgorithm(BuildNetworkFromFolderAlgorithm())
        self.addAlgorithm(PostprocessNetworkAlgorithm())

    def id(self):
        return PROVIDER_ID

    def name(self):
        return translations.get_text('processing_provider_name')

    def longName(self):
        return self.name()
