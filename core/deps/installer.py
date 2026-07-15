# -*- coding: utf-8 -*-
"""
Dependency installer for GPS Road Builder (pure logic, no Qt).

Two user-selected backends install the *real* optional libraries — no degraded
fallbacks and no silent auto-install (compatible with the official QGIS plugin
repository rules). See docs/PLAN_REALIZACII.md §7.

  A. pip -> target : `pip install --target=<libs> <spec>` on the QGIS Python.
  B. prebuilt wheels: download a curated wheel bundle (zip) from a mirror,
     extract it and `pip install --no-index --find-links=<dir> --target=<libs>`.
  C. from a local folder of *.whl (offline variant of B).

Everything is installed into a plugin-local libs directory that is added to
sys.path, so the system Python is never touched.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import importlib.util
import os
import subprocess  # nosec B404 - used only to run the QGIS python's own pip
import sys
import urllib.parse
import urllib.request
import zipfile

USER_AGENT = 'QGIS-GpsRoadBuilder/0.1 (+https://github.com/AlexKobyakov/gps_road_builder)'

# Разрешённые схемы URL (безопасность, CWE-22): только http/https.
ALLOWED_SCHEMES = ('http', 'https')

# Реестр опциональных зависимостей.
#   import_name : имя для проверки `import`
#   pip_spec    : спецификатор для pip
#   purpose_key : ключ перевода назначения
#   optional    : всегда True в Фазе 0 (все ускорители необязательны)
#   wheel_bundles: словарь platform_tag -> список URL-зеркал с zip колёс
#                  (заполняется мейнтейнером; пусто = способ B недоступен)
PACKAGES = {
    'numba': {
        'import_name': 'numba',
        'pip_spec': 'numba',
        'purpose_key': 'deps_purpose_numba',
        'optional': True,
        'wheel_bundles': {},
    },
    'scikit-image': {
        'import_name': 'skimage',
        'pip_spec': 'scikit-image',
        'purpose_key': 'deps_purpose_skimage',
        'optional': True,
        'wheel_bundles': {},
    },
    'pyarrow': {
        'import_name': 'pyarrow',
        'pip_spec': 'pyarrow',
        'purpose_key': 'deps_purpose_pyarrow',
        'optional': True,
        'wheel_bundles': {},
    },
    'scikit-learn': {
        'import_name': 'sklearn',
        'pip_spec': 'scikit-learn',
        'purpose_key': 'deps_purpose_sklearn',
        'optional': True,
        'wheel_bundles': {},
    },
}


# ---------------------------------------------------------------------------
# libs-каталог плагина и sys.path
# ---------------------------------------------------------------------------

def libs_dir():
    """Каталог для доустановленных библиотек внутри профиля QGIS.

    В обычном режиме — `<профиль QGIS>/gps_road_builder/libs`. Вне QGIS
    (например, в тестах) — `<домашний>/.gps_road_builder/libs`.
    """
    base = None
    try:
        from qgis.core import QgsApplication
        base = QgsApplication.qgisSettingsDirPath()
    except Exception:
        base = None
    if not base:
        base = os.path.join(os.path.expanduser('~'), '.gps_road_builder')
    path = os.path.join(base, 'gps_road_builder', 'libs')
    os.makedirs(path, exist_ok=True)
    return path


def ensure_on_path(path=None):
    """Добавить libs-каталог в начало sys.path (идемпотентно)."""
    path = path or libs_dir()
    if path not in sys.path:
        sys.path.insert(0, path)
    return path


# ---------------------------------------------------------------------------
# Проверки состояния
# ---------------------------------------------------------------------------

def is_installed(import_name):
    """Доступна ли библиотека для импорта в текущем окружении."""
    try:
        return importlib.util.find_spec(import_name) is not None
    except (ImportError, ValueError):
        return False


def package_status():
    """Список (name, import_name, purpose_key, installed) по всем пакетам."""
    result = []
    for name, cfg in PACKAGES.items():
        result.append((
            name,
            cfg['import_name'],
            cfg['purpose_key'],
            is_installed(cfg['import_name']),
        ))
    return result


def python_executable():
    """Лучшее приближение к интерпретатору Python для запуска pip.

    В QGIS `sys.executable` иногда указывает на исполняемый файл приложения
    (Windows/OSGeo4W), а не на python. Пытаемся найти python рядом.
    """
    exe = sys.executable or ''
    if exe and os.path.basename(exe).lower().startswith('python'):
        return exe
    # Ищем python в каталоге текущего исполняемого файла
    if exe:
        folder = os.path.dirname(exe)
        for cand in ('python3', 'python', 'python3.exe', 'python.exe'):
            p = os.path.join(folder, cand)
            if os.path.isfile(p):
                return p
    return exe or 'python'


def pip_available(python=None):
    """Доступен ли `pip` в интерпретаторе QGIS."""
    python = python or python_executable()
    try:
        # nosec B603: не shell, аргументы фиксированы (интерпретатор + `-m pip`),
        # пользовательского ввода в команде нет.
        proc = subprocess.run(  # nosec B603
            [python, '-m', 'pip', '--version'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=30, **_no_window())
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


# ---------------------------------------------------------------------------
# Построение команд pip (чистые функции — покрыты тестами)
# ---------------------------------------------------------------------------

def build_pip_command(specs, target, python=None, find_links=None,
                      no_index=False):
    """Собрать команду `pip install --target=<target> ...`.

    Args:
        specs: список спецификаторов пакетов (напр. ['numba']).
        target: каталог установки (--target).
        python: путь к интерпретатору (по умолчанию — python_executable()).
        find_links: каталог с локальными колёсами (для оффлайн/готовых сборок).
        no_index: не обращаться к PyPI (True при установке из колёс/папки).
    """
    python = python or python_executable()
    cmd = [python, '-m', 'pip', 'install',
           '--target', target, '--upgrade', '--no-input',
           '--disable-pip-version-check']
    if no_index:
        cmd.append('--no-index')
    if find_links:
        cmd += ['--find-links', find_links]
    cmd += list(specs)
    return cmd


# ---------------------------------------------------------------------------
# Безопасная работа с сетью и архивами (порт из garmin_export/downloader)
# ---------------------------------------------------------------------------

def _build_web_opener():
    opener = urllib.request.OpenerDirector()
    for handler in (
        urllib.request.ProxyHandler(),
        urllib.request.HTTPHandler(),
        urllib.request.HTTPSHandler(),
        urllib.request.HTTPDefaultErrorHandler(),
        urllib.request.HTTPRedirectHandler(),
        urllib.request.HTTPErrorProcessor(),
    ):
        opener.add_handler(handler)
    return opener


_WEB_OPENER = _build_web_opener()


def open_url(url, timeout=120):
    """Открыть URL только по http/https (защита от file:/ftp:/data:)."""
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError('Disallowed URL scheme: {0}'.format(scheme or '(empty)'))
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    return _WEB_OPENER.open(request, timeout=timeout)


def _is_within(base_dir, target_path):
    """Защита от zip-slip: target_path должен быть внутри base_dir."""
    base = os.path.abspath(base_dir)
    target = os.path.abspath(target_path)
    return target == base or target.startswith(base + os.sep)


def safe_extract_zip(archive_path, dest_dir):
    """Безопасно распаковать zip (проверка path traversal)."""
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(archive_path) as zf:
        for name in zf.namelist():
            out_path = os.path.join(dest_dir, name)
            if not _is_within(dest_dir, out_path):
                raise ValueError('Unsafe path in archive: {0}'.format(name))
        zf.extractall(dest_dir)
    return dest_dir


def _download(url, dest_path, progress_cb=None, cancelled_cb=None):
    with open_url(url) as response:
        try:
            total = int(response.headers.get('Content-Length') or 0)
        except (TypeError, ValueError, AttributeError):
            total = 0
        received = 0
        with open(dest_path, 'wb') as out:
            while True:
                if cancelled_cb and cancelled_cb():
                    raise InterruptedError()
                chunk = response.read(65536)
                if not chunk:
                    break
                out.write(chunk)
                received += len(chunk)
                if progress_cb:
                    progress_cb(received, total, '')
    return dest_path


# ---------------------------------------------------------------------------
# Бэкенды установки
# ---------------------------------------------------------------------------

def _no_window():
    """Не показывать консольное окно на Windows при запуске subprocess."""
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {'startupinfo': startupinfo}
    return {}


def _run_pip(cmd, progress_cb=None, cancelled_cb=None):
    """Запустить pip, транслируя вывод в progress_cb; поддержка отмены."""
    # nosec B603: не shell; `cmd` собирается плагином (интерпретатор + pip +
    # имена пакетов из реестра PACKAGES), не из произвольного ввода пользователя.
    proc = subprocess.Popen(  # nosec B603
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, **_no_window())
    try:
        for line in iter(proc.stdout.readline, ''):
            if cancelled_cb and cancelled_cb():
                proc.terminate()
                raise InterruptedError()
            if progress_cb and line.strip():
                progress_cb(0, 0, line.strip())
    finally:
        proc.stdout.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError('pip exited with code {0}'.format(ret))


def install_via_pip(specs, target=None, progress_cb=None, cancelled_cb=None,
                    python=None):
    """Backend A: установка из PyPI в libs-каталог плагина."""
    target = target or libs_dir()
    cmd = build_pip_command(specs, target, python=python)
    _run_pip(cmd, progress_cb, cancelled_cb)
    ensure_on_path(target)
    return target


def install_from_folder(specs, folder, target=None, progress_cb=None,
                        cancelled_cb=None, python=None):
    """Backend C: установка из локальной папки с колёсами (оффлайн)."""
    target = target or libs_dir()
    cmd = build_pip_command(specs, target, python=python,
                            find_links=folder, no_index=True)
    _run_pip(cmd, progress_cb, cancelled_cb)
    ensure_on_path(target)
    return target


def install_via_wheels(specs, wheel_urls, target=None, progress_cb=None,
                       cancelled_cb=None, python=None, work_dir=None):
    """Backend B: скачать zip(ы) колёс с зеркала, распаковать и поставить."""
    target = target or libs_dir()
    work_dir = work_dir or os.path.join(target, '_wheels')
    os.makedirs(work_dir, exist_ok=True)

    errors = []
    extracted = False
    for url in wheel_urls:
        try:
            if progress_cb:
                progress_cb(0, 0, urllib.parse.urlparse(url).netloc)
            archive = os.path.join(work_dir, 'bundle.zip')
            _download(url, archive, progress_cb, cancelled_cb)
            safe_extract_zip(archive, work_dir)
            extracted = True
            break
        except InterruptedError:
            raise
        except Exception as exc:  # переходим к следующему зеркалу
            errors.append(str(exc))
            continue

    if not extracted:
        raise RuntimeError('Could not fetch wheel bundle: {0}'
                           .format('; '.join(errors) or 'no mirrors configured'))

    return install_from_folder(specs, work_dir, target=target,
                               progress_cb=progress_cb,
                               cancelled_cb=cancelled_cb, python=python)
