# -*- coding: utf-8 -*-
"""Guard test: the RidgeSlide algorithm core must never import qgis or PyQt.

The processing/algorithm core is QGIS-agnostic by design (the algorithm↔
application boundary, ADD4 п.10): RidgeSlide, density, graph, preprocess,
splitmerge, the pipeline and the pure IO/parsers. This test enforces the
invariant machine-checkably so it cannot silently regress.

A small ADAPTER layer under core/ is the documented exception — thin QGIS glue
(settings via QSettings, the dependency installer, the QGIS profile log path,
the SHP/GPKG writer). It will move out of the algorithm core when RidgeSlide is
fully extracted as a standalone library. Everything ELSE under core/ must stay
pure."""

import io
import os
import re

import gps_road_builder.core as core_pkg

# QGIS-coupled adapter modules (the exception — not part of the algorithm core).
_ADAPTER = {
    'settings_manager.py',                      # QSettings
    'logging_setup.py',                         # QgsApplication profile path
    os.path.join('deps', 'installer.py'),       # QgsApplication
    os.path.join('deps', 'install_worker.py'),  # QObject/pyqtSignal
    os.path.join('io', 'writer.py'),            # QgsVectorFileWriter (SHP/GPKG)
}

# A line that (after optional whitespace) starts with `import`/`from` and then
# names qgis or PyQt — i.e. an actual import statement, not a mention in prose.
_FORBIDDEN = re.compile(r'^\s*(from|import)\s+(qgis|PyQt5|PyQt6|PyQt)\b',
                        re.MULTILINE)


def test_algorithm_core_has_no_qgis_or_pyqt_imports():
    root = os.path.dirname(os.path.abspath(core_pkg.__file__))
    offenders = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith('.py'):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if rel in _ADAPTER:
                continue
            with io.open(path, encoding='utf-8') as fh:
                if _FORBIDDEN.search(fh.read()):
                    offenders.append(rel)
    assert not offenders, \
        'algorithm core must not import qgis/PyQt, found in: {0}'.format(
            offenders)


def test_ridgeslide_package_is_pure():
    """RidgeSlide specifically (the extractable library) must be qgis-free."""
    root = os.path.join(os.path.dirname(os.path.abspath(core_pkg.__file__)),
                        'ridgeslide')
    for name in os.listdir(root):
        if name.endswith('.py'):
            with io.open(os.path.join(root, name), encoding='utf-8') as fh:
                assert not _FORBIDDEN.search(fh.read()), \
                    'ridgeslide/{0} must not import qgis/PyQt'.format(name)
