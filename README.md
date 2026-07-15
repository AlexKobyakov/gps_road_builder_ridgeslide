# GPS Road Builder

[![CI](https://github.com/AlexKobyakov/gps_road_builder/actions/workflows/ci.yml/badge.svg)](https://github.com/AlexKobyakov/gps_road_builder/actions/workflows/ci.yml)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
![QGIS 3.22+](https://img.shields.io/badge/QGIS-3.22%2B%20(3.x)-589632.svg)
![Version](https://img.shields.io/badge/version-1.0.0-informational.svg)
![Tests](https://img.shields.io/badge/tests-207%20offline-success.svg)

**A QGIS plugin that reconstructs a connected road/path network (a graph) from
raw GPS tracks — powered by RidgeSlide, our own density‑based method.**

Feed it millions of noisy GPS points from many vehicles; get back a clean,
weighted network of the roads or paths those vehicles actually used. It is not
tied to forestry: it works for **logging haul roads, logistics fleets, running
and cycling tracks, off‑road/enduro, agricultural machinery, vessels (AIS),
OpenStreetMap traces, and more** — anywhere many overlapping GPS traces reveal an
underlying network.

---

## What makes it different: RidgeSlide

**RidgeSlide** is our from‑scratch Python/NumPy/Numba reimplementation of the
density‑based road‑network method, reworked from Guo et al. (2020) and the
reference `paulmach/slide`, with our own corrections and additions. The idea:
roads are the **ridges** of a density surface built from all the GPS points;
RidgeSlide slides trajectories onto those ridges, then a centerline skeleton is
turned into a graph.

Why it matters:

- **Fast and scalable** — a Numba `@njit(parallel=True)` kernel processes tens of
  millions of points; a dependency‑free NumPy reference is always available.
- **Robust thresholding** — a percentile mode avoids the classic Otsu failure
  (cutting *above* the roads) on sparse, heterogeneous data.
- **Clean geometry** — hole‑filling, micro‑loop removal, Chaikin smoothing and a
  connectivity pass turn a jagged raster skeleton into a usable network.
- A separate **KDE mode** is available for very sparse fixes.

RidgeSlide — its concept, generalization, development and completion — is the
original work of **Alexander Kobyakov**.

See **[ALGORITHMS.md](ALGORITHMS.md)** for the full algorithm list and details.

---

## Features

- **Flexible ingest** — recursive folders of **CSV and XLSX**; or a **project
  vector layer** (points/lines); or a **GPX / KML / SHP** file — with automatic
  delimiter/datetime detection and mandatory deduplication. Vector inputs need no
  coordinate columns (the geometry provides them).
- **Preprocessing** — per‑device near‑duplicate thinning, speed/acceleration
  physical filter, optional REB / anti‑spoofing filter, gap segmentation.
- **Seamless working CRS** — a data‑centered Transverse Mercator removes the
  UTM‑zone‑seam problem; anti‑meridian safe.
- **Two methods** — **RidgeSlide** (default, dense to moderately sparse) and
  **KDE + buffer** (very sparse fixes, experimental).
- **Scenario presets** — one‑click starting points for forest roads, dense sport
  tracks (running/cycling), urban/logistics fleets, OSM traces and sparse
  fleet/AIS data; save and load your own as JSON.
- **Graph extraction** — Otsu / manual / **percentile** thresholding,
  skeletonization (scikit‑image, medial‑axis centerline, or a built‑in NumPy
  Zhang–Suen fallback), skeleton→graph (no `sknw`), Douglas–Peucker
  simplification, edge weighting and `(frequency, length)` artifact filtering
  with long‑road protection.
- **Quality & attributes** — road class by frequency, `reconstructed` flag,
  `n_devices` (unique devices per edge), Chaikin smoothing.
- **Connectivity** — bridge dangling ends, drop small components, keep the
  largest network; a dedicated **Post‑process** tab refines an existing graph
  without a full rebuild.
- **Area of interest** — clip input points by a polygon (file or project layer).
- **Scalable** — split‑and‑merge over overlapping tiles with boundary fixing.
- **Transparent** — the run log records every setting and per‑stage metric; a
  per‑run manifest (`gps_road_builder_runs.jsonl`) lets you diff runs while tuning.
- **Export** — GeoJSON, GraphML, Shapefile, GeoPackage.
- **On‑demand dependencies** — `numba`, `scikit‑image` etc. are installed only
  when you ask, from a dialog. No silent auto‑install. Interface in **RU and EN**.

---

## Requirements

- **QGIS 3.22+ — the whole 3.x branch** (Qt5), Windows or Linux. Tested up to
  **QGIS 3.44 “Solothurn”**. QGIS **4.x (Qt6)** needs separate work and is not
  supported yet.
- Uses libraries shipped with QGIS: `numpy`, `scipy`, `shapely`, `pyproj`,
  `pandas`.
- Optional accelerators, installable from the **Dependencies** tab:
  `numba` (fast RidgeSlide — strongly recommended), `scikit‑image`
  (skeletonization / medial axis), `pyarrow`, `scikit‑learn`.

## Installation

1. Build the plugin zip: `python scripts/build_plugin.py` →
   `dist/gps_road_builder.zip`.
2. In QGIS: **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Open it from the **Vector** menu or the toolbar (🛰️).
4. Open the **Dependencies** tab and install **numba** (RidgeSlide is much faster
   with it).

## Quick start

1. **Data** tab → choose the root folder with your CSV/XLSX exports → **Scan**.
   Optionally set an **Area of interest** polygon to drop points outside your zone.
2. Pick a **preset** that matches your data density, or tune parameters per tab.
3. On the **Density / Slide** tab set **Slide backend = Auto** (uses numba if
   installed — do not leave it on `numpy`, which is the slow reference).
4. Click **Build road graph** — it runs in the background; watch progress and the
   log.
5. The network is added to the project (line width ∝ traversal frequency). Review
   the **Overview** tab and, if needed, the **Post‑process** tab.
6. Export via the **Output** tab (GeoJSON / GraphML / SHP / GPKG).

**Full walkthrough: [USER_GUIDE.md](USER_GUIDE.md).**

## Tuning — and not giving up

A good network rarely comes out perfect on the **first (or second) try** — that is
normal. The result depends on your data density and a few parameters; expect to
iterate. The plugin is built for exactly this:

- **Read the log.** Each run logs its full settings and per‑stage metrics,
  including the binarization **threshold per tile**. Wildly varying thresholds are
  the usual reason a network comes out too sparse — switch to the **percentile**
  threshold.
- **Too sparse?** Lower the threshold percentile, use a finer cell size, or lower
  the min edge length. **Too noisy?** Raise the percentile / min length / min
  frequency, or enable spur and small‑component removal.
- **Too slow?** Make sure **numba** is selected; use a coarser cell and a larger
  resample step so sparse points don't explode into tens of millions.
- **Iterate cheaply.** Use the **cache folder** + "start from stage" to re‑tune
  later steps without re‑running the expensive early ones, and the
  **Post‑process** tab to refine a built graph without rebuilding.

See the troubleshooting section of the [user guide](USER_GUIDE.md).

---

## Development

```bash
pip install -r requirements-dev.txt      # pytest, flake8
pip install -r requirements-test.txt     # numpy, pandas, scipy, pyproj, openpyxl
pytest                                    # offline test suite (no QGIS needed)
flake8 .
```

The `core/` package is pure Python (no `qgis`/`PyQt` imports) and is fully
offline‑tested (176 tests); `gui/` and `tasks/` integrate with QGIS. CI runs the
tests on Linux and Windows for Python 3.9 and 3.12.

```
core/          pure algorithmic core (io, preprocess, density, slide, graph, splitmerge, pipeline)
gui/           QGIS dialog, tabs, dependency installer, layers/style, histograms
tasks/         QgsTask background wrappers
translations/  RU/EN interface strings
tests/         offline pytest suite
```

## License

The **plugin** is **GPLv3** — see [LICENSE](LICENSE).

The **RidgeSlide core** (`core/ridgeslide/`) is a self‑contained, QGIS‑agnostic
method released under the **MIT License** — see
[core/ridgeslide/LICENSE](core/ridgeslide/LICENSE) and
[NOTICE](core/ridgeslide/NOTICE) for its lineage (paulmach/slide, MIT, 2013 +
Guo et al. 2020 + original additions). MIT is GPL‑compatible, so the GPLv3
plugin bundles the MIT core. See [CITATION.cff](CITATION.cff) to cite this work.

## Author

Кобяков Александр Викторович (Alex Kobyakov), Lesburo · kobyakov@lesburo.ru ·
Telegram [@AKobyakov](https://t.me/AKobyakov)

**RidgeSlide** — its concept, generalization, development and completion — is the
original work of **Alexander Kobyakov** (Кобяков Александр Викторович). It builds
on the academic density method of Guo, Bardera, Fort & Silveira (2020), *A
scalable method to construct compact road networks from GPS trajectories* (IJGIS),
and the Slide method by Paul Mach (Strava Labs), which he reimagined,
reimplemented in Python/NumPy/Numba, corrected, generalized and brought to
completion as a distinct method.
# gps_road_builder_ridgeslide
