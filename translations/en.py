# -*- coding: utf-8 -*-
"""
English translations for GPS Road Builder (fallback language).

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

translations = {
    # --- General ---
    'window_title': 'GPS Road Builder (RidgeSlide)',
    'plugin_description': 'Reconstruct a road/path network graph from raw GPS '
                          'tracks (forestry, logistics, sports, OSM, ...) with '
                          'the RidgeSlide method.',
    'info': 'Information',
    'error': 'Error',
    'warning': 'Warning',
    'close': 'Close',
    'cancel': 'Cancel',
    'ok': 'OK',
    'details': 'Details',
    'coming_soon': 'Coming soon',
    'phase0_notice': 'This step is part of the processing pipeline and will be '
                     'implemented in the next development phases. Phase 0 '
                     'delivers the plugin skeleton and UI chassis.',

    # --- Header ---
    'header_support': 'Support',
    'header_about_author': 'About',
    'support_tip': 'Support the development of this plugin!',
    'author_tip': 'Information about the plugin author',

    # --- Tabs ---
    'tab_data': 'Data',
    'tab_preprocess': 'Preprocess',
    'tab_density': 'Density / RidgeSlide',
    'tab_graph': 'Graph',
    'tab_scale': 'Scale',
    'tab_postprocess': 'Post-process',
    'tab_output': 'Output',
    'tab_deps': 'Dependencies',

    # --- Control buttons ---
    'build_graph': 'Build road graph',
    'test_run': 'Test run (area)',
    'building': 'Building...',
    'clear_logs': 'Clear log',

    # --- Results / progress ---
    'progress': 'Progress',
    'logs': 'Log',
    'results': 'Results',
    'col_stage': 'Stage',
    'col_status': 'Status',
    'col_message': 'Message',
    'log_ready': 'GPS Road Builder is ready. Choose data and parameters, then '
                 'build the road graph.',

    # --- Dependencies tab ---
    'deps_intro': 'GPS Road Builder works on libraries already shipped with QGIS '
                  '(numpy, scipy, shapely, pyproj, pandas). The libraries below '
                  'are optional accelerators — install them here when needed. '
                  'Nothing is installed without your explicit action.',
    'deps_col_package': 'Library',
    'deps_col_purpose': 'Purpose',
    'deps_col_status': 'Status',
    'deps_status_installed': 'installed',
    'deps_status_missing': 'not installed',
    'deps_install_method': 'Install method:',
    'deps_method_auto': 'Auto',
    'deps_method_pip': 'pip → plugin folder',
    'deps_method_wheels': 'Prebuilt wheels (mirror)',
    'deps_method_folder': 'From local folder',
    'deps_install_selected': 'Install selected',
    'deps_recheck': 'Re-check',
    'deps_installing': 'Installing {0}...',
    'deps_install_done': 'Installed: {0}',
    'deps_install_failed': 'Installation failed: {0}',
    'deps_pip_unavailable': 'pip is not available in the QGIS Python; use '
                            '"Prebuilt wheels" or "From local folder".',
    'deps_choose_folder': 'Choose folder with wheels (*.whl)',
    'deps_purpose_numba': 'Fast RidgeSlide core (JIT, parallel)',
    'deps_purpose_skimage': 'Skeletonization of the density mask',
    'deps_purpose_pyarrow': 'Faster CSV reading',
    'deps_purpose_sklearn': 'Optional DBSCAN pre-clustering',
    'deps_optional': 'optional',

    # --- Install progress dialog ---
    'installing': 'Installing dependencies...',
    'downloading': 'Downloading...',
    'extracting': 'Extracting...',

    # --- Phase 4: tabs, presets, build ---
    'preset_label': 'Preset:',
    'preset_apply': 'Apply',
    'preset_save': 'Save',
    'preset_load': 'Load',
    'preset_applied': 'Preset applied',
    'preset_saved': 'Preset saved',
    'preset_loaded': 'Preset loaded',
    'cache_group': 'Intermediate results (checkpoints)',
    'cache_dir': 'Cache folder',
    'cache_start': 'Start from stage',
    'cache_stop': 'Stop after stage',
    'stage_none': '—',
    'stage_points': 'Cleaned points',
    'stage_tracks': 'Projected tracks',
    'tip_cache': 'Folder to save/load intermediate results, so you can re-tune '
                 'without re-running the whole pipeline.',
    'stopped_after': 'Stopped after stage',
    'preset_mixed': 'Mixed (default)',
    'preset_highway': 'Haul roads',
    'preset_spurs': 'Spurs / skid trails',
    'preset_dense_tracks': 'Dense tracks (running / cycling)',
    'preset_urban_logistics': 'Urban vehicles / logistics',
    'preset_osm_traces': 'OSM traces (heterogeneous)',
    'preset_sparse_slide': 'Sparse / RidgeSlide (recommended)',
    'preset_sparse_slide_accurate': 'Sparse / RidgeSlide (accurate)',
    'preset_sparse_ais': 'Sparse vessels / AIS',
    'preset_fgis_kde': 'Sparse / KDE (experimental)',
    'data_group': 'Input data',
    'data_source': 'Input source',
    'src_files': 'CSV/XLSX files (folder)',
    'src_layer': 'Project layer (points/lines)',
    'src_vfile': 'GPX / KML / SHP file',
    'data_layer_hint': 'Points/lines from the project. Coordinates come from the '
                       'geometry; device/time from fields (auto) or synthesized.',
    'data_folder': 'Folder with CSV/XLSX (recursive)',
    'data_browse': 'Browse folder',
    'data_scan': 'Scan',
    'data_load_hint': 'Pick a root folder (months inside) or individual files.',
    'data_season_split': 'Split by seasons',
    'data_files_found': 'Files found: {0}',
    'pp_group': 'Preprocessing',
    'pp_mindist': 'Thin near points, m',
    'pp_vmax': 'Max speed, km/h',
    'pp_amax': 'Max acceleration, m/s²',
    'pp_gap_dt': 'Time gap, min',
    'pp_gap_ds': 'Distance gap, m',
    'pp_resample': 'Resample step K, m',
    'pp_reb': 'REB / anti-spoofing filter',
    'method_group': 'Method & backends',
    'method_label': 'Method',
    'method_slide': 'Density + RidgeSlide (dense tracks)',
    'method_kde': 'KDE + buffer (sparse tracks)',
    'ds_slide_backend': 'RidgeSlide backend',
    'ds_skel_backend': 'Skeletonizer',
    'backend_auto': 'Auto',
    'backend_numba': 'numba (fast)',
    'backend_numpy': 'numpy (slow, reference)',
    'skel_skimage': 'scikit-image',
    'skel_medial': 'Medial axis (centerline)',
    'skel_zhang': 'Zhang–Suen (built-in)',
    'kde_radius': 'KDE radius, m',
    'kde_buffer': 'Gap buffer, m',
    'tip_method': 'RidgeSlide suits dense trajectories. KDE suits sparse fixes '
                  '(every 15 min / 5 km): no resampling, gaps '
                  'bridged by a buffer.',
    'ds_group': 'Density & RidgeSlide',
    'ds_cell': 'Cell size τ, m',
    'ds_sigma1': 'Smoothing σ1, px',
    'ds_sigma2': 'Smoothing σ2, px',
    'ds_sharpness': 'Kernel sharpness',
    'ds_advanced': 'Advanced',
    'ds_min_loops': 'RidgeSlide min loops',
    'ds_max_loops': 'RidgeSlide max loops',
    'gr_group': 'Graph',
    'gr_eps_mode': 'Threshold ε',
    'gr_eps_auto': 'Auto (Otsu)',
    'gr_eps_manual': 'Manual',
    'gr_eps_adaptive': 'Adaptive',
    'gr_eps_percentile': 'Percentile (for sparse)',
    'gr_eps_value': 'ε value',
    'gr_eps_pct_value': 'Threshold percentile, %',
    'gr_dp': 'Douglas–Peucker, m',
    'gr_fmin': 'Min edge frequency f',
    'gr_lmin': 'Min edge length l, m',
    'gr_spur': 'Remove dangling spurs shorter than, m',
    'gr_fill_holes': 'Fill mask holes, m',
    'gr_loop_min': 'Remove micro-loops shorter than, m',
    'gr_smooth': 'Smoothing (Chaikin), iterations',
    'gr_protect': 'Protect long rare roads',
    'sc_group': 'Scale (split-and-merge)',
    'sc_mode': 'Tiling',
    'sc_auto': 'Auto',
    'sc_off': 'Off',
    'sc_forced': 'Forced',
    'sc_nx': 'Tiles X',
    'sc_ny': 'Tiles Y',
    'sc_maxpoints': 'Max points per tile',
    'out_group': 'Output',
    'out_crs': 'Output CRS',
    'out_layer_name': 'Layer name',
    'out_add_layer': 'Add result layer to project',
    'out_style_freq': 'Style width by frequency',
    'out_export_group': 'Export',
    'out_export_format': 'Format',
    'out_export_path': 'File',
    'out_export_browse': 'Browse',
    'out_export_none': 'None',
    'out_export_geojson': 'GeoJSON',
    'out_export_graphml': 'GraphML',
    'out_export_gpkg': 'GeoPackage',
    'out_export_shp': 'Shapefile',
    'export_done': 'Exported to',
    'export_failed': 'Export failed',
    'tip_cell': 'Roughly 1/2–1/3 of the road width (haul road 6–10 m). Bigger = '
               'faster and less memory.',
    'tip_sigma': 'Larger for noisier data (dense canopy).',
    'tip_fmin': 'Do not cut rare long spurs (see the protect option).',
    'tip_resample': 'Close to the average spacing of track points. For sparse '
                    'data (fix every 15 min / 5 km) keep it large.',
    'tip_mindist': 'Drop points closer than this to the previous kept point of '
                   'the same device. Strongly reduces data size and speeds up '
                   'the whole run. 0 = off.',
    'tip_vmax': 'Points implying a higher speed are treated as errors.',
    'tip_gap': 'A jump larger than this starts a new sub-track (signal loss).',
    'tip_amax': 'Points whose acceleration between consecutive speeds exceeds '
                'this are treated as errors (spoofing/noise).',
    'tip_gap_dt': 'A time gap larger than this starts a new sub-track. For sparse '
                  'fixes (every 15 min) set it higher, otherwise tracks break '
                  'into single points.',
    'tip_slide_backend': 'What actually runs RidgeSlide. "Auto" = numba if it is '
                         'installed (else numpy). numba is tens of times faster. '
                         'NOTE: installing numba on the Dependencies tab does NOT '
                         'select it here — pick "Auto" or "numba". RidgeSlide only.',
    'tip_skel_backend': 'scikit-image — high-quality skeletonization; Zhang–Suen '
                        '— built-in dependency-free fallback.',
    'tip_sigma2': 'Smoothing of the surface after RidgeSlide, before thresholding. '
                  'Larger = smoother centerlines but less fine detail. RidgeSlide only.',
    'tip_sharpness': 'Sharpness of the density kernel: >0 emphasizes road ridges, '
                     '0 = plain Gaussian. RidgeSlide method only.',
    'tip_kde_radius': 'KDE kernel search radius. Larger = more continuous '
                      'corridors but wider blur. KDE method only.',
    'tip_kde_buffer': 'Width of the buffer that bridges gaps in sparse corridors '
                      '(mask dilation). KDE method only.',
    'tip_slide_loops': 'Bounds on the number of RidgeSlide compaction iterations. '
                       'RidgeSlide method only.',
    'tip_eps_mode': 'How the density threshold for the road mask is chosen: Auto '
                    '(Otsu) — from the histogram; Manual — set a value; Adaptive '
                    '— currently falls back to Otsu.',
    'tip_eps_value': 'Absolute density threshold (for Manual mode). Lower = more '
                     'roads and noise, higher = only dense parts.',
    'tip_eps_pct': 'Threshold by a density percentile (Percentile mode). 75 = '
                   'keep the top 25% of density. More robust than Otsu on sparse '
                   'KDE data where Otsu cuts above the roads.',
    'tip_fill_holes': 'Fill holes in the mask smaller than this — removes '
                      'skeleton loop "crossings" on the thick KDE mask. 0 = off. '
                      'Needs scikit-image.',
    'tip_loop_min': 'Remove short self-loops (micro "crossings") shorter than '
                    'this length. 0 = keep.',
    'tip_skel_medial': 'Medial axis (the centerline from the FGIS LK note) — '
                       'cleaner on thick KDE masks than plain skeletonization.',
    'tip_dp': 'Douglas–Peucker geometry simplification tolerance in meters. '
              'Larger = fewer vertices, coarser lines.',
    'tip_lmin': 'Edges shorter than this are removed as artifacts (unless '
                'protected by length/frequency).',
    'tip_protect': 'Do not remove long edges even if they are rare (keeps spurs / '
                   'skid trails).',
    'tip_sc_mode': 'Splitting the area into tiles to save memory: Auto — by point '
                   'count; Off — a single raster; Forced — set the grid.',
    'tip_sc_grid': 'Number of tiles along X and Y (Forced mode only).',
    'tip_sc_maxpoints': 'Point-count threshold per tile for auto splitting. '
                        'Smaller = more tiles and less memory per tile.',
    'tip_reb': 'Removes REB/spoofing artifacts: teleports (>120 km/h), jumps '
               '>200 m in <60 s, and A→B→C spikes (a point flies off and returns).',
    'tip_spur': 'Remove short dangling branches (spurs) — skeletonization '
                'artifacts. 0 = keep. Long roads are not touched.',
    'tip_smooth': 'Smooth the stair-steps of the raster skeleton (Chaikin '
                  'corner-cutting). More iterations = smoother lines. 0 = no '
                  'smoothing. Edge ends (nodes) stay put.',
    # --- Connectivity / post-processing (WS-Conn/WS-Post) ---
    'ds_slide_close': 'Mask closing (RidgeSlide), m',
    'tip_slide_close': 'Morphological closing of the road mask by dilation '
                       '(bridges gaps) for the RidgeSlide method. 0 = off. Analogous '
                       'to the KDE gap buffer.',
    'pt_intro': 'Improve an already-built graph without a full rebuild: bridge '
                'gaps, smooth stair-steps, drop small components.',
    'pt_conn_group': 'Graph connectivity',
    'pt_connect_gap': 'Bridge gaps within radius, m',
    'pt_bridge_facing': 'Bridge facing dead-ends up to, m',
    'pt_stitch': 'Stitch components into one network up to, m',
    'pt_break': 'Break edges at crossings (make junctions)',
    'pt_junction': 'Consolidate junction clusters within, m',
    'pt_min_component': 'Remove components shorter than, m',
    'pt_keep_largest': 'Keep only the largest network',
    'tip_connect_gap': 'Bridge gaps within this radius: a dangling end (dead-end) '
                       'is joined to the nearest OTHER end AND to the nearest '
                       'point on a neighbouring edge (a T-gap; the edge is split). '
                       '0 = off.',
    'tip_bridge_facing': 'Directional bridge: connect dead-ends that face each '
                         'other (their road continuations point at one another), '
                         'even beyond the normal radius — up to this distance. '
                         'Does not join random close dead-ends at a wide angle. '
                         '0 = off.',
    'tip_stitch': 'Stitch connected components into ONE network: join the nearest '
                  'nodes of different components until connected or the gap '
                  'exceeds this. Guarantees connectivity within the distance. '
                  '0 = off.',
    'tip_break': 'Split two edges that cross geometrically but share no node, '
                 'inserting a real junction (GRASS v.clean break). Improves '
                 'connectivity of roads that cross visually but are broken. Note: '
                 'creates a false junction at bridges/overpasses (roads that '
                 'cross without meeting).',
    'tip_junction': 'Consolidate clusters of nearby junction nodes into one node '
                    '(cleans the "bushy" intersections left by 8-connectivity, '
                    'OSMnx-like). 0 = off. Run after breaking at crossings.',
    'tip_min_component': 'Remove isolated network pieces whose total length is '
                         'below this. 0 = keep.',
    'tip_keep_largest': 'Keep only the single largest (by length) connected '
                        'network, dropping isolated fragments.',
    'pt_apply_group': 'Apply to an existing graph',
    'pt_source': 'Graph source',
    'pt_source_last': 'Last result',
    'pt_source_layer': 'Project layer',
    'pt_apply': 'Apply post-processing',
    'pt_done': 'Post-processing applied',
    'pt_no_graph': 'No graph: build one first or pick a line layer.',
    'aoi_group': 'Area of interest (AOI)',
    'aoi_source_label': 'AOI source',
    'aoi_none': 'No clipping',
    'aoi_file': 'Polygon from file',
    'aoi_layer': 'Project layer',
    'aoi_browse': 'Choose file',
    'tip_aoi': 'Clip points by an area-of-interest polygon BEFORE processing — '
               'removes points in the sea / outside the zone and shrinks data.',
    'aoi_load_failed': 'Failed to load the AOI polygon',
    'eta': 'ETA',
    'steps_plan': 'Steps',
    'libs_active': 'Available libraries',
    'tab_overview': 'Overview',
    'hist_frequency_title': 'Edge frequency',
    'hist_length_title': 'Edge length',
    'build_started': 'Build started',
    'build_no_folder': 'Choose a data folder or files first.',
    'build_no_input': 'Could not get points from the layer/file. Check the input '
                      'source (project layer or a GPX/KML/SHP file).',
    'build_done': 'Road graph built',
    'build_failed': 'Build failed',
    'build_cancelled': 'Build cancelled',
    'result_edges': 'edges',
    'result_nodes': 'nodes',
    'result_length_km': 'total length',
    'layer_added': 'Result layer added to the project',

    # --- Author dialog ---
    'version': 'Version',
    'author': 'Author',
    'contact': 'Contact',
    'year': 'Year',
    'organization': 'Organization',
    'multilingual_support': 'Multilingual interface (RU, EN).',
    'about_subtitle': 'Reconstruct road/path networks from GPS tracks',
    'about_algorithm_title': 'RidgeSlide — the engine',
    'about_algorithm_text': 'This plugin is a QGIS front-end for <b>RidgeSlide</b>'
                            ' — a density-ridge method that consolidates noisy GPS'
                            ' tracks into clean road centerlines. RidgeSlide was '
                            'conceived, generalized, developed and completed by '
                            'Alexander Kobyakov, building on Guo et al. (2020) and'
                            ' the Slide approach (paulmach/slide), with original '
                            'corrections and additions (KDE hybrid, percentile '
                            'thresholding, post-processing, parallel Numba).',

    # --- Donation dialog (identical to reference plugin) ---
    'donation_title': 'Support development',
    'donation_window_title': '☕ Support the development',
    'donation_description': 'GPS Road Builder is developed and maintained in '
                            'free time. If it is useful to you, you can support '
                            'further development. Thank you!',
    'donation_kofi': '☕ Ko-fi',
    'donation_tbank': '💳 T-Bank',
    'donation_github': '🐙 GitHub Sponsors',
}
