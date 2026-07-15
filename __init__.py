# -*- coding: utf-8 -*-
"""
GPS Road Builder — QGIS plugin
Восстановление связного графа лесных дорог из сырых GPS-треков лесовозной техники.

Ядро метода: Guo et al. (2020), «A scalable method to construct compact road
networks from GPS trajectories» — плотностный четырёхшаговый подход с
улучшенным Slide, скелетизацией и взвешиванием рёбер. См. docs/PLAN_REALIZACII.md.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Organization: Lesburo
Year: 2026

Modular architecture:
- plugin.py           : main plugin class (QGIS integration)
- gui/                : UI chassis (tabbed dialog, header, dialogs) — design ported
                        from the garmin_export plugin
- core/               : pure algorithmic core + settings + dependency installer
- tasks/              : QgsTask background wrappers
- translations/       : multi-language UI strings (RU, EN)
"""


def classFactory(iface):
    """Точка входа QGIS-плагина.

    Args:
        iface: объект интерфейса QGIS (QgisInterface).

    Returns:
        GpsRoadBuilderPlugin: экземпляр основного класса плагина.
    """
    from .plugin import GpsRoadBuilderPlugin
    return GpsRoadBuilderPlugin(iface)
