# -*- coding: utf-8 -*-
"""
Package the GPS Road Builder (RidgeSlide) plugin into an installable QGIS zip.
Собирает dist/gps_road_builder_ridgeslide.zip только из файлов плагина, исключая
данные, документацию, тесты и служебные каталоги (чтобы zip был компактным и
подходил для официального реестра QGIS). Имя папки внутри zip = PLUGIN_NAME =
идентификатор плагина в QGIS/реестре; внутренние id (QSettings/логи/libs)
остаются 'gps_road_builder' — это внутренние строки, от имени папки не зависят.

Использование:
    python scripts/build_plugin.py
    python scripts/build_plugin.py --qgis4-smoke
"""

import argparse
import os
import zipfile

PLUGIN_NAME = 'gps_road_builder_ridgeslide'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')

# Каталоги и файлы верхнего уровня, которые НЕ входят в плагин.
EXCLUDE_DIRS = {
    '.git', '.github', '.claude', 'article', 'data', 'reserch', 'docs',
    'tests', 'scripts', 'dist', '__pycache__', '.pytest_cache', '.venv', '_libs', 'libs',
    'test_temp', 'memory',
}
EXCLUDE_TOP_FILES = {
    'requirements-dev.txt', 'requirements-test.txt', 'setup.cfg',
    'README.md', '.gitignore', '.gitattributes',
}
EXCLUDE_SUFFIXES = ('.pyc', '.pyo')


def _included_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = os.path.relpath(dirpath, ROOT)
        top = rel_dir.split(os.sep)[0]
        if rel_dir != '.' and top in EXCLUDE_DIRS:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            if name.endswith(EXCLUDE_SUFFIXES):
                continue
            if rel_dir == '.' and name in EXCLUDE_TOP_FILES:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, ROOT)
            yield full, rel


def _qgis4_smoke_metadata(text):
    """Raise the ceiling in legacy metadata; no-op after QGIS 4 release."""
    source = 'qgisMaximumVersion=3.99'
    if 'qgisMaximumVersion=4.99' in text:
        return text
    if source not in text:
        raise ValueError('Expected production QGIS maximum version not found')
    return text.replace(source, 'qgisMaximumVersion=4.99', 1)


def build(qgis4_smoke=False):
    os.makedirs(DIST, exist_ok=True)
    suffix = '_qgis4_smoke' if qgis4_smoke else ''
    out = os.path.join(DIST, PLUGIN_NAME + suffix + '.zip')
    count = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for full, rel in _included_files():
            # внутри zip файлы кладём в папку с именем плагина
            archive_name = os.path.join(PLUGIN_NAME, rel)
            if qgis4_smoke and rel == 'metadata.txt':
                with open(full, encoding='utf-8') as metadata:
                    zf.writestr(archive_name, _qgis4_smoke_metadata(metadata.read()))
            else:
                zf.write(full, archive_name)
            count += 1
    print('Wrote {0} ({1} files)'.format(out, count))
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--qgis4-smoke', action='store_true',
        help='build a local-only ZIP that allows QGIS 4.x for runtime smoke')
    args = parser.parse_args()
    build(qgis4_smoke=args.qgis4_smoke)
