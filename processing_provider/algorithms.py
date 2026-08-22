# -*- coding: utf-8 -*-
"""The three public, reproducible GPS Road Builder Processing algorithms."""

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsProcessing, QgsProcessingAlgorithm,
    QgsProcessingException, QgsProcessingParameterBoolean,
    QgsProcessingParameterDefinition, QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink, QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFile, QgsProcessingParameterNumber, QgsWkbTypes,
)

from ..core import pipeline
from ..core.graph import postops
from ..qgis_adapter.layers import (
    dataframe_from_feature_source, metric_graph_from_feature_source,
    road_graph_fields, write_graph_to_sink,
)
from ..qgis_compat import qgis_enum
from ..translation_manager import translations
from . import ids


def _advanced(parameter):
    """Mark a parameter as optional fine tuning in QGIS 3 and 4."""
    flag = qgis_enum('ProcessingParameterFlag', 'Advanced',
                     QgsProcessingParameterDefinition, 'FlagAdvanced')
    parameter.setFlags(parameter.flags() | flag)
    return parameter


class _BaseAlgorithm(QgsProcessingAlgorithm):
    """Shared parameter mapping, feedback bridge and standard sink writing."""

    def group(self):
        return translations.get_text('processing_group')

    def groupId(self):
        return ids.GROUP_ID

    def shortHelpString(self):
        return translations.get_text('processing_help_general')

    @staticmethod
    def _number(machine_id, label_key, default, minimum=0.0, advanced=False,
                integer=False):
        kind = qgis_enum(
            'ProcessingNumberParameterType', 'Integer' if integer else 'Double',
            QgsProcessingParameterNumber)
        parameter = QgsProcessingParameterNumber(
            machine_id, translations.get_text(label_key), kind, default,
            minValue=minimum)
        return _advanced(parameter) if advanced else parameter

    def _add_build_parameters(self):
        self.addParameter(QgsProcessingParameterEnum(
            ids.PRESET, translations.get_text('processing_preset'),
            [translations.get_text('preset_' + name) for name in ids.PRESET_ORDER],
            defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            ids.METHOD, translations.get_text('processing_method'),
            [translations.get_text('method_slide'), translations.get_text('method_kde')],
            defaultValue=0))
        self.addParameter(self._number(ids.CELL_SIZE, 'processing_cell_size', 5.0, 0.01))
        self.addParameter(self._number(ids.MIN_FREQUENCY, 'processing_min_frequency', 2, 1,
                                       integer=True))
        self.addParameter(self._number(ids.MIN_LENGTH, 'processing_min_length', 30.0))
        for key, label, default in (
                (ids.MAX_SPEED, 'processing_max_speed', 70.0),
                (ids.MAX_ACCELERATION, 'processing_max_acceleration', 4.0),
                (ids.MIN_POINT_DISTANCE, 'processing_min_point_distance', 10.0),
                (ids.GAP_TIME, 'processing_gap_time', 5.0),
                (ids.GAP_DISTANCE, 'processing_gap_distance', 500.0),
                (ids.RESAMPLE_STEP, 'processing_resample_step', 5.0),
                (ids.SIGMA_1, 'processing_sigma1', 5.0),
                (ids.SIGMA_2, 'processing_sigma2', 3.0),
                (ids.SHARPNESS, 'processing_sharpness', 1.5),
                (ids.EPS_PERCENTILE, 'processing_threshold_percentile', 80.0),
                (ids.SIMPLIFY_TOLERANCE, 'processing_simplify_tolerance', 2.0)):
            self.addParameter(self._number(key, label, default, advanced=True))
        self.addParameter(_advanced(QgsProcessingParameterEnum(
            ids.EPS_MODE, translations.get_text('processing_threshold_mode'),
            [translations.get_text('gr_eps_auto'), translations.get_text('gr_eps_manual'),
             translations.get_text('gr_eps_percentile')], defaultValue=0)))

    def _add_postprocess_parameters(self):
        for key, label in (
                (ids.SPUR_LENGTH, 'processing_spur_length'),
                (ids.CONNECT_GAP, 'processing_connect_gap'),
                (ids.BRIDGE_FACING, 'processing_bridge_facing'),
                (ids.STITCH_MAX, 'processing_stitch_max'),
                (ids.JUNCTION_DISTANCE, 'processing_junction_distance'),
                (ids.MIN_COMPONENT, 'processing_min_component')):
            self.addParameter(self._number(key, label, 0.0, advanced=True))
        self.addParameter(self._number(ids.SMOOTH_ITERATIONS,
                                       'processing_smooth_iterations', 0, 0,
                                       advanced=True, integer=True))
        self.addParameter(_advanced(QgsProcessingParameterBoolean(
            ids.BREAK_CROSSINGS, translations.get_text('processing_break_crossings'),
            defaultValue=False)))
        self.addParameter(_advanced(QgsProcessingParameterBoolean(
            ids.KEEP_LARGEST, translations.get_text('processing_keep_largest'),
            defaultValue=False)))

    def _machine_values(self, parameters, context, include_build=True,
                        include_postprocess=False):
        values = {}
        if include_build:
            values[ids.PRESET] = ids.PRESET_ORDER[self.parameterAsEnum(parameters, ids.PRESET, context)]
            values[ids.METHOD] = ids.METHOD_OPTIONS[self.parameterAsEnum(parameters, ids.METHOD, context)]
            values[ids.CELL_SIZE] = self.parameterAsDouble(parameters, ids.CELL_SIZE, context)
            values[ids.MIN_FREQUENCY] = self.parameterAsInt(parameters, ids.MIN_FREQUENCY, context)
            values[ids.MIN_LENGTH] = self.parameterAsDouble(parameters, ids.MIN_LENGTH, context)
            for key in (ids.MAX_SPEED, ids.MAX_ACCELERATION, ids.MIN_POINT_DISTANCE,
                        ids.GAP_TIME, ids.GAP_DISTANCE, ids.RESAMPLE_STEP,
                        ids.SIGMA_1, ids.SIGMA_2, ids.SHARPNESS,
                        ids.EPS_PERCENTILE, ids.SIMPLIFY_TOLERANCE):
                values[key] = self.parameterAsDouble(parameters, key, context)
            values[ids.EPS_MODE] = ids.EPS_MODE_OPTIONS[
                self.parameterAsEnum(parameters, ids.EPS_MODE, context)]
        if include_postprocess:
            for key in (ids.SPUR_LENGTH, ids.CONNECT_GAP, ids.BRIDGE_FACING,
                        ids.STITCH_MAX, ids.JUNCTION_DISTANCE, ids.MIN_COMPONENT):
                values[key] = self.parameterAsDouble(parameters, key, context)
            values[ids.SMOOTH_ITERATIONS] = self.parameterAsInt(
                parameters, ids.SMOOTH_ITERATIONS, context)
            for key in (ids.BREAK_CROSSINGS, ids.KEEP_LARGEST):
                values[key] = self.parameterAsBool(parameters, key, context)
        return values

    @staticmethod
    def _feedback_progress(feedback):
        def callback(fraction, stage):
            feedback.setProgress(max(0.0, min(97.0, float(fraction) * 97.0)))
            feedback.pushInfo(translations.get_text('processing_stage').format(stage))
        return callback

    def _run_build(self, dataframe, values, feedback):
        feedback.pushInfo(translations.get_text('processing_building'))
        result = pipeline.build_road_graph(
            dataframe, params=ids.pipeline_params_from_machine_values(values),
            progress=self._feedback_progress(feedback), is_cancelled=feedback.isCanceled)
        if feedback.isCanceled() or result is None:
            raise QgsProcessingException(translations.get_text('processing_cancelled'))
        if result.get('partial'):
            raise QgsProcessingException(translations.get_text('processing_partial_result'))
        return result['graph']

    def _create_sink(self, parameters, context):
        line_string = qgis_enum('WkbType', 'LineString', QgsWkbTypes)
        sink, destination = self.parameterAsSink(
            parameters, ids.OUTPUT, context, road_graph_fields(), line_string,
            QgsCoordinateReferenceSystem('EPSG:4326'))
        if sink is None:
            raise QgsProcessingException(translations.get_text('processing_sink_failed'))
        return sink, destination

    def _write_result(self, graph, parameters, context, feedback):
        sink, destination = self._create_sink(parameters, context)
        count = write_graph_to_sink(graph, sink, feedback)
        if feedback.isCanceled():
            raise QgsProcessingException(translations.get_text('processing_cancelled'))
        feedback.setProgress(100.0)
        feedback.pushInfo(translations.get_text('processing_written').format(count))
        return {ids.OUTPUT: destination}


class BuildNetworkFromLayerAlgorithm(_BaseAlgorithm):
    def name(self):
        return ids.BUILD_FROM_LAYER

    def displayName(self):
        return translations.get_text('processing_build_from_layer')

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            ids.INPUT, translations.get_text('processing_input_layer'),
            [qgis_enum('ProcessingSourceType', 'VectorAnyGeometry',
                       QgsProcessing, 'TypeVectorAnyGeometry')]))
        self._add_build_parameters()
        self.addParameter(QgsProcessingParameterFeatureSink(
            ids.OUTPUT, translations.get_text('processing_output_network')))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, ids.INPUT, context)
        if source is None:
            raise QgsProcessingException(translations.get_text('processing_invalid_input'))
        try:
            dataframe = dataframe_from_feature_source(source, context.transformContext())
            if dataframe.empty:
                raise ValueError(translations.get_text('processing_empty_input'))
            graph = self._run_build(dataframe, self._machine_values(parameters, context), feedback)
            return self._write_result(graph, parameters, context, feedback)
        except QgsProcessingException:
            raise
        except Exception as exc:
            raise QgsProcessingException('{0}: {1}'.format(
                translations.get_text('processing_build_failed'), exc))

    def createInstance(self):
        return BuildNetworkFromLayerAlgorithm()


class BuildNetworkFromFolderAlgorithm(_BaseAlgorithm):
    def name(self):
        return ids.BUILD_FROM_FOLDER

    def displayName(self):
        return translations.get_text('processing_build_from_folder')

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(
            ids.FOLDER, translations.get_text('processing_input_folder'),
            behavior=qgis_enum('ProcessingFileParameterBehavior', 'Folder',
                               QgsProcessingParameterFile)))
        self._add_build_parameters()
        self.addParameter(QgsProcessingParameterFeatureSink(
            ids.OUTPUT, translations.get_text('processing_output_network')))

    def processAlgorithm(self, parameters, context, feedback):
        from ..core.io import csv_reader

        folder = self.parameterAsFile(parameters, ids.FOLDER, context)
        if not folder:
            raise QgsProcessingException(translations.get_text('processing_invalid_folder'))
        try:
            dataframe = csv_reader.load_dataset(folder)
            if dataframe.empty:
                raise ValueError(translations.get_text('processing_empty_input'))
            graph = self._run_build(dataframe, self._machine_values(parameters, context), feedback)
            return self._write_result(graph, parameters, context, feedback)
        except QgsProcessingException:
            raise
        except Exception as exc:
            raise QgsProcessingException('{0}: {1}'.format(
                translations.get_text('processing_build_failed'), exc))

    def createInstance(self):
        return BuildNetworkFromFolderAlgorithm()


class PostprocessNetworkAlgorithm(_BaseAlgorithm):
    def name(self):
        return ids.POSTPROCESS_NETWORK

    def displayName(self):
        return translations.get_text('processing_postprocess_network')

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            ids.INPUT, translations.get_text('processing_input_network'),
            [qgis_enum('GeometryType', 'Line', QgsWkbTypes, 'LineGeometry')]))
        self._add_postprocess_parameters()
        self.addParameter(QgsProcessingParameterFeatureSink(
            ids.OUTPUT, translations.get_text('processing_output_network')))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, ids.INPUT, context)
        if source is None:
            raise QgsProcessingException(translations.get_text('processing_invalid_input'))
        try:
            feedback.pushInfo(translations.get_text('processing_postprocessing'))
            graph, projector = metric_graph_from_feature_source(source, context.transformContext())
            if not graph.nodes:
                raise ValueError(translations.get_text('processing_empty_input'))
            values = self._machine_values(parameters, context, include_build=False,
                                          include_postprocess=True)
            result, _stats = postops.apply(
                graph, ids.pipeline_params_from_machine_values(values))
            pipeline._attach_lonlat(result, projector)
            return self._write_result(result, parameters, context, feedback)
        except QgsProcessingException:
            raise
        except Exception as exc:
            raise QgsProcessingException('{0}: {1}'.format(
                translations.get_text('processing_postprocess_failed'), exc))

    def createInstance(self):
        return PostprocessNetworkAlgorithm()
