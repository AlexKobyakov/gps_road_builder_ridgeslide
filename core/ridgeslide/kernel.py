# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
RidgeSlide kernel (§4.2.1 of the plan). Part of the MIT-licensed RidgeSlide core
(see LICENSE / NOTICE in this folder).
Ядро Slide, сверенное с эталонной Go-реализацией (paulmach/slide) и Guo 2020:
  - distance-компонент с множителем ½ (исправление №1 Guo);
  - angle-компонент = бисектриса нормированных «рук», множитель cbrt(cos)+1;
  - momentum = полная коррекция прошлой итерации;
  - движение концов проекцией на соседний сегмент (исправление №2 Guo);
  - сходимость: среднее плотности + эксп. сглаживание (0.2) + MinLoops/MaxLoops.

Два бэкенда с идентичной семантикой:
  - `slide_all_numpy` — эталон корректности (векторизация по точкам трека);
  - `slide_all_numba` — near-C, параллельно по трекам (prange), при наличии numba.
Публичная `slide_all` выбирает бэкенд.

Раскладка данных (CSR): pts (N,2) float64 + offsets (M+1,) int; трек t занимает
pts[offsets[t]:offsets[t+1]]. Поля dens/gx/gy — read-only во время прохода
(пересчитываются после), поэтому обработка треков независима и детерминирована.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import numpy as np

DEFAULT_WEIGHTS = (0.5, 0.2, 0.1, 0.7)   # ω1..ω4 (Guo, плотностная поверхность)
DEFAULT_U_THR = 5e-4
DEFAULT_MIN_LOOPS = 100
DEFAULT_MAX_LOOPS = 4000


# ---------------------------------------------------------------------------
# NumPy-эталон
# ---------------------------------------------------------------------------

def _bilerp_np(F, px, py):
    """Билинейная интерполяция поля F (H,W) в дробных пикселях (векторно)."""
    H, W = F.shape
    x0 = np.floor(px).astype(np.intp)
    y0 = np.floor(py).astype(np.intp)
    valid = (x0 >= 0) & (y0 >= 0) & (x0 < W - 1) & (y0 < H - 1)
    fx = px - x0
    fy = py - y0
    x0c = np.clip(x0, 0, W - 2)
    y0c = np.clip(y0, 0, H - 2)
    x1c = x0c + 1
    y1c = y0c + 1
    v = (F[y0c, x0c] * (1 - fx) * (1 - fy)
         + F[y0c, x1c] * fx * (1 - fy)
         + F[y1c, x0c] * (1 - fx) * fy
         + F[y1c, x1c] * fx * fy)
    return np.where(valid, v, 0.0)


def _project_end_np(P, e, i1, i2):
    """Ортогональная проекция точки P[e] на прямую через P[i1], P[i2]."""
    b = P[i1]
    d = P[i2] - b
    dd = float(d @ d)
    if dd > 1e-12:
        t = float((P[e] - b) @ d) / dd
        P[e] = b + t * d


def _slide_one_np(P, dens, gx, gy, ox, oy, inv_cell,
                  w1, w2, w3, w4, u_thr, min_iter, max_iter, depth_reduce):
    """Обработать один трек (мутирует P на месте)."""
    n = len(P)
    if n < 3:
        return
    mv = np.zeros((n, 2))
    smoothed = 0.0
    for it in range(max_iter):
        pm = P[0:n - 2]
        pc = P[1:n - 1]
        pp = P[2:n]
        u = pp - pm
        v = pc - pm
        uu = (u * u).sum(axis=1)
        uv = (u * v).sum(axis=1)

        # distance component (½ — исправление №1)
        safe_uu = np.where(uu > 1e-12, uu, 1.0)
        t = (uv / safe_uu)[:, None]
        center = pm + u * t
        dv = 0.5 * ((pm - center) + (pp - center))
        dv[uu <= 1e-12] = 0.0

        # angle component (бисектриса нормированных «рук»)
        n1 = pm - pc
        n2 = pp - pc
        l1 = np.hypot(n1[:, 0], n1[:, 1])
        l2 = np.hypot(n2[:, 0], n2[:, 1])
        good = (l1 > 1e-12) & (l2 > 1e-12)
        sl1 = np.where(l1 > 1e-12, l1, 1.0)[:, None]
        sl2 = np.where(l2 > 1e-12, l2, 1.0)[:, None]
        n1h = n1 / sl1
        n2h = n2 / sl2
        cos = (n1h * n2h).sum(axis=1)
        factor = np.cbrt(cos) + 1.0
        bis = n1h + n2h
        nb = np.hypot(bis[:, 0], bis[:, 1])
        mn = np.minimum(l1, l2)
        ok = good & (nb > 1e-12) & (factor != 0.0)
        av = np.zeros((n - 2, 2))
        safe_nb = np.where(nb > 1e-12, nb, 1.0)[:, None]
        av_full = bis / safe_nb * (mn * factor)[:, None]
        av[ok] = av_full[ok]

        # surface component (градиент плотности в точке)
        px = (pc[:, 0] - ox) * inv_cell
        py = (pc[:, 1] - oy) * inv_cell
        sv = np.column_stack([_bilerp_np(gx, px, py), _bilerp_np(gy, px, py)])

        cr = w1 * sv + w2 * dv + w3 * av + w4 * mv[1:n - 1]
        if depth_reduce:
            val = _bilerp_np(dens, px, py)
            cr = cr * np.sqrt(np.clip(1.0 - val, 0.0, None))[:, None]

        new_interior = pc + cr
        mv[1:n - 1] = cr
        P[1:n - 1] = new_interior

        # концы (исправление №2)
        _project_end_np(P, 0, 1, 2)
        _project_end_np(P, n - 1, n - 2, n - 3)

        # сходимость: среднее плотности + эксп. сглаживание
        apx = (P[:, 0] - ox) * inv_cell
        apy = (P[:, 1] - oy) * inv_cell
        s = float(_bilerp_np(dens, apx, apy).mean())
        prev = smoothed
        smoothed = 0.2 * prev + 0.8 * s
        if it >= min_iter and abs(smoothed - prev) < u_thr:
            break


def slide_all_numpy(pts, offsets, dens, gx, gy, ox, oy, inv_cell,
                    w1, w2, w3, w4, u_thr, min_iter, max_iter, depth_reduce):
    """Прогнать Slide по всем трекам (эталон; мутирует pts)."""
    for t in range(len(offsets) - 1):
        a, b = int(offsets[t]), int(offsets[t + 1])
        _slide_one_np(pts[a:b], dens, gx, gy, ox, oy, inv_cell,
                      w1, w2, w3, w4, u_thr, min_iter, max_iter, depth_reduce)


# ---------------------------------------------------------------------------
# Numba-бэкенд (опционально)
# ---------------------------------------------------------------------------

try:
    from numba import njit, prange
    HAVE_NUMBA = True
except Exception:  # pragma: no cover - numba опциональна
    HAVE_NUMBA = False


if HAVE_NUMBA:
    import math

    @njit(cache=True, fastmath=True, inline='always')
    def _bilerp_nb(F, x, y):
        x0 = int(math.floor(x))
        y0 = int(math.floor(y))
        if x0 < 0 or y0 < 0 or x0 >= F.shape[1] - 1 or y0 >= F.shape[0] - 1:
            return 0.0
        fx = x - x0
        fy = y - y0
        return (F[y0, x0] * (1 - fx) * (1 - fy)
                + F[y0, x0 + 1] * fx * (1 - fy)
                + F[y0 + 1, x0] * (1 - fx) * fy
                + F[y0 + 1, x0 + 1] * fx * fy)

    @njit(cache=True, fastmath=True)
    def _project_end_nb(pts, e, i1, i2):
        bx = pts[i1, 0]
        by = pts[i1, 1]
        dx = pts[i2, 0] - bx
        dy = pts[i2, 1] - by
        dd = dx * dx + dy * dy
        if dd > 1e-12:
            t = ((pts[e, 0] - bx) * dx + (pts[e, 1] - by) * dy) / dd
            pts[e, 0] = bx + t * dx
            pts[e, 1] = by + t * dy

    @njit(cache=True, fastmath=True)
    def _slide_one_nb(pts, a, b, dens, gx, gy, ox, oy, inv_cell,
                      w1, w2, w3, w4, u_thr, min_iter, max_iter, depth_reduce):
        n = b - a
        if n < 3:
            return
        mv = np.zeros((n, 2))
        newp = np.zeros((n, 2))
        smoothed = 0.0
        for it in range(max_iter):
            for k in range(1, n - 1):
                i = a + k
                pmx = pts[i - 1, 0]
                pmy = pts[i - 1, 1]
                pcx = pts[i, 0]
                pcy = pts[i, 1]
                ppx = pts[i + 1, 0]
                ppy = pts[i + 1, 1]
                ux = ppx - pmx
                uy = ppy - pmy
                vx = pcx - pmx
                vy = pcy - pmy
                uu = ux * ux + uy * uy
                uv = ux * vx + uy * vy
                if uu > 1e-12:
                    tt = uv / uu
                    cx = pmx + ux * tt
                    cy = pmy + uy * tt
                    dvx = 0.5 * ((pmx - cx) + (ppx - cx))
                    dvy = 0.5 * ((pmy - cy) + (ppy - cy))
                else:
                    dvx = 0.0
                    dvy = 0.0
                n1x = pmx - pcx
                n1y = pmy - pcy
                n2x = ppx - pcx
                n2y = ppy - pcy
                l1 = math.sqrt(n1x * n1x + n1y * n1y)
                l2 = math.sqrt(n2x * n2x + n2y * n2y)
                if l1 < 1e-12 or l2 < 1e-12:
                    avx = 0.0
                    avy = 0.0
                else:
                    n1x /= l1
                    n1y /= l1
                    n2x /= l2
                    n2y /= l2
                    cos = n1x * n2x + n1y * n2y
                    factor = math.copysign(abs(cos) ** (1.0 / 3.0), cos) + 1.0
                    bx = n1x + n2x
                    by = n1y + n2y
                    nb = math.sqrt(bx * bx + by * by)
                    if nb < 1e-12 or factor == 0.0:
                        avx = 0.0
                        avy = 0.0
                    else:
                        mn = l1 if l1 < l2 else l2
                        avx = bx / nb * mn * factor
                        avy = by / nb * mn * factor
                pxp = (pcx - ox) * inv_cell
                pyp = (pcy - oy) * inv_cell
                svx = _bilerp_nb(gx, pxp, pyp)
                svy = _bilerp_nb(gy, pxp, pyp)
                crx = w1 * svx + w2 * dvx + w3 * avx + w4 * mv[k, 0]
                cry = w1 * svy + w2 * dvy + w3 * avy + w4 * mv[k, 1]
                if depth_reduce:
                    val = _bilerp_nb(dens, pxp, pyp)
                    r = math.sqrt(max(0.0, 1.0 - val))
                    crx *= r
                    cry *= r
                newp[k, 0] = pcx + crx
                newp[k, 1] = pcy + cry
                mv[k, 0] = crx
                mv[k, 1] = cry
            for k in range(1, n - 1):
                pts[a + k, 0] = newp[k, 0]
                pts[a + k, 1] = newp[k, 1]
            _project_end_nb(pts, a, a + 1, a + 2)
            _project_end_nb(pts, b - 1, b - 2, b - 3)
            s = 0.0
            for k in range(n):
                i = a + k
                s += _bilerp_nb(dens, (pts[i, 0] - ox) * inv_cell,
                                (pts[i, 1] - oy) * inv_cell)
            s /= n
            prev = smoothed
            smoothed = 0.2 * prev + 0.8 * s
            if it >= min_iter and abs(smoothed - prev) < u_thr:
                break

    @njit(parallel=True, cache=True, fastmath=True)
    def slide_all_numba(pts, offsets, dens, gx, gy, ox, oy, inv_cell,
                        w1, w2, w3, w4, u_thr, min_iter, max_iter, depth_reduce):
        m = offsets.shape[0] - 1
        for t in prange(m):
            _slide_one_nb(pts, offsets[t], offsets[t + 1], dens, gx, gy,
                          ox, oy, inv_cell, w1, w2, w3, w4,
                          u_thr, min_iter, max_iter, depth_reduce)


# ---------------------------------------------------------------------------
# Публичный диспетчер
# ---------------------------------------------------------------------------

def slide_all(pts, offsets, dens, gx, gy, ox, oy, inv_cell,
              weights=DEFAULT_WEIGHTS, u_thr=DEFAULT_U_THR,
              min_iter=DEFAULT_MIN_LOOPS, max_iter=DEFAULT_MAX_LOOPS,
              depth_reduce=False, backend='auto'):
    """Прогнать Slide по всем трекам (мутирует pts на месте).

    Args:
        pts: (N, 2) float64 — все точки треков (CSR).
        offsets: (M+1,) int — границы треков.
        dens, gx, gy: (H, W) float64 — плотность и её градиент (read-only).
        ox, oy, inv_cell: параметры сетки (мир → пиксель).
        weights: (ω1, ω2, ω3, ω4).
        backend: 'auto' | 'numpy' | 'numba'.
    """
    pts = np.ascontiguousarray(pts, dtype=np.float64)
    offsets = np.ascontiguousarray(offsets, dtype=np.int64)
    dens = np.ascontiguousarray(dens, dtype=np.float64)
    gx = np.ascontiguousarray(gx, dtype=np.float64)
    gy = np.ascontiguousarray(gy, dtype=np.float64)
    w1, w2, w3, w4 = (float(w) for w in weights)
    di = 1 if depth_reduce else 0

    use_numba = (backend == 'numba') or (backend == 'auto' and HAVE_NUMBA)
    if backend == 'numba' and not HAVE_NUMBA:
        raise RuntimeError('numba backend requested but numba is not available')

    if use_numba:
        slide_all_numba(pts, offsets, dens, gx, gy, float(ox), float(oy),
                        float(inv_cell), w1, w2, w3, w4, float(u_thr),
                        int(min_iter), int(max_iter), di)
    else:
        slide_all_numpy(pts, offsets, dens, gx, gy, float(ox), float(oy),
                        float(inv_cell), w1, w2, w3, w4, float(u_thr),
                        int(min_iter), int(max_iter), di)
    return pts
