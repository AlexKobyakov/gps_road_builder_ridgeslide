# -*- coding: utf-8 -*-
"""
Package the GPS Road Builder plugin into an installable QGIS zip.
Собирает dist/gps_road_builder.zip только из файлов плагина, исключая данные,
документацию, тесты и служебные каталоги (чтобы zip был компактным и подходил
для официального реестра QGIS).

Использование:
    python scripts/build_plugin.py
"""

import os
import zipfile

PLUGIN_NAME = 'gps_road_builder'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')

# Каталоги и файлы верхнего уровня, которые НЕ входят в плагин.
EXCLUDE_DIRS = {
    '.git', '.github', '.claude', 'article', 'data', 'reserch', 'docs',
    'tests', 'scripts', 'dist', '__pycache__', '.pytest_cache', '_libs', 'libs',
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


def build():
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, PLUGIN_NAME + '.zip')
    count = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for full, rel in _included_files():
            # внутри zip файлы кладём в папку с именем плагина
            zf.write(full, os.path.join(PLUGIN_NAME, rel))
            count += 1
    print('Wrote {0} ({1} files)'.format(out, count))
    return out


if __name__ == '__main__':
    build()
