# -*- coding: utf-8 -*-
"""
Pipeline checkpointing for GPS Road Builder (§WS-D of the update plan).
Сохранение/загрузка промежуточных результатов, чтобы при подборе настроек не
перезапускать весь долгий конвейер (замечание 5.3 тестировщика).

Два чекпоинта (самые дорогие этапы):
  - `points` — очищенные и прореженные точки (DataFrame) после read→clean→thin;
  - `tracks` — спроецированные под-треки (метрические) после segmentize→project→
    resample, плюс proj4 рабочего кадра (для обратной репроекции результата).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import json
import os

import numpy as np

POINTS_DATA = 'points.pkl'
POINTS_META = 'points.json'
TRACKS_DATA = 'tracks.npz'
TRACKS_META = 'tracks.json'


def has_points(cache_dir):
    return bool(cache_dir) and os.path.isfile(os.path.join(cache_dir, POINTS_DATA))


def has_tracks(cache_dir):
    return bool(cache_dir) and os.path.isfile(os.path.join(cache_dir, TRACKS_DATA))


def _write_json(path, meta):
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)


def _read_json(path):
    if not os.path.isfile(path):
        return {}
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def save_points(cache_dir, df, meta=None):
    """Сохранить очищенные/прореженные точки (DataFrame → pickle)."""
    os.makedirs(cache_dir, exist_ok=True)
    df.to_pickle(os.path.join(cache_dir, POINTS_DATA))
    _write_json(os.path.join(cache_dir, POINTS_META), dict(meta or {}))


def load_points(cache_dir):
    """Загрузить точки: (DataFrame, meta)."""
    import pandas as pd
    df = pd.read_pickle(os.path.join(cache_dir, POINTS_DATA))
    return df, _read_json(os.path.join(cache_dir, POINTS_META))


def save_tracks(cache_dir, tracks, proj4, meta=None):
    """Сохранить под-треки (CSR-массив npz) и proj4 рабочего кадра."""
    os.makedirs(cache_dir, exist_ok=True)
    arrays = [np.asarray(t, dtype=float) for t in tracks if len(t) > 0]
    lengths = [len(a) for a in arrays]
    offsets = np.zeros(len(arrays) + 1, dtype=np.int64)
    if lengths:
        offsets[1:] = np.cumsum(lengths)
    pts = np.vstack(arrays) if arrays else np.zeros((0, 2))
    np.savez(os.path.join(cache_dir, TRACKS_DATA), pts=pts, offsets=offsets)
    m = dict(meta or {})
    m['proj4'] = proj4
    _write_json(os.path.join(cache_dir, TRACKS_META), m)


def load_tracks(cache_dir):
    """Загрузить под-треки: (список массивов Ni×2, proj4, meta)."""
    data = np.load(os.path.join(cache_dir, TRACKS_DATA))
    pts = data['pts']
    offsets = data['offsets']
    tracks = [pts[int(offsets[i]):int(offsets[i + 1])].copy()
              for i in range(len(offsets) - 1)]
    meta = _read_json(os.path.join(cache_dir, TRACKS_META))
    return tracks, meta.get('proj4'), meta
