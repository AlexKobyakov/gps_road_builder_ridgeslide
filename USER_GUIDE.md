# GPS Road Builder — User Guide

A practical guide to building a road/path network from GPS tracks with GPS Road
Builder. For the algorithms behind it see [ALGORITHMS.md](ALGORITHMS.md); for an
overview see [README.md](README.md).

---

## 1. Install

1. Build the zip: `python scripts/build_plugin.py` → `dist/gps_road_builder.zip`.
2. QGIS → **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Open the **Dependencies** tab in the plugin and install **numba** (RidgeSlide
   is many times faster with it) and **scikit‑image** (skeletonization / medial
   axis). Nothing is installed without your click.

## 2. Input data format

The plugin accepts three input sources (Data tab → **Input source**):

1. **CSV / XLSX files** — a folder (scanned recursively; a common layout is one
   folder per month) or individual files. Column requirements are below.
2. **Project vector layer** — a point or line layer already loaded in QGIS.
3. **GPX / KML / SHP file** — a GPS/track/vector file.

For **vector layers and files** there are no coordinate‑column requirements — the
geometry provides the coordinates. `device`/`time` are auto‑detected from field
names (same aliases as below) when present, and synthesized otherwise; for line
layers each line is treated as one track. GPX files use the `track_points`
sub‑layer (with its per‑point time).

For **CSV/XLSX**, the required columns are (case‑insensitive; common aliases are
auto‑detected):

| Role | Meaning | Accepted names |
|---|---|---|
| `device` | vehicle / unit id | device_id, id, imei, unit, unit_id, object, object_id, машина, устройство |
| `time` | timestamp | navigation_dttm, time, datetime, timestamp, dttm, date_time, dt, время, дата |
| `lat` | latitude, degrees (WGS84) | lat, latitude, y, широта |
| `lon` | longitude, degrees (WGS84) | lon, lng, long, longitude, x, долгота |

- **Delimiter** (CSV) is auto‑detected: `;`, `,`, tab, `|`, `/`.
- **Datetime** is auto‑detected (ISO `2025-01-31 14:00:00` and day‑first dotted
  `31.01.2025 14:00`).
- **Coordinates** are decimal degrees, WGS84.
- No speed/course columns are needed — speed is computed from Δdistance / Δtime.

There are no optional columns yet; extra columns are ignored.

## 3. The tabs (workflow)

- **Data** — pick the folder / files, **Scan** to list them, optionally set an
  **Area of interest** polygon (from a file or a project layer) to clip points
  outside your zone before processing.
- **Preprocessing** — near‑duplicate thinning (per device), speed/acceleration
  filter, optional REB/anti‑spoofing filter, gap segmentation, resample step.
- **Density / Slide** — method (**RidgeSlide** or KDE), backend, skeletonizer,
  cell size τ, smoothing σ.
- **Graph** — threshold mode (Otsu / manual / **percentile**), Douglas–Peucker,
  min edge frequency/length, spur / hole / micro‑loop cleanup, Chaikin smoothing.
- **Scale** — tiling for large data (auto / off / forced), max points per tile.
- **Post‑process** — refine a built graph or a project line layer without a full
  rebuild: bridge gaps, **break edges at crossings** (turn a visual X into a real
  junction), **consolidate junction clusters**, drop small components, keep the
  largest network.
- **Output** — CRS, layer name, export format/path, and the **cache folder** +
  "start from / stop after stage" for checkpointed runs.
- **Dependencies** — install optional accelerators; see which are active.

## 4. Choosing a method and preset

- **RidgeSlide** (default) suits dense to moderately sparse tracks and builds a
  connected network by concentrating density onto road ridges. **Recommended for
  most data**, including sparse fleet data — with the right preset. RidgeSlide was
  conceived, generalized, developed and completed by **Alexander Kobyakov** (see
  [ALGORITHMS.md](ALGORITHMS.md)).
- **KDE + buffer** is a separate mode for very sparse fixes; it is experimental
  (its per‑tile Otsu threshold is fragile — use the percentile threshold).

Start from a **preset** close to your data, then tune. Always confirm
**Slide backend = Auto/numba** on the Density tab — `numpy` is the slow reference.

**Built-in presets** (starting points — expect to tune, especially the
threshold):

| Preset | For | Notes |
|---|---|---|
| Mixed (default) | Mixed forest roads | Otsu threshold, medium cell |
| Haul roads | Main logging roads | Higher min frequency, coarser cell |
| Spurs / skid trails | Faint spurs / skid trails | Fine cell, keeps rare edges |
| Dense tracks (running / cycling) | Dense sport/foot tracks (fix 1–5 s) | Fine cell, short resample, Otsu |
| Urban vehicles / logistics | City driving / delivery fleets | Higher min frequency, percentile |
| OSM traces (heterogeneous) | Mixed-quality public GPS traces | Percentile threshold for robustness |
| Sparse / RidgeSlide (recommended) | Sparse fleet fixes (15 min / 5 km) | numba, coarse resample, percentile |
| Sparse / RidgeSlide (accurate) | Sparse data, geometry close to reference | Finer cell/resample, less smoothing (slower; numba) |
| Sparse vessels / AIS | Very sparse ship reports | Coarse cell/resample, wide gaps |
| Sparse / KDE (experimental) | Very sparse fixes, KDE mode | Percentile, hole-fill, loop cleanup |

The scenario presets (running/cycling, urban/logistics, OSM, AIS) encode
**assumptions about the data**, not tuned answers — treat their numbers as a
starting point and adjust the cell size, resample step and threshold to your
own tracks.

## 5. Tuning — read the log

Every run writes a detailed log to
`<QGIS profile>/gps_road_builder/gps_road_builder.log` and appends a compact
one‑line summary per run to `gps_road_builder_runs.jsonl` (great for diffing
runs). The log records:

- the full resolved **settings** of the run and the **resolved backend**;
- per‑stage metrics and durations, including the **binarization threshold per
  tile** and a min/median/max summary;
- the resample point‑count inflation, and the cleanup edge/node counts.

**Diagnosing common outcomes:**

| Symptom | Likely cause | Fix |
|---|---|---|
| Network too **sparse** | per‑tile Otsu thresholds vary wildly (hot‑spot tiles blow out) | use **percentile** threshold; lower the percentile for more roads |
| Network too **noisy** | threshold too low / short artifacts | raise percentile, min length, min frequency; enable spur & small‑component removal |
| **Stair‑steps / crossings** | raster skeleton artifacts | increase Chaikin smoothing; enable hole‑fill and micro‑loop removal; try the medial‑axis skeletonizer |
| **Very slow / stuck** | numpy backend, or resample exploded the point count | select **numba**; use a coarser cell and larger resample step |
| **Gaps** in the network | roads not bridged | raise the "bridge gaps" radius on the Post‑process tab — it now joins dead‑ends both end‑to‑end and to the nearest point on a neighbouring edge (T‑gaps) |

**It is normal to iterate.** Use the **cache folder** + "start from stage" to
re‑tune later steps without re‑running read/clean, and the **Post‑process** tab to
refine a built graph without rebuilding.

## 6. Output & attributes

The result layer (EPSG:4326, LineString) carries per‑edge attributes:

- `frequency` — number of track passes (line width scales with it);
- `length` — meters;
- `road_class` — main / improved / ordinary / winter (by frequency quantiles);
- `reconstructed` — 1 if the segment was inferred (no track coverage);
- `n_devices` — number of unique devices near the edge (fresh runs only).

Export from the **Output** tab to GeoJSON, GraphML, Shapefile or GeoPackage.

## 7. Troubleshooting

- **"Slide runs on numpy" warning / very slow** — set Slide backend to numba
  (install it on the Dependencies tab first).
- **"Density raster too large for a tile"** — increase the cell size τ or reduce
  "max points per tile".
- **"Resampling produced N points"** in the log with a huge ratio — increase the
  resample step and/or the distance gap so sparse points don't inflate.
- **No log file?** It is in the QGIS **profile** folder, not the plugin folder:
  `<profile>/gps_road_builder/gps_road_builder.log`.
- **Result empty** — check the AOI polygon actually covers your data, and that the
  speed filter (`v_max`) is not too aggressive for sparse fixes.
