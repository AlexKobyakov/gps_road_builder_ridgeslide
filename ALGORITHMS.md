# Algorithms in GPS Road Builder

This document lists the algorithms used across the pipeline: what each does, which
library provides it, and where it lives in the code. The star of the show —
**RidgeSlide** — is described first.

---

## ⭐ RidgeSlide — our density‑based network reconstruction

**What it is.** RidgeSlide is our own reimplementation, in pure Python /
NumPy / Numba, of the density‑based road‑network method. Roads are treated as the
**ridges** of a density surface built from all GPS points; trajectories are
iteratively "slid" onto those ridges (a mean‑shift‑like compaction), and the
compacted surface is turned into a centerline graph.

**Origins and what we changed.** It started from Guo, Bardera, Fort & Silveira
(2020), *A scalable method to construct compact road networks from GPS
trajectories* (IJGIS), and was cross‑checked line‑by‑line against the reference Go
implementation `paulmach/slide` (Strava Labs). During that review we found the
paper and the code disagree in several places; we followed the code and fixed the
math accordingly. Our version adds substantially on top:

- **Faithful, corrected kernel** — distance component with the ½ factor;
  angle component as the bisector of normalized arms with a `cbrt(cos)+1` term
  (not the paper's formula); full‑correction momentum; endpoint motion by
  projection onto the neighbouring segment; convergence by mean density with
  exponential smoothing and min/max loop bounds.
- **Two interchangeable backends** — a NumPy reference (correctness oracle) and a
  Numba `@njit(parallel=True)` kernel parallel over tracks (`prange`), verified
  equivalent.
- **Our additions beyond Guo/Slide** — a hybrid **KDE** mode for very sparse
  data; a **percentile threshold** that avoids Otsu's failure on skewed surfaces;
  mask hole‑filling and micro‑loop removal for clean centerlines; a graph
  post‑processing stage (degree‑2 merge, spur/component cleanup, gap bridging,
  Chaikin smoothing); device‑aware edge attributes.

**Where.** `core/ridgeslide/kernel.py` (the kernel + backends),
`core/ridgeslide/refine.py` (density + compaction), with a small public API
façade `core/ridgeslide/api.py` (`RidgeSlide` / `RidgeSlideConfig` /
`RidgeSlideResult`); orchestrated by `core/pipeline.py`.

**Standalone core.** `core/ridgeslide/` is QGIS‑agnostic (no `qgis`/`PyQt`
imports — enforced by a guard test) and **MIT‑licensed** (see
`core/ridgeslide/LICENSE` and `NOTICE`), so it can be reused as a library; the
surrounding plugin is GPLv3.

**Why the name.** Roads = **ridges** of the density surface; the method **slides**
trajectories onto them.

**Authorship.** RidgeSlide — its concept, generalization, development and
completion — is the original work of **Alexander Kobyakov** (Кобяков Александр
Викторович). Building on the academic density method (Guo et al. 2020) and the
reference Slide method, he devised, generalized, engineered and finished this
distinct Python/NumPy/Numba implementation with its own corrections and additions.

---

## Supporting algorithms

| Stage | Algorithm | Purpose | Library | Where |
|---|---|---|---|---|
| Ingest | Delimiter / datetime sniffing | Auto‑detect CSV format | pandas + custom | `core/io/csv_reader.py`, `schema.py` |
| Clean | Haversine + physical filter | Drop impossible speeds/accelerations | NumPy (custom) | `core/preprocess/clean.py` |
| Clean | REB / anti‑spoofing | Remove teleports and A→B→C spikes | NumPy (custom) | `core/preprocess/clean.py` |
| Thin | Greedy per‑device thinning | Drop near‑duplicate fixes of one device | Numba / NumPy (custom) | `core/preprocess/thin.py` |
| Segment | Gap segmentation | Split tracks on time/distance gaps | pandas (custom) | `core/preprocess/segmentize.py` |
| CRS | Data‑centered Transverse Mercator | Seam‑free metric working frame | pyproj | `core/density/projection.py` |
| AOI | Point‑in‑polygon (ray casting, even‑odd) | Clip points to an area of interest | NumPy (custom) | `core/preprocess/aoi.py` |
| Density | Binning + sharpened Gaussian | Build & smooth the density surface | NumPy / SciPy | `core/density/{grid,blur}.py` |
| Density | **RidgeSlide** compaction | Slide trajectories onto ridges | NumPy / Numba (custom) | `core/slide/*` |
| Density | KDE | Density for very sparse data | SciPy | `core/density/kde.py` |
| Threshold | Otsu | Auto threshold (dense/bimodal) | NumPy (custom) | `core/graph/binarize.py` |
| Threshold | **Percentile** | Robust threshold for sparse/skewed | NumPy (custom) | `core/graph/binarize.py` |
| Mask | Dilation / hole‑fill | Bridge gaps, kill skeleton loops | SciPy / scikit‑image | `core/graph/binarize.py` |
| Skeleton | scikit‑image skeletonize / **medial axis** | 1‑px centerline | scikit‑image | `core/graph/skeletonize.py` |
| Skeleton | Zhang–Suen thinning | Dependency‑free fallback | NumPy (custom) | `core/graph/skeletonize.py` |
| Graph | Skeleton → graph | Nodes/edges from skeleton (no `sknw`) | NumPy (custom) | `core/graph/to_graph.py` |
| Graph | Douglas–Peucker (RDP) | Simplify edge geometry | NumPy (custom) | `core/graph/simplify.py` |
| Graph | cKDTree edge weighting | Frequency & `n_devices` per edge | SciPy | `core/graph/edge_weights.py` |
| Cleanup | Degree‑2 merge, spur/loop/component removal | De‑fragment | NumPy / SciPy (custom) | `core/graph/{postprocess,connect,postops}.py` |
| Cleanup | Gap bridging — end‑to‑end, node‑to‑edge snapping (splits the edge at a T‑gap), directional bridging of facing dead‑ends, and component stitching (Kruskal over k‑NN) | Make the network connected | SciPy cKDTree (custom) | `core/graph/connect.py` |
| Cleanup | Chaikin corner‑cutting | Smooth stair‑steps | NumPy (custom) | `core/graph/smoothing.py` |
| Attributes | Frequency quantiles | `road_class`, `reconstructed` | NumPy (custom) | `core/graph/attributes.py` |
| Scale | Split‑and‑merge over tiles | Bounded memory on huge inputs | NumPy / SciPy (custom) | `core/splitmerge/*` |

Optional accelerators (`numba`, `scikit‑image`, `pyarrow`, `scikit‑learn`) are
installed on demand from the Dependencies tab; every path has a dependency‑free
fallback so the plugin runs on a bare QGIS install.
