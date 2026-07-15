# -*- coding: utf-8 -*-
"""
Pytest bootstrap: make the plugin importable as the canonical `gps_road_builder`
package WITHOUT QGIS and REGARDLESS of the checkout folder name.

The plugin package lives at the repository ROOT (flat layout). Tests import it
by its canonical name `gps_road_builder`, but the importable top-level name
otherwise follows the checkout FOLDER name — which differs between the dev repo
(`gps_road_builder`) and the public release repo (`gps_road_builder_ridgeslide`).
Relying on the folder name broke CI in the public repo, so we register the repo
root under the canonical name explicitly.

Only modules free of qgis/PyQt imports are exercised by the offline test suite;
the plugin's __init__.py is safe to execute (it only defines classFactory, which
imports qgis lazily).
"""

import importlib.util
import os
import sys

_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PARENT = os.path.dirname(_PLUGIN_DIR)

# Harmless: works when the checkout folder happens to be named
# `gps_road_builder` (e.g. the dev repo). The explicit registration below is
# what makes it robust to any other folder name (the public release repo).
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

if 'gps_road_builder' not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        'gps_road_builder', os.path.join(_PLUGIN_DIR, '__init__.py'),
        submodule_search_locations=[_PLUGIN_DIR])
    _module = importlib.util.module_from_spec(_spec)
    sys.modules['gps_road_builder'] = _module
    _spec.loader.exec_module(_module)
