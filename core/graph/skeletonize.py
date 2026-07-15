# -*- coding: utf-8 -*-
"""
Skeletonization of the binary road mask (Guo 2020 §3.4).
Использует scikit-image, если доступен; иначе — встроенная чистая numpy-версия
алгоритма Zhang–Suen («lite»-режим, §7 плана), чтобы пайплайн не зависел от
тяжёлого колеса.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np


def _zhang_suen(mask):
    """Утончение Zhang–Suen до скелета шириной 1 пиксель (векторно)."""
    img = (np.asarray(mask) > 0).astype(np.uint8)
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            padded = np.pad(img, 1)
            p2 = padded[0:-2, 1:-1]
            p3 = padded[0:-2, 2:]
            p4 = padded[1:-1, 2:]
            p5 = padded[2:, 2:]
            p6 = padded[2:, 1:-1]
            p7 = padded[2:, 0:-2]
            p8 = padded[1:-1, 0:-2]
            p9 = padded[0:-2, 0:-2]
            b = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            a = np.zeros_like(b)
            for i in range(8):
                a += ((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8)
            cond = (img == 1) & (b >= 2) & (b <= 6) & (a == 1)
            if step == 0:
                cond &= (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                cond &= (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            if cond.any():
                img[cond] = 0
                changed = True
    return img.astype(bool)


def skeletonize(mask, backend='auto'):
    """Скелетизировать бинарную маску.

    backend: 'auto' (skimage при наличии, иначе Zhang–Suen) | 'skimage' |
    'medial_axis' (медиальная ось — centerline из записки ФГИС ЛК, чище на
    толстых масках KDE) | 'zhang_suen'.
    """
    mask = np.asarray(mask) > 0
    if backend == 'medial_axis':
        from skimage.morphology import medial_axis
        return np.asarray(medial_axis(mask), dtype=bool)
    if backend in ('auto', 'skimage'):
        try:
            from skimage.morphology import skeletonize as _sk
            return np.asarray(_sk(mask), dtype=bool)
        except Exception:
            if backend == 'skimage':
                raise
    return _zhang_suen(mask)
