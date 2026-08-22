# -*- coding: utf-8 -*-
"""Stable, non-localised public IDs for Processing workflows.

Do not rename these values: Model Designer models, batch jobs and scripts use
them as a public API.  Display strings are deliberately kept elsewhere.
"""

from ..core.presets import PRESET_ORDER, build_pipeline_params, preset_settings


PROVIDER_ID = 'gpsroadbuilder'
GROUP_ID = 'gpsroadbuilder'

BUILD_FROM_LAYER = 'build_network_from_layer'
BUILD_FROM_FOLDER = 'build_network_from_folder'
POSTPROCESS_NETWORK = 'postprocess_network'
ALGORITHM_IDS = (BUILD_FROM_LAYER, BUILD_FROM_FOLDER, POSTPROCESS_NETWORK)

INPUT = 'INPUT'
FOLDER = 'FOLDER'
OUTPUT = 'OUTPUT'
PRESET = 'PRESET'
METHOD = 'METHOD'
CELL_SIZE = 'CELL_SIZE'
MIN_FREQUENCY = 'MIN_FREQUENCY'
MIN_LENGTH = 'MIN_LENGTH'
MAX_SPEED = 'MAX_SPEED'
MAX_ACCELERATION = 'MAX_ACCELERATION'
MIN_POINT_DISTANCE = 'MIN_POINT_DISTANCE'
GAP_TIME = 'GAP_TIME'
GAP_DISTANCE = 'GAP_DISTANCE'
RESAMPLE_STEP = 'RESAMPLE_STEP'
SIGMA_1 = 'SIGMA_1'
SIGMA_2 = 'SIGMA_2'
SHARPNESS = 'SHARPNESS'
EPS_MODE = 'EPS_MODE'
EPS_PERCENTILE = 'EPS_PERCENTILE'
SIMPLIFY_TOLERANCE = 'SIMPLIFY_TOLERANCE'
SPUR_LENGTH = 'SPUR_LENGTH'
SMOOTH_ITERATIONS = 'SMOOTH_ITERATIONS'
CONNECT_GAP = 'CONNECT_GAP'
BRIDGE_FACING = 'BRIDGE_FACING'
STITCH_MAX = 'STITCH_MAX'
BREAK_CROSSINGS = 'BREAK_CROSSINGS'
JUNCTION_DISTANCE = 'JUNCTION_DISTANCE'
MIN_COMPONENT = 'MIN_COMPONENT'
KEEP_LARGEST = 'KEEP_LARGEST'

METHOD_OPTIONS = ('slide', 'kde')
EPS_MODE_OPTIONS = ('otsu', 'manual', 'percentile')

PARAMETER_IDS = (
    INPUT, FOLDER, OUTPUT, PRESET, METHOD, CELL_SIZE, MIN_FREQUENCY,
    MIN_LENGTH, MAX_SPEED, MAX_ACCELERATION, MIN_POINT_DISTANCE, GAP_TIME,
    GAP_DISTANCE, RESAMPLE_STEP, SIGMA_1, SIGMA_2, SHARPNESS, EPS_MODE,
    EPS_PERCENTILE, SIMPLIFY_TOLERANCE, SPUR_LENGTH, SMOOTH_ITERATIONS,
    CONNECT_GAP, BRIDGE_FACING, STITCH_MAX, BREAK_CROSSINGS,
    JUNCTION_DISTANCE, MIN_COMPONENT, KEEP_LARGEST,
)


def settings_from_machine_values(values):
    """Map pure Processing values to the existing preset/settings contract."""
    preset = values.get(PRESET, PRESET_ORDER[0])
    if preset not in PRESET_ORDER:
        preset = PRESET_ORDER[0]
    settings = preset_settings(preset)
    mapping = {
        METHOD: 'method', CELL_SIZE: 'cell_tau', MIN_FREQUENCY: 'edge_f_min',
        MIN_LENGTH: 'edge_l_min', MAX_SPEED: 'v_max_kmh',
        MAX_ACCELERATION: 'a_max', MIN_POINT_DISTANCE: 'min_point_dist',
        GAP_TIME: 'gap_dt_min', GAP_DISTANCE: 'gap_ds_m',
        RESAMPLE_STEP: 'resample_k', SIGMA_1: 'sigma1', SIGMA_2: 'sigma2',
        SHARPNESS: 'sharpness', EPS_MODE: 'eps_mode',
        EPS_PERCENTILE: 'eps_percentile', SIMPLIFY_TOLERANCE: 'dp_tolerance',
        SPUR_LENGTH: 'spur_min_m', SMOOTH_ITERATIONS: 'smooth_iters',
        CONNECT_GAP: 'connect_gap_m', BRIDGE_FACING: 'bridge_facing_m',
        STITCH_MAX: 'stitch_max_m', BREAK_CROSSINGS: 'break_crossings',
        JUNCTION_DISTANCE: 'junction_m', MIN_COMPONENT: 'min_component_m',
        KEEP_LARGEST: 'keep_largest',
    }
    for machine_id, settings_key in mapping.items():
        if machine_id in values:
            settings[settings_key] = values[machine_id]
    return settings


def pipeline_params_from_machine_values(values):
    """Build pipeline params solely from explicit Processing values."""
    return build_pipeline_params(settings_from_machine_values(values))
