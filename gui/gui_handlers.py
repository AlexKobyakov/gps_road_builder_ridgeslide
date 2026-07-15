# -*- coding: utf-8 -*-
"""
Event handlers for the GPS Road Builder main dialog.
Обработчики: язык, поддержка/автор, пресеты, выбор данных, запуск конвейера в
фоне (QgsTask), установка зависимостей, добавление слоя-результата.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import os
import time

from qgis.PyQt.QtCore import Qt, QThread
from qgis.PyQt.QtWidgets import QMessageBox, QFileDialog, QListWidgetItem, QTableWidgetItem
from qgis.core import QgsApplication

from ..translation_manager import translations
from ..core.settings_manager import SettingsManager, DEFAULTS


class GuiEventHandlers:
    """Обработчики событий главного диалога."""

    def __init__(self, dialog):
        self.dialog = dialog
        self.settings = SettingsManager()
        self.install_thread = None
        self.install_worker = None
        self.task = None
        self.last_result = None

    # ------------------------------------------------------------------
    # Настройки
    # ------------------------------------------------------------------

    def load_settings(self):
        self.dialog.apply_values(self.settings.get_all())

    def _persist(self, values):
        """Сохранить в QSettings только известные ключи."""
        self.settings.set_many({k: v for k, v in values.items()
                                if k in DEFAULTS})

    # ------------------------------------------------------------------
    # Язык / диалоги
    # ------------------------------------------------------------------

    def onLanguageChanged(self, _index):
        code = self.dialog.header.language_combo.currentData()
        if code and translations.set_language(code):
            self.settings.set('language', code)
            self.dialog.retranslateUi()

    def showDonation(self):
        from .simple_donation import SimpleDonationDialog
        SimpleDonationDialog(self.dialog).exec_()

    def showAuthorInfo(self):
        from .gui_dialogs import AuthorInfoDialog
        AuthorInfoDialog(self.dialog).exec_()

    def clearLogs(self):
        self.dialog.log_text.clear()

    # ------------------------------------------------------------------
    # Пресеты и данные
    # ------------------------------------------------------------------

    def applyPreset(self):
        from ..core.presets import preset_settings
        name = self.dialog.preset_combo.currentData()
        s = preset_settings(name)
        # Пресет — цельная стартовая конфигурация: применяем ко всем
        # параметрическим вкладкам (иначе поля «Предобработки», напр. gap/ресэмпл
        # у sparse_slide, игнорировались). Незаданные ключи → дефолты вкладки.
        for tab in (self.dialog.preprocess_tab, self.dialog.density_tab,
                    self.dialog.graph_tab, self.dialog.scale_tab,
                    self.dialog.postprocess_tab):
            tab.set_values(s)
        self.dialog._syncMethodDependentTabs()
        self.dialog.log_message('🎛️ ' + translations.get_text('preset_applied'))

    def savePreset(self):
        from ..core import presets
        t = translations.get_text
        path, _flt = QFileDialog.getSaveFileName(
            self.dialog, t('preset_save'), '', '*.json')
        if not path:
            return
        try:
            presets.save_preset(path, self.dialog.collect_values())
            self.dialog.log_message('💾 {0}: {1}'.format(t('preset_saved'), path))
        except Exception as exc:  # pragma: no cover - defensive
            self.dialog.log_message('❌ {0}'.format(exc))

    def loadPreset(self):
        from ..core import presets
        t = translations.get_text
        path, _flt = QFileDialog.getOpenFileName(
            self.dialog, t('preset_load'), '', '*.json')
        if not path:
            return
        try:
            self.dialog.apply_values(presets.load_preset(path))
            self.dialog.log_message('📂 {0}: {1}'.format(t('preset_loaded'), path))
        except Exception as exc:  # pragma: no cover - defensive
            self.dialog.log_message('❌ {0}'.format(exc))

    def browseCache(self):
        folder = QFileDialog.getExistingDirectory(
            self.dialog, translations.get_text('cache_dir'),
            self.dialog.output_tab.cache_line.text().strip()
            or os.path.expanduser('~'))
        if folder:
            self.dialog.output_tab.cache_line.setText(folder)

    def browseAoi(self):
        t = translations.get_text
        path, _flt = QFileDialog.getOpenFileName(
            self.dialog, t('aoi_browse'), '',
            '*.gpkg *.geojson *.json *.shp')
        if path:
            self.dialog.data_tab.aoi_path_line.setText(path)

    def browseVfile(self):
        t = translations.get_text
        path, _flt = QFileDialog.getOpenFileName(
            self.dialog, t('data_browse'), '',
            '*.gpx *.kml *.shp *.gpkg *.geojson')
        if path:
            self.dialog.data_tab.vfile_line.setText(path)

    def _input_dataframe(self, values):
        """Собрать df из слоя/файла для источников 'layer'/'vfile' (или None)."""
        from . import layers
        src = values.get('input_source', 'files')
        if src == 'vfile' and values.get('input_vfile'):
            return layers.df_from_file(values['input_vfile'])
        if src == 'layer':
            from qgis.core import QgsProject
            lid = self.dialog.data_tab.input_layer_combo.currentData()
            layer = QgsProject.instance().mapLayer(lid) if lid else None
            if layer is not None:
                return layers.df_from_layer(layer)
        return None

    def refreshLayerCombos(self):
        """Заполнить списки слоёв проекта: полигоны для AOI, линии для постобр."""
        try:
            from qgis.core import QgsProject, QgsWkbTypes
        except Exception:
            return
        aoi_combo = self.dialog.data_tab.aoi_layer_combo
        line_combo = self.dialog.postprocess_tab.layer_combo
        input_combo = self.dialog.data_tab.input_layer_combo
        for combo in (aoi_combo, line_combo, input_combo):
            combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if not hasattr(layer, 'geometryType'):
                continue
            gtype = layer.geometryType()
            if gtype == QgsWkbTypes.PolygonGeometry:
                aoi_combo.addItem(layer.name(), layer.id())
            elif gtype == QgsWkbTypes.LineGeometry:
                line_combo.addItem(layer.name(), layer.id())
                input_combo.addItem(layer.name(), layer.id())
            elif gtype == QgsWkbTypes.PointGeometry:
                input_combo.addItem(layer.name(), layer.id())

    def _load_aoi_polygon(self, values):
        """Загрузить кольца полигона AOI по настройкам (файл/слой) или None."""
        from . import layers
        src = values.get('aoi_source', '')
        try:
            if src == 'file' and values.get('aoi_path'):
                return layers.polygon_rings_from_file(values['aoi_path'])
            if src == 'layer':
                from qgis.core import QgsProject
                lid = self.dialog.data_tab.aoi_layer_combo.currentData()
                layer = QgsProject.instance().mapLayer(lid) if lid else None
                if layer is not None:
                    return layers.polygon_rings_from_layer(layer)
        except Exception as exc:  # pragma: no cover - defensive
            self.dialog.log_message('⚠️ {0}: {1}'.format(
                translations.get_text('aoi_load_failed'), exc))
        return None

    def browseFolder(self):
        start = self.dialog.data_tab.folder_line.text().strip() \
            or os.path.expanduser('~')
        folder = QFileDialog.getExistingDirectory(
            self.dialog, translations.get_text('data_browse'), start)
        if folder:
            self.dialog.data_tab.folder_line.setText(folder)
            self.scanFolder()

    def scanFolder(self):
        from ..core.io import csv_reader
        folder = self.dialog.data_tab.folder_line.text().strip()
        lst = self.dialog.data_tab.file_list
        lst.clear()
        if not folder or not os.path.isdir(folder):
            return
        files = csv_reader.iter_data_files(folder)
        for month, path in files:
            item = QListWidgetItem('{0} / {1}'.format(month, os.path.basename(path)))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, path)
            lst.addItem(item)
        self.dialog.data_tab.info_label.setText(
            translations.get_text('data_files_found').format(len(files)))

    def browseExport(self):
        t = translations.get_text
        fmt = self.dialog.output_tab.export_format_combo.currentData()
        ext = {'geojson': '*.geojson', 'graphml': '*.graphml',
               'gpkg': '*.gpkg', 'shp': '*.shp'}.get(fmt, '*.*')
        path, _flt = QFileDialog.getSaveFileName(
            self.dialog, t('out_export_browse'), '', ext)
        if path:
            self.dialog.output_tab.export_path_line.setText(path)

    def _export_result(self, graph):
        """Экспорт результата в выбранный формат (после сборки)."""
        values = self.dialog.output_tab.get_values()
        fmt = values.get('export_format', 'none')
        path = values.get('export_path', '')
        if fmt == 'none' or not path:
            return
        t = translations.get_text
        try:
            from ..core.io import writer
            if fmt == 'geojson':
                writer.write_geojson(graph, path)
            elif fmt == 'graphml':
                writer.write_graphml(graph, path)
            else:
                from . import layers
                layer = layers.build_road_layer(graph, style_by_frequency=False)
                writer.save_vector_layer(layer, path, driver_key=fmt)
            self.dialog.log_message('💾 {0} {1}'.format(t('export_done'), path))
        except Exception as exc:  # pragma: no cover - defensive
            self.dialog.log_message('❌ {0}: {1}'.format(t('export_failed'), exc))

    def _selected_paths(self):
        lst = self.dialog.data_tab.file_list
        paths = []
        for i in range(lst.count()):
            item = lst.item(i)
            if item.checkState() == Qt.Checked:
                paths.append(item.data(Qt.UserRole))
        return paths

    # ------------------------------------------------------------------
    # Построение
    # ------------------------------------------------------------------

    def build(self):
        from ..core.presets import build_pipeline_params
        from ..tasks.build_task import BuildRoadGraphTask

        t = translations.get_text
        if self.task is not None:
            QMessageBox.information(self.dialog, t('info'), t('build_started'))
            return

        values = self.dialog.collect_values()
        start_stage = values.get('start_stage', '')
        resuming = start_stage in ('points', 'tracks') and values.get('cache_dir')
        input_source = values.get('input_source', 'files')

        folder = self.dialog.data_tab.folder_line.text().strip()
        paths = self._selected_paths()
        # Слой/файл: собираем df сразу (основной поток) — конвертация геометрии.
        input_df = None
        if not resuming and input_source in ('layer', 'vfile'):
            try:
                input_df = self._input_dataframe(values)
            except Exception as exc:
                QMessageBox.warning(self.dialog, t('warning'), str(exc))
                return
            if input_df is None or input_df.empty:
                QMessageBox.warning(self.dialog, t('warning'), t('build_no_input'))
                return
        elif (not resuming and input_source == 'files' and not paths
              and not (folder and os.path.isdir(folder))):
            QMessageBox.warning(self.dialog, t('warning'), t('build_no_folder'))
            return

        self._persist(values)
        pparams = build_pipeline_params(values)
        if 'tile_grid' in values:
            pparams['tile_grid'] = values['tile_grid']
        if 'max_points_per_tile' in values:
            pparams['max_points_per_tile'] = int(values['max_points_per_tile'])
        pparams['cache_dir'] = values.get('cache_dir', '')
        pparams['start_stage'] = start_stage
        pparams['stop_after'] = values.get('stop_after', '')
        aoi_rings = self._load_aoi_polygon(values)
        if aoi_rings:
            pparams['aoi_polygon'] = aoi_rings

        self._output_opts = {
            'add_layer': values.get('add_layer', True),
            'style_freq': values.get('style_freq', True),
            'layer_name': values.get('layer_name', 'GPS Road Network'),
        }

        task_params = {'pipeline_params': pparams}
        if input_df is not None:
            task_params['dataframe'] = input_df
        elif paths:
            task_params['input_paths'] = paths
        elif folder:
            task_params['input_folder'] = folder
        # при резюме с чекпоинта входные данные не требуются (build_task вернёт
        # пустой кадр, а pipeline возьмёт данные из кэша)

        self.task = BuildRoadGraphTask(t('window_title'), params=task_params)
        self.task.progressChanged.connect(self._on_progress)
        self.task.progressMessage.connect(self._on_step)
        self.task.taskCompleted.connect(self._on_completed)
        self.task.taskTerminated.connect(self._on_terminated)

        self.dialog.progress_bar.setRange(0, 100)
        self.dialog.progress_bar.setValue(0)
        self.dialog.progress_bar.setVisible(True)
        self.dialog.control_buttons.build_button.setEnabled(False)
        self._build_start = time.time()
        self.dialog.log_message('🚀 ' + t('build_started'))
        self._log_plan()
        QgsApplication.taskManager().addTask(self.task)

    def _log_plan(self):
        """Показать заранее список шагов и активные библиотеки (5.1, 5.2)."""
        from ..core.pipeline import STEPS
        from ..core.deps import installer
        t = translations.get_text
        self.dialog.log_message('📋 {0}: {1}'.format(
            t('steps_plan'), ' → '.join(STEPS)))
        active = [name for name, imp, _pk, ok in installer.package_status() if ok]
        self.dialog.log_message('🧩 {0}: {1}'.format(
            t('libs_active'), ', '.join(active) if active else '—'))

    def cancel(self):
        if self.task is not None:
            self.task.cancel()
            self.dialog.log_message('⚠️ ' + translations.get_text('cancel'))

    def _on_progress(self, value):
        self.dialog.progress_bar.setValue(int(value))
        self._update_eta(value / 100.0)

    def _on_step(self, _frac, message):
        if message and message not in ('done',):
            self.dialog.log_message('⏳ ' + str(message))

    def _update_eta(self, frac):
        """Оценить остаток времени по прошедшему времени и доле выполнения."""
        t = translations.get_text
        start = getattr(self, '_build_start', None)
        if not start or frac <= 0.01:
            self.dialog.progress_label.setText('📊 ' + t('progress'))
            return
        elapsed = time.time() - start
        remaining = elapsed * (1.0 - frac) / frac
        self.dialog.progress_label.setText(
            '📊 {0}: {1:.0f}%  ·  {2}: {3}'.format(
                t('progress'), frac * 100.0, t('eta'),
                self._fmt_duration(remaining)))

    @staticmethod
    def _fmt_duration(seconds):
        seconds = int(max(0, seconds))
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return '{0}ч {1}м'.format(h, m)
        if m:
            return '{0}м {1}с'.format(m, s)
        return '{0}с'.format(s)

    def _on_completed(self):
        t = translations.get_text
        task = self.task
        self.task = None
        self._reset_progress()
        result = getattr(task, 'result_payload', None)
        if not result:
            return
        stats = result.get('stats', {})
        if result.get('partial'):
            # Остановка после этапа (пошаговый режим): слой не строим.
            self.dialog.log_message('⏸️ {0}: {1}'.format(
                t('stopped_after'), result.get('stage', '')))
            self._fill_results(stats)
            return
        self.dialog.log_message(
            '🎉 {0}: {1} {2}, {3} {4}'.format(
                t('build_done'), stats.get('edges', 0), t('result_edges'),
                stats.get('nodes', 0), t('result_nodes')))
        self.last_result = result           # для вкладки «Постобработка»
        self._fill_results(stats)
        self._fill_overview(result['graph'], stats)
        self._maybe_add_layer(result['graph'])
        self._export_result(result['graph'])

    def _on_terminated(self):
        t = translations.get_text
        task = self.task
        self.task = None
        self._reset_progress()
        if getattr(task, 'exception', None) is not None:
            from .gui_dialogs import ErrorDialog
            self.dialog.log_message('❌ ' + t('build_failed'))
            ErrorDialog(t('error'), t('build_failed'),
                        details=str(task.exception), parent=self.dialog).exec_()
        else:
            self.dialog.log_message('⚠️ ' + t('build_cancelled'))

    def _reset_progress(self):
        self.dialog.progress_bar.setVisible(False)
        self.dialog.control_buttons.build_button.setEnabled(True)
        self.dialog.progress_label.setText(
            '📊 ' + translations.get_text('progress'))

    def _fill_results(self, stats):
        table = self.dialog.results_table
        rows = [
            ('input', stats.get('input', 0)),
            ('duplicates_removed', stats.get('duplicates_removed', 0)),
            ('near_dup_removed', stats.get('near_dup_removed', 0)),
            ('reb_removed', stats.get('reb_removed', 0)),
            ('tracks', stats.get('tracks', 0)),
            ('tiles', stats.get('tiles', 1)),
            ('edges', stats.get('edges', 0)),
            ('nodes', stats.get('nodes', 0)),
        ]
        table.setRowCount(len(rows))
        for r, (key, value) in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(str(key)))
            table.setItem(r, 1, QTableWidgetItem('OK'))
            table.setItem(r, 2, QTableWidgetItem(str(value)))

    def _fill_overview(self, graph, stats):
        from ..core.io import features
        feats = features.road_graph_features(graph)
        self.dialog.hist_frequency.set_values(features.frequency_values(feats))
        self.dialog.hist_length.set_values(features.length_values(feats))
        total_km = sum(f['length'] for f in feats) / 1000.0
        t = translations.get_text
        self.dialog.stats_label.setText(
            '{0}: {1}  |  {2}: {3}  |  {4}: {5:.1f} km'.format(
                t('result_edges'), stats.get('edges', 0),
                t('result_nodes'), stats.get('nodes', 0),
                t('result_length_km'), total_km))

    # ------------------------------------------------------------------
    # Постобработка готового графа (§WS-Post)
    # ------------------------------------------------------------------

    def applyPostprocess(self):
        """Применить связность/сглаживание к последнему результату или слою."""
        from ..core.presets import build_pipeline_params
        from ..core.graph import postops
        from ..core import pipeline, run_log
        from ..core.logging_setup import get_logger, runs_manifest_path
        from . import layers
        t = translations.get_text

        params = build_pipeline_params(self.dialog.collect_values())
        source = self.dialog.postprocess_tab.source_combo.currentData()

        graph, projector = self._postprocess_source(source)
        if graph is None:
            QMessageBox.warning(self.dialog, t('warning'), t('pt_no_graph'))
            return
        # §WS-L: пишем параметры постобработки в файл-лог (как для сборки).
        logger = get_logger()
        logger.info('=== post-processing (source=%s) ===', source)
        for line in run_log.format_params(params):
            logger.info(line)
        try:
            out, stats = postops.apply(graph, params)
            pipeline._attach_lonlat(out, projector)
            name = '{0} (post)'.format(
                self.dialog.output_tab.get_values().get(
                    'layer_name', 'GPS Road Network'))
            layer = layers.build_road_layer(out, name=name, style_by_frequency=True)
            layers.add_to_project(layer)
            self.last_result = {'graph': out, 'projector': projector,
                                'stats': stats, 'params': params}
            detail = ('bridged={0} snapped={1} faced={2} stitched={3} '
                      'broken={4} junctions={5} comp_dropped={6}'.format(
                          stats.get('bridged', 0), stats.get('snapped', 0),
                          stats.get('faced', 0), stats.get('stitched', 0),
                          stats.get('broken', 0), stats.get('junctions_merged', 0),
                          stats.get('components_dropped', 0)))
            logger.info('post done: %d edges, %d nodes | %s',
                        stats.get('edges', 0), stats.get('nodes', 0), detail)
            try:
                with open(runs_manifest_path(), 'a', encoding='utf-8') as fh:
                    fh.write(run_log.manifest_line(
                        'post', params, stats) + '\n')
            except Exception:  # pragma: no cover - defensive
                pass
            self.dialog.log_message('✨ {0}: {1} {2}, {3} {4}'.format(
                t('pt_done'), stats.get('edges', 0), t('result_edges'),
                stats.get('nodes', 0), t('result_nodes')))
            self.dialog.log_message('   ↳ ' + detail)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception('Post-processing failed')
            self.dialog.log_message('❌ {0}'.format(exc))

    def _postprocess_source(self, source):
        """Вернуть (metric_graph, projector) из последнего результата или слоя."""
        if source == 'last':
            res = self.last_result
            if not res or not res.get('graph'):
                return None, None
            return res['graph'], res['projector']
        # source == 'layer': прочитать слой линий и спроецировать в метрику
        from qgis.core import QgsProject
        from ..core.density import projection
        from ..core.graph import simplify as simplify_mod
        from . import layers
        import numpy as np
        lid = self.dialog.postprocess_tab.layer_combo.currentData()
        layer = QgsProject.instance().mapLayer(lid) if lid else None
        if layer is None:
            return None, None
        g = layers.graph_from_layer(layer)
        if not g.nodes:
            return None, None
        lons = np.array([xy[0] for xy in g.nodes.values()], dtype=float)
        lats = np.array([xy[1] for xy in g.nodes.values()], dtype=float)
        projector = projection.Projector.for_data(lons, lats)
        for nid, (lon, lat) in list(g.nodes.items()):
            x, y = projector.forward(np.array([lon]), np.array([lat]))
            g.nodes[nid] = (float(x[0]), float(y[0]))
        for e in g.edges:
            ll = e['coords_lonlat']
            x, y = projector.forward(ll[:, 0], ll[:, 1])
            e['coords'] = np.column_stack([x, y])
            e['length'] = simplify_mod.polyline_length(e['coords'])
        return g, projector

    def _maybe_add_layer(self, graph):
        if not getattr(self, '_output_opts', {}).get('add_layer', True):
            return
        try:
            from . import layers
            layer = layers.build_road_layer(
                graph, name=self._output_opts.get('layer_name', 'GPS Road Network'),
                style_by_frequency=self._output_opts.get('style_freq', True))
            layers.add_to_project(layer)
            self.dialog.log_message(
                '🗺️ ' + translations.get_text('layer_added'))
        except Exception as exc:  # pragma: no cover - defensive
            self.dialog.log_message('❌ ' + str(exc))

    # ------------------------------------------------------------------
    # Установка зависимостей
    # ------------------------------------------------------------------

    def recheckDependencies(self):
        self.dialog.deps_widget.refresh()
        self.dialog.log_message('🔄 ' + translations.get_text('deps_recheck'))

    def installDependencies(self):
        from ..core.deps import installer
        from ..core.deps.install_worker import InstallWorker
        from .gui_dialogs import InstallProgressDialog, ErrorDialog

        t = translations.get_text
        if self.install_thread is not None:
            QMessageBox.information(self.dialog, t('info'), t('installing'))
            return

        selected = self.dialog.deps_widget.selected_packages()
        if not selected:
            QMessageBox.information(self.dialog, t('info'), t('deps_intro'))
            return

        method = self.dialog.deps_widget.selected_method()
        specs = [cfg['pip_spec'] for _name, cfg in selected]
        names = ', '.join(name for name, _cfg in selected)

        wheel_urls, folder = [], None
        if method in ('auto', 'pip') and not installer.pip_available():
            if method == 'pip':
                QMessageBox.warning(self.dialog, t('warning'),
                                    t('deps_pip_unavailable'))
                return
            method = 'wheels'
        if method == 'wheels':
            for _name, cfg in selected:
                for urls in cfg.get('wheel_bundles', {}).values():
                    wheel_urls.extend(urls)
            if not wheel_urls:
                QMessageBox.warning(self.dialog, t('warning'),
                                    t('deps_pip_unavailable'))
                return
        if method == 'folder':
            folder = QFileDialog.getExistingDirectory(
                self.dialog, t('deps_choose_folder'))
            if not folder:
                return

        progress = InstallProgressDialog(t('installing'), self.dialog)
        self.install_thread = QThread(self.dialog)
        self.install_worker = InstallWorker(
            specs, method=method, wheel_urls=wheel_urls, folder=folder)
        self.install_worker.moveToThread(self.install_thread)
        self.install_thread.started.connect(self.install_worker.run)
        self.install_worker.progress.connect(progress.update_progress)
        self.install_worker.status.connect(progress.set_status)
        progress.cancel_button.clicked.connect(self.install_worker.cancel)

        result = {}

        def on_finished(success, payload):
            result['success'] = success
            result['payload'] = payload
            progress.accept()

        self.install_worker.finished.connect(on_finished)
        self.install_thread.start()
        self.dialog.log_message('📥 ' + t('deps_installing').format(names))
        progress.exec_()

        if 'success' not in result:
            self.install_worker.cancel()
        self.install_thread.quit()
        self.install_thread.wait(15000)
        self.install_thread = None
        self.install_worker = None

        if result.get('success'):
            self.dialog.log_message('✅ ' + t('deps_install_done').format(names))
            self.dialog.deps_widget.refresh()
        else:
            payload = result.get('payload', '')
            if payload and payload != 'cancelled':
                self.dialog.log_message('❌ ' + t('deps_install_failed').format(names))
                ErrorDialog(t('error'), t('deps_install_failed').format(names),
                            details=payload, parent=self.dialog).exec_()
