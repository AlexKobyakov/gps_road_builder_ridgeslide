# -*- coding: utf-8 -*-
"""
Separable smoothing and gradient of the density surface (§4.6 of the plan).
Заострённое гауссово ядро Маха (без меркаторовского множителя — τ постоянна),
сепарабельное сглаживание и градиент для Slide.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np


def build_kernel(sigma_px, sharpness=1.5):
    """Заострённый гаусс Маха в пикселях (sharpness=0 → чистый гаусс).

    Внутри 1σ — линейный подъём к острому пику, дальше — гауссов хвост.
    Нормируется на сумму=1 (сохранение «массы» плотности).
    """
    sigma_px = float(sigma_px)
    if sigma_px <= 0:
        return np.array([1.0])
    add = float(sharpness) * sigma_px
    size = int(np.ceil(3.5 * sigma_px))
    k = np.empty(2 * size + 1, dtype=float)
    inv_sqrt_e = 1.0 / np.sqrt(np.e)
    for i in range(size + 1):
        if i < sigma_px:
            x = -add / sigma_px * i + (add + inv_sqrt_e)
        else:
            x = np.exp(-(i / sigma_px) ** 2)
        k[size - i] = x
        k[size + i] = x
    return k / k.sum()


def separable_smooth(values, kernel):
    """Сепарабельная свёртка 2D-массива 1D-ядром по обеим осям."""
    from scipy.ndimage import convolve1d
    out = convolve1d(np.asarray(values, dtype=float), kernel, axis=0,
                     mode='constant', cval=0.0)
    out = convolve1d(out, kernel, axis=1, mode='constant', cval=0.0)
    return out


def smooth_density(values, sigma_px, sharpness=1.5):
    """Сгладить поверхность плотности заострённым ядром."""
    kernel = build_kernel(sigma_px, sharpness=sharpness)
    if kernel.size == 1:
        return np.asarray(values, dtype=float).copy()
    return separable_smooth(values, kernel)


def gradient(values):
    """Градиент поверхности в пиксельных единицах.

    Returns:
        (gx, gy): производные по X (столбцы) и Y (строки). Соответствуют
        направлению возрастания плотности вдоль мировых осей X и Y.
    """
    values = np.asarray(values, dtype=float)
    gy, gx = np.gradient(values)  # np.gradient → (d/row, d/col) = (dY, dX)
    return gx, gy
