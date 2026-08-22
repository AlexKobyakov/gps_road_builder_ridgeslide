# -*- coding: utf-8 -*-
"""
Settings tabs for the GPS Road Builder dialog (real controls).
Вкладки с реальными контролами (Данные…Вывод). Каждая вкладка умеет
get_values()/set_values() в терминах ключей настроек (settings_manager).

Дизайн — в стиле референсного плагина garmin_export.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QListWidget, QCheckBox, QSpinBox, QDoubleSpinBox
)

from .gui_components import StyledComboBox, create_styled_button, create_info_label
from .i18n import RetranslatableMixin, retranslate_combo
from ..translation_manager import translations


def _dspin(minv, maxv, step, decimals=2, value=0.0):
    sp = QDoubleSpinBox()
    sp.setRange(minv, maxv)
    sp.setSingleStep(step)
    sp.setDecimals(decimals)
    sp.setValue(value)
    return sp


def _ispin(minv, maxv, value=0):
    sp = QSpinBox()
    sp.setRange(minv, maxv)
    sp.setValue(value)
    return sp


class DataTab(RetranslatableMixin, QWidget):
    """Вкладка «Данные»: выбор папки/файлов, сезонность."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_i18n()
        self._files_found = None
        t = translations.get_text
        layout = QVBoxLayout(self)

        self.group = QGroupBox(t('data_group'))
        form = QVBoxLayout(self.group)

        # Источник входа: файлы CSV/XLSX | слой проекта | файл GPX/KML/SHP.
        src_row = QHBoxLayout()
        self.source_combo = StyledComboBox()
        for key, code in (('src_files', 'files'), ('src_layer', 'layer'),
                          ('src_vfile', 'vfile')):
            self.source_combo.addItem(t(key), code)
        self.source_label = self._bind_text(QLabel(), 'data_source')
        src_row.addWidget(self.source_label)
        src_row.addWidget(self.source_combo, 1)
        form.addLayout(src_row)

        # (а) Файлы CSV/XLSX
        self.files_widget = QWidget()
        fw = QVBoxLayout(self.files_widget)
        fw.setContentsMargins(0, 0, 0, 0)
        folder_row = QHBoxLayout()
        self.folder_line = QLineEdit()
        self.folder_line.setPlaceholderText(t('data_folder'))
        self.browse_button = create_styled_button(t('data_browse'), 'secondary', '📂')
        self.scan_button = create_styled_button(t('data_scan'), 'secondary', '🔎')
        folder_row.addWidget(self.folder_line, 1)
        folder_row.addWidget(self.browse_button)
        folder_row.addWidget(self.scan_button)
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(120)
        # Ограничиваем высоту, чтобы группа AOI ниже была видна без прокрутки (#3).
        self.file_list.setMaximumHeight(200)
        self.info_label = create_info_label(t('data_load_hint'))
        fw.addLayout(folder_row)
        fw.addWidget(self.file_list)
        fw.addWidget(self.info_label)
        form.addWidget(self.files_widget)

        # (б) Слой проекта (точки/линии)
        self.layer_widget = QWidget()
        lw = QVBoxLayout(self.layer_widget)
        lw.setContentsMargins(0, 0, 0, 0)
        self.input_layer_combo = StyledComboBox()
        lw.addWidget(create_info_label(t('data_layer_hint')))
        lw.addWidget(self.input_layer_combo)
        form.addWidget(self.layer_widget)

        # (в) Файл GPX/KML/SHP
        self.vfile_widget = QWidget()
        vw = QHBoxLayout(self.vfile_widget)
        vw.setContentsMargins(0, 0, 0, 0)
        self.vfile_line = QLineEdit()
        self.vfile_browse_button = create_styled_button(
            t('data_browse'), 'secondary', '📂')
        vw.addWidget(self.vfile_line, 1)
        vw.addWidget(self.vfile_browse_button)
        form.addWidget(self.vfile_widget)

        self.season_check = QCheckBox(t('data_season_split'))
        form.addWidget(self.season_check)
        layout.addWidget(self.group)
        self.source_combo.currentIndexChanged.connect(self._sync_source)
        self._sync_source()

        # Область интереса (AOI) — обрезка точек по полигону (§WS-AOI).
        self.aoi_group = self._bind_text(QGroupBox(), 'aoi_group')
        aform = QFormLayout(self.aoi_group)
        self.aoi_source_combo = StyledComboBox()
        for key, code in (('aoi_none', ''), ('aoi_file', 'file'),
                          ('aoi_layer', 'layer')):
            self.aoi_source_combo.addItem(t(key), code)
        self.aoi_source_combo.setToolTip(t('tip_aoi'))
        aoi_row = QHBoxLayout()
        self.aoi_path_line = QLineEdit()
        self.aoi_browse_button = create_styled_button(
            t('aoi_browse'), 'secondary', '📂')
        aoi_row.addWidget(self.aoi_path_line, 1)
        aoi_row.addWidget(self.aoi_browse_button)
        self.aoi_layer_combo = StyledComboBox()
        self._add_form_row(aform, 'aoi_source_label', self.aoi_source_combo)
        self._add_form_row(aform, 'aoi_file', aoi_row)
        self._add_form_row(aform, 'aoi_layer', self.aoi_layer_combo)
        layout.addWidget(self.aoi_group)
        self.aoi_source_combo.currentIndexChanged.connect(self._sync_aoi)
        self._sync_aoi()
        self.retranslateUi()

    def retranslateUi(self):
        self._retranslate_bound_widgets()
        self.group.setTitle(translations.get_text('data_group'))
        self.folder_line.setPlaceholderText(translations.get_text('data_folder'))
        self.browse_button.setText('📂 ' + translations.get_text('data_browse'))
        self.scan_button.setText('🔎 ' + translations.get_text('data_scan'))
        self.vfile_browse_button.setText('📂 ' + translations.get_text('data_browse'))
        self.aoi_browse_button.setText('📂 ' + translations.get_text('aoi_browse'))
        self.season_check.setText(translations.get_text('data_season_split'))
        retranslate_combo(
            self.source_combo, (('src_files', 'files'), ('src_layer', 'layer'),
                                ('src_vfile', 'vfile')))
        retranslate_combo(
            self.aoi_source_combo, (('aoi_none', ''), ('aoi_file', 'file'),
                                    ('aoi_layer', 'layer')))
        self.aoi_source_combo.setToolTip(translations.get_text('tip_aoi'))
        if self._files_found is None:
            self.info_label.setText(translations.get_text('data_load_hint'))
        else:
            self.info_label.setText(
                translations.get_text('data_files_found').format(self._files_found))

    def set_files_found(self, count):
        self._files_found = count
        self.info_label.setText(translations.get_text('data_files_found').format(count))

    def _sync_aoi(self):
        src = self.aoi_source_combo.currentData()
        self.aoi_path_line.setEnabled(src == 'file')
        self.aoi_browse_button.setEnabled(src == 'file')
        self.aoi_layer_combo.setEnabled(src == 'layer')

    def _sync_source(self):
        src = self.source_combo.currentData()
        self.files_widget.setVisible(src == 'files')
        self.layer_widget.setVisible(src == 'layer')
        self.vfile_widget.setVisible(src == 'vfile')

    def set_values(self, s):
        self.folder_line.setText(str(s.get('input_folder', '') or ''))
        self.season_check.setChecked(bool(s.get('split_seasons', False)))
        idx = self.source_combo.findData(str(s.get('input_source', 'files')))
        if idx >= 0:
            self.source_combo.setCurrentIndex(idx)
        self.vfile_line.setText(str(s.get('input_vfile', '') or ''))
        idx = self.aoi_source_combo.findData(str(s.get('aoi_source', '') or ''))
        if idx >= 0:
            self.aoi_source_combo.setCurrentIndex(idx)
        self.aoi_path_line.setText(str(s.get('aoi_path', '') or ''))
        self._sync_source()
        self._sync_aoi()

    def get_values(self):
        return {
            'input_folder': self.folder_line.text().strip(),
            'split_seasons': self.season_check.isChecked(),
            'input_source': self.source_combo.currentData(),
            'input_vfile': self.vfile_line.text().strip(),
            'aoi_source': self.aoi_source_combo.currentData(),
            'aoi_path': self.aoi_path_line.text().strip(),
        }


class PreprocessTab(RetranslatableMixin, QWidget):
    """Вкладка «Предобработка»."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_i18n()
        t = translations.get_text
        layout = QVBoxLayout(self)
        self.group = QGroupBox()
        form = QFormLayout(self.group)

        self.mindist_spin = _dspin(0, 1000, 1, 1, 10)
        self.mindist_spin.setToolTip(t('tip_mindist'))
        self.vmax_spin = _dspin(1, 300, 5, 0, 70)
        self.vmax_spin.setToolTip(t('tip_vmax'))
        self.amax_spin = _dspin(0.1, 50, 0.5, 1, 4)
        self.amax_spin.setToolTip(t('tip_amax'))
        self.gap_dt_spin = _dspin(0.1, 600, 1, 1, 5)
        self.gap_dt_spin.setToolTip(t('tip_gap_dt'))
        self.gap_ds_spin = _dspin(1, 100000, 50, 0, 500)
        self.gap_ds_spin.setToolTip(t('tip_gap'))
        self.resample_spin = _dspin(0.5, 1000, 1, 1, 5)
        self.resample_spin.setToolTip(t('tip_resample'))
        self.reb_check = QCheckBox(t('pp_reb'))
        self.reb_check.setToolTip(t('tip_reb'))

        self._add_form_row(form, 'pp_mindist', self.mindist_spin)
        self._add_form_row(form, 'pp_vmax', self.vmax_spin)
        self._add_form_row(form, 'pp_amax', self.amax_spin)
        self._add_form_row(form, 'pp_gap_dt', self.gap_dt_spin)
        self._add_form_row(form, 'pp_gap_ds', self.gap_ds_spin)
        self._add_form_row(form, 'pp_resample', self.resample_spin)
        self._add_form_row(form, '', self.reb_check)
        layout.addWidget(self.group)
        self.retranslateUi()

    def retranslateUi(self):
        self._retranslate_bound_widgets()
        t = translations.get_text
        self.group.setTitle(t('pp_group'))
        self.reb_check.setText(t('pp_reb'))
        for widget, key in ((self.mindist_spin, 'tip_mindist'),
                            (self.vmax_spin, 'tip_vmax'), (self.amax_spin, 'tip_amax'),
                            (self.gap_dt_spin, 'tip_gap_dt'), (self.gap_ds_spin, 'tip_gap'),
                            (self.resample_spin, 'tip_resample'), (self.reb_check, 'tip_reb')):
            widget.setToolTip(t(key))

    def apply_method(self, is_kde):
        """Деактивировать поля, нерелевантные для метода KDE (ресэмпл не нужен)."""
        self.resample_spin.setEnabled(not is_kde)

    def set_values(self, s):
        self.mindist_spin.setValue(float(s.get('min_point_dist', 10.0)))
        self.vmax_spin.setValue(float(s.get('v_max_kmh', 70.0)))
        self.amax_spin.setValue(float(s.get('a_max', 4.0)))
        self.gap_dt_spin.setValue(float(s.get('gap_dt_min', 5.0)))
        self.gap_ds_spin.setValue(float(s.get('gap_ds_m', 500.0)))
        self.resample_spin.setValue(float(s.get('resample_k', 5.0)))
        self.reb_check.setChecked(bool(s.get('reb_enabled', False)))

    def get_values(self):
        return {
            'min_point_dist': self.mindist_spin.value(),
            'v_max_kmh': self.vmax_spin.value(),
            'a_max': self.amax_spin.value(),
            'gap_dt_min': self.gap_dt_spin.value(),
            'gap_ds_m': self.gap_ds_spin.value(),
            'resample_k': self.resample_spin.value(),
            'reb_enabled': self.reb_check.isChecked(),
        }


class DensitySlideTab(RetranslatableMixin, QWidget):
    """Вкладка «Плотность / Slide»."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_i18n()
        t = translations.get_text
        layout = QVBoxLayout(self)

        self.method_group = QGroupBox()
        mform = QFormLayout(self.method_group)
        self.method_combo = StyledComboBox()
        self.method_combo.addItem(t('method_slide'), 'slide')
        self.method_combo.addItem(t('method_kde'), 'kde')
        self.method_combo.setToolTip(t('tip_method'))
        self.slide_backend_combo = StyledComboBox()
        for key, code in (('backend_auto', 'auto'), ('backend_numba', 'numba'),
                          ('backend_numpy', 'numpy')):
            self.slide_backend_combo.addItem(t(key), code)
        self.slide_backend_combo.setToolTip(t('tip_slide_backend'))
        self.skel_backend_combo = StyledComboBox()
        for key, code in (('backend_auto', 'auto'), ('skel_skimage', 'skimage'),
                          ('skel_medial', 'medial_axis'),
                          ('skel_zhang', 'zhang_suen')):
            self.skel_backend_combo.addItem(t(key), code)
        self.skel_backend_combo.setToolTip(t('tip_skel_backend'))
        self.kde_radius_spin = _dspin(1, 500, 5, 0, 50)
        self.kde_radius_spin.setToolTip(t('tip_kde_radius'))
        self.gap_buffer_spin = _dspin(0, 500, 5, 0, 30)
        self.gap_buffer_spin.setToolTip(t('tip_kde_buffer'))
        self.slide_close_spin = _dspin(0, 500, 5, 0, 0)
        self.slide_close_spin.setToolTip(t('tip_slide_close'))
        self._add_form_row(mform, 'method_label', self.method_combo)
        self._add_form_row(mform, 'ds_slide_backend', self.slide_backend_combo)
        self._add_form_row(mform, 'ds_skel_backend', self.skel_backend_combo)
        self._add_form_row(mform, 'kde_radius', self.kde_radius_spin)
        self._add_form_row(mform, 'kde_buffer', self.gap_buffer_spin)
        self._add_form_row(mform, 'ds_slide_close', self.slide_close_spin)
        layout.addWidget(self.method_group)
        self.method_combo.currentIndexChanged.connect(self._sync_method)

        self.group = QGroupBox()
        form = QFormLayout(self.group)

        self.cell_spin = _dspin(0.5, 50, 0.5, 1, 5)
        self.cell_spin.setToolTip(t('tip_cell'))
        self.sigma1_spin = _dspin(0, 30, 0.5, 1, 5)
        self.sigma1_spin.setToolTip(t('tip_sigma'))
        self.sigma2_spin = _dspin(0, 30, 0.5, 1, 3)
        self.sigma2_spin.setToolTip(t('tip_sigma2'))
        self.sharpness_spin = _dspin(0, 5, 0.1, 1, 1.5)
        self.sharpness_spin.setToolTip(t('tip_sharpness'))
        self._add_form_row(form, 'ds_cell', self.cell_spin)
        self._add_form_row(form, 'ds_sigma1', self.sigma1_spin)
        self._add_form_row(form, 'ds_sigma2', self.sigma2_spin)
        self._add_form_row(form, 'ds_sharpness', self.sharpness_spin)
        layout.addWidget(self.group)

        self.advanced_group = QGroupBox()
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        adv_form = QFormLayout(self.advanced_group)
        self.min_loops_spin = _ispin(0, 20000, 100)
        self.min_loops_spin.setToolTip(t('tip_slide_loops'))
        self.max_loops_spin = _ispin(1, 40000, 4000)
        self.max_loops_spin.setToolTip(t('tip_slide_loops'))
        self._add_form_row(adv_form, 'ds_min_loops', self.min_loops_spin)
        self._add_form_row(adv_form, 'ds_max_loops', self.max_loops_spin)
        layout.addWidget(self.advanced_group)
        self._sync_method()
        self.retranslateUi()

    def retranslateUi(self):
        self._retranslate_bound_widgets()
        t = translations.get_text
        self.method_group.setTitle(t('method_group'))
        self.group.setTitle(t('ds_group'))
        self.advanced_group.setTitle(t('ds_advanced'))
        retranslate_combo(
            self.method_combo, (('method_slide', 'slide'), ('method_kde', 'kde')))
        slide_backends = (('backend_auto', 'auto'), ('backend_numba', 'numba'),
                          ('backend_numpy', 'numpy'))
        skeletonizers = (('backend_auto', 'auto'), ('skel_skimage', 'skimage'),
                         ('skel_medial', 'medial_axis'), ('skel_zhang', 'zhang_suen'))
        retranslate_combo(self.slide_backend_combo, slide_backends)
        retranslate_combo(self.skel_backend_combo, skeletonizers)
        for widget, key in ((self.method_combo, 'tip_method'),
                            (self.slide_backend_combo, 'tip_slide_backend'),
                            (self.skel_backend_combo, 'tip_skel_backend'),
                            (self.kde_radius_spin, 'tip_kde_radius'),
                            (self.gap_buffer_spin, 'tip_kde_buffer'),
                            (self.slide_close_spin, 'tip_slide_close'),
                            (self.cell_spin, 'tip_cell'), (self.sigma1_spin, 'tip_sigma'),
                            (self.sigma2_spin, 'tip_sigma2'), (self.sharpness_spin, 'tip_sharpness'),
                            (self.min_loops_spin, 'tip_slide_loops'),
                            (self.max_loops_spin, 'tip_slide_loops')):
            widget.setToolTip(t(key))

    def current_method(self):
        return self.method_combo.currentData()

    def _sync_method(self):
        """Активировать поля, относящиеся к выбранному методу, и гасить чужие.

        KDE использует радиус/буфер; Slide — свой бэкенд, σ1/σ2, заострённость и
        число итераций. Нерелевантные поля становятся серыми, чтобы не путать.
        """
        is_kde = self.method_combo.currentData() == 'kde'
        # Поля только для KDE
        self.kde_radius_spin.setEnabled(is_kde)
        self.gap_buffer_spin.setEnabled(is_kde)
        # Поля только для Slide
        for w in (self.slide_backend_combo, self.sigma1_spin, self.sigma2_spin,
                  self.sharpness_spin, self.min_loops_spin, self.max_loops_spin,
                  self.slide_close_spin):
            w.setEnabled(not is_kde)

    def _set_combo(self, combo, code):
        idx = combo.findData(code)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def set_values(self, s):
        self._set_combo(self.method_combo, s.get('method', 'slide'))
        self._set_combo(self.slide_backend_combo, s.get('slide_backend', 'auto'))
        self._set_combo(self.skel_backend_combo, s.get('skeleton_backend', 'auto'))
        self.kde_radius_spin.setValue(float(s.get('kde_radius', 50.0)))
        self.gap_buffer_spin.setValue(float(s.get('gap_buffer_m', 30.0)))
        self.slide_close_spin.setValue(float(s.get('slide_close_gaps_m', 0.0)))
        self.cell_spin.setValue(float(s.get('cell_tau', 5.0)))
        self.sigma1_spin.setValue(float(s.get('sigma1', 5.0)))
        self.sigma2_spin.setValue(float(s.get('sigma2', 3.0)))
        self.sharpness_spin.setValue(float(s.get('sharpness', 1.5)))
        self.min_loops_spin.setValue(int(s.get('slide_min_loops', 100)))
        self.max_loops_spin.setValue(int(s.get('slide_max_loops', 4000)))
        self._sync_method()

    def get_values(self):
        return {
            'method': self.method_combo.currentData(),
            'slide_backend': self.slide_backend_combo.currentData(),
            'skeleton_backend': self.skel_backend_combo.currentData(),
            'kde_radius': self.kde_radius_spin.value(),
            'gap_buffer_m': self.gap_buffer_spin.value(),
            'slide_close_gaps_m': self.slide_close_spin.value(),
            'cell_tau': self.cell_spin.value(),
            'sigma1': self.sigma1_spin.value(),
            'sigma2': self.sigma2_spin.value(),
            'sharpness': self.sharpness_spin.value(),
            'slide_min_loops': self.min_loops_spin.value(),
            'slide_max_loops': self.max_loops_spin.value(),
        }


class GraphTab(RetranslatableMixin, QWidget):
    """Вкладка «Граф»."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_i18n()
        t = translations.get_text
        layout = QVBoxLayout(self)
        self.group = QGroupBox()
        form = QFormLayout(self.group)

        self.eps_mode_combo = StyledComboBox()
        for key, code in (('gr_eps_auto', 'otsu'), ('gr_eps_manual', 'manual'),
                          ('gr_eps_percentile', 'percentile'),
                          ('gr_eps_adaptive', 'adaptive')):
            self.eps_mode_combo.addItem(t(key), code)
        self.eps_mode_combo.setToolTip(t('tip_eps_mode'))
        self.eps_value_spin = _dspin(0, 1e6, 0.5, 3, 0)
        self.eps_value_spin.setToolTip(t('tip_eps_value'))
        self.eps_pct_spin = _dspin(0, 100, 1, 0, 80)
        self.eps_pct_spin.setToolTip(t('tip_eps_pct'))
        self.fill_holes_spin = _dspin(0, 100000, 5, 0, 0)
        self.fill_holes_spin.setToolTip(t('tip_fill_holes'))
        self.loop_min_spin = _dspin(0, 100000, 5, 0, 0)
        self.loop_min_spin.setToolTip(t('tip_loop_min'))
        self.dp_spin = _dspin(0, 50, 0.5, 1, 2)
        self.dp_spin.setToolTip(t('tip_dp'))
        self.fmin_spin = _ispin(1, 1000, 2)
        self.fmin_spin.setToolTip(t('tip_fmin'))
        self.lmin_spin = _dspin(0, 100000, 5, 0, 30)
        self.lmin_spin.setToolTip(t('tip_lmin'))
        self.spur_spin = _dspin(0, 100000, 5, 0, 0)
        self.spur_spin.setToolTip(t('tip_spur'))
        self.smooth_spin = _ispin(0, 8, 0)
        self.smooth_spin.setToolTip(t('tip_smooth'))
        self.protect_check = QCheckBox(t('gr_protect'))
        self.protect_check.setToolTip(t('tip_protect'))

        self._add_form_row(form, 'gr_eps_mode', self.eps_mode_combo)
        self._add_form_row(form, 'gr_eps_value', self.eps_value_spin)
        self._add_form_row(form, 'gr_eps_pct_value', self.eps_pct_spin)
        self._add_form_row(form, 'gr_dp', self.dp_spin)
        self._add_form_row(form, 'gr_fmin', self.fmin_spin)
        self._add_form_row(form, 'gr_lmin', self.lmin_spin)
        self._add_form_row(form, 'gr_spur', self.spur_spin)
        self._add_form_row(form, 'gr_fill_holes', self.fill_holes_spin)
        self._add_form_row(form, 'gr_loop_min', self.loop_min_spin)
        self._add_form_row(form, 'gr_smooth', self.smooth_spin)
        self._add_form_row(form, '', self.protect_check)
        layout.addWidget(self.group)

        self.eps_mode_combo.currentIndexChanged.connect(self._sync_eps)
        self._sync_eps()
        self.retranslateUi()

    def retranslateUi(self):
        self._retranslate_bound_widgets()
        t = translations.get_text
        self.group.setTitle(t('gr_group'))
        self.protect_check.setText(t('gr_protect'))
        retranslate_combo(
            self.eps_mode_combo, (('gr_eps_auto', 'otsu'), ('gr_eps_manual', 'manual'),
                                  ('gr_eps_percentile', 'percentile'), ('gr_eps_adaptive', 'adaptive')))
        for widget, key in ((self.eps_mode_combo, 'tip_eps_mode'),
                            (self.eps_value_spin, 'tip_eps_value'),
                            (self.eps_pct_spin, 'tip_eps_pct'), (self.fill_holes_spin, 'tip_fill_holes'),
                            (self.loop_min_spin, 'tip_loop_min'), (self.dp_spin, 'tip_dp'),
                            (self.fmin_spin, 'tip_fmin'), (self.lmin_spin, 'tip_lmin'),
                            (self.spur_spin, 'tip_spur'), (self.smooth_spin, 'tip_smooth'),
                            (self.protect_check, 'tip_protect')):
            widget.setToolTip(t(key))

    def _sync_eps(self):
        mode = self.eps_mode_combo.currentData()
        self.eps_value_spin.setEnabled(mode == 'manual')
        self.eps_pct_spin.setEnabled(mode == 'percentile')

    def set_values(self, s):
        idx = self.eps_mode_combo.findData(s.get('eps_mode', 'otsu'))
        if idx >= 0:
            self.eps_mode_combo.setCurrentIndex(idx)
        self.eps_value_spin.setValue(float(s.get('eps_value', 0.0)))
        self.eps_pct_spin.setValue(float(s.get('eps_percentile', 80.0)))
        self.dp_spin.setValue(float(s.get('dp_tolerance', 2.0)))
        self.fmin_spin.setValue(int(s.get('edge_f_min', 2)))
        self.lmin_spin.setValue(float(s.get('edge_l_min', 30.0)))
        self.spur_spin.setValue(float(s.get('spur_min_m', 0.0)))
        self.fill_holes_spin.setValue(float(s.get('fill_holes_m', 0.0)))
        self.loop_min_spin.setValue(float(s.get('loop_min_m', 0.0)))
        self.smooth_spin.setValue(int(s.get('smooth_iters', 0)))
        self.protect_check.setChecked(bool(s.get('protect_long_edges', True)))
        self._sync_eps()

    def get_values(self):
        return {
            'eps_mode': self.eps_mode_combo.currentData(),
            'eps_value': self.eps_value_spin.value(),
            'eps_percentile': self.eps_pct_spin.value(),
            'dp_tolerance': self.dp_spin.value(),
            'edge_f_min': self.fmin_spin.value(),
            'edge_l_min': self.lmin_spin.value(),
            'spur_min_m': self.spur_spin.value(),
            'fill_holes_m': self.fill_holes_spin.value(),
            'loop_min_m': self.loop_min_spin.value(),
            'smooth_iters': self.smooth_spin.value(),
            'protect_long_edges': self.protect_check.isChecked(),
        }


class ScaleTab(RetranslatableMixin, QWidget):
    """Вкладка «Масштаб» (split-and-merge)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_i18n()
        t = translations.get_text
        layout = QVBoxLayout(self)
        self.group = QGroupBox()
        form = QFormLayout(self.group)

        self.mode_combo = StyledComboBox()
        for key, code in (('sc_auto', 'auto'), ('sc_off', 'off'),
                          ('sc_forced', 'forced')):
            self.mode_combo.addItem(t(key), code)
        self.mode_combo.setToolTip(t('tip_sc_mode'))
        self.nx_spin = _ispin(1, 20, 2)
        self.nx_spin.setToolTip(t('tip_sc_grid'))
        self.ny_spin = _ispin(1, 20, 2)
        self.ny_spin.setToolTip(t('tip_sc_grid'))
        self.maxpoints_spin = _ispin(10000, 20000000, 400000)
        self.maxpoints_spin.setToolTip(t('tip_sc_maxpoints'))

        self._add_form_row(form, 'sc_mode', self.mode_combo)
        self._add_form_row(form, 'sc_nx', self.nx_spin)
        self._add_form_row(form, 'sc_ny', self.ny_spin)
        self._add_form_row(form, 'sc_maxpoints', self.maxpoints_spin)
        layout.addWidget(self.group)

        self.mode_combo.currentIndexChanged.connect(self._sync)
        self._sync()
        self.retranslateUi()

    def retranslateUi(self):
        self._retranslate_bound_widgets()
        t = translations.get_text
        self.group.setTitle(t('sc_group'))
        retranslate_combo(
            self.mode_combo, (('sc_auto', 'auto'), ('sc_off', 'off'), ('sc_forced', 'forced')))
        for widget, key in ((self.mode_combo, 'tip_sc_mode'), (self.nx_spin, 'tip_sc_grid'),
                            (self.ny_spin, 'tip_sc_grid'), (self.maxpoints_spin, 'tip_sc_maxpoints')):
            widget.setToolTip(t(key))

    def _sync(self):
        forced = self.mode_combo.currentData() == 'forced'
        self.nx_spin.setEnabled(forced)
        self.ny_spin.setEnabled(forced)

    def set_values(self, s):
        idx = self.mode_combo.findData(s.get('split_mode', 'auto'))
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self.maxpoints_spin.setValue(int(s.get('max_points_per_tile', 400000)))
        self._sync()

    def get_values(self):
        vals = {
            'split_mode': self.mode_combo.currentData(),
            'max_points_per_tile': self.maxpoints_spin.value(),
        }
        if self.mode_combo.currentData() == 'forced':
            vals['tile_grid'] = (self.nx_spin.value(), self.ny_spin.value())
        return vals


class PostprocessTab(RetranslatableMixin, QWidget):
    """Вкладка «Постобработка»: связность + доводка готового графа (§WS-Post)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_i18n()
        t = translations.get_text
        layout = QVBoxLayout(self)
        self.intro_label = create_info_label(t('pt_intro'))
        layout.addWidget(self.intro_label)

        self.conn_group = QGroupBox()
        form = QFormLayout(self.conn_group)
        self.connect_spin = _dspin(0, 100000, 5, 0, 0)
        self.connect_spin.setToolTip(t('tip_connect_gap'))
        self.bridge_facing_spin = _dspin(0, 1000000, 10, 0, 0)
        self.bridge_facing_spin.setToolTip(t('tip_bridge_facing'))
        self.stitch_spin = _dspin(0, 1000000, 50, 0, 0)
        self.stitch_spin.setToolTip(t('tip_stitch'))
        self.break_check = QCheckBox(t('pt_break'))
        self.break_check.setToolTip(t('tip_break'))
        self.junction_spin = _dspin(0, 100000, 5, 0, 0)
        self.junction_spin.setToolTip(t('tip_junction'))
        self.min_comp_spin = _dspin(0, 1000000, 50, 0, 0)
        self.min_comp_spin.setToolTip(t('tip_min_component'))
        self.keep_largest_check = QCheckBox(t('pt_keep_largest'))
        self.keep_largest_check.setToolTip(t('tip_keep_largest'))
        self._add_form_row(form, 'pt_connect_gap', self.connect_spin)
        self._add_form_row(form, 'pt_bridge_facing', self.bridge_facing_spin)
        self._add_form_row(form, 'pt_stitch', self.stitch_spin)
        self._add_form_row(form, '', self.break_check)
        self._add_form_row(form, 'pt_junction', self.junction_spin)
        self._add_form_row(form, 'pt_min_component', self.min_comp_spin)
        self._add_form_row(form, '', self.keep_largest_check)
        layout.addWidget(self.conn_group)

        self.apply_group = QGroupBox()
        aform = QFormLayout(self.apply_group)
        self.source_combo = StyledComboBox()
        self.source_combo.addItem(t('pt_source_last'), 'last')
        self.source_combo.addItem(t('pt_source_layer'), 'layer')
        self.layer_combo = StyledComboBox()
        self.apply_button = create_styled_button(t('pt_apply'), 'primary', '✨')
        self._add_form_row(aform, 'pt_source', self.source_combo)
        self._add_form_row(aform, 'pt_source_layer', self.layer_combo)
        self._add_form_row(aform, '', self.apply_button)
        layout.addWidget(self.apply_group)
        self.source_combo.currentIndexChanged.connect(self._sync_source)
        self._sync_source()
        self.retranslateUi()

    def retranslateUi(self):
        self._retranslate_bound_widgets()
        t = translations.get_text
        self.intro_label.setText(t('pt_intro'))
        self.conn_group.setTitle(t('pt_conn_group'))
        self.apply_group.setTitle(t('pt_apply_group'))
        self.break_check.setText(t('pt_break'))
        self.keep_largest_check.setText(t('pt_keep_largest'))
        self.apply_button.setText('✨ ' + t('pt_apply'))
        retranslate_combo(
            self.source_combo, (('pt_source_last', 'last'), ('pt_source_layer', 'layer')))
        for widget, key in ((self.connect_spin, 'tip_connect_gap'),
                            (self.bridge_facing_spin, 'tip_bridge_facing'),
                            (self.stitch_spin, 'tip_stitch'), (self.break_check, 'tip_break'),
                            (self.junction_spin, 'tip_junction'), (self.min_comp_spin, 'tip_min_component'),
                            (self.keep_largest_check, 'tip_keep_largest')):
            widget.setToolTip(t(key))

    def _sync_source(self):
        self.layer_combo.setEnabled(self.source_combo.currentData() == 'layer')

    def set_values(self, s):
        self.connect_spin.setValue(float(s.get('connect_gap_m', 0.0)))
        self.bridge_facing_spin.setValue(float(s.get('bridge_facing_m', 0.0)))
        self.stitch_spin.setValue(float(s.get('stitch_max_m', 0.0)))
        self.break_check.setChecked(bool(s.get('break_crossings', False)))
        self.junction_spin.setValue(float(s.get('junction_m', 0.0)))
        self.min_comp_spin.setValue(float(s.get('min_component_m', 0.0)))
        self.keep_largest_check.setChecked(bool(s.get('keep_largest', False)))

    def get_values(self):
        return {
            'connect_gap_m': self.connect_spin.value(),
            'bridge_facing_m': self.bridge_facing_spin.value(),
            'stitch_max_m': self.stitch_spin.value(),
            'break_crossings': self.break_check.isChecked(),
            'junction_m': self.junction_spin.value(),
            'min_component_m': self.min_comp_spin.value(),
            'keep_largest': self.keep_largest_check.isChecked(),
        }


class OutputTab(RetranslatableMixin, QWidget):
    """Вкладка «Вывод»."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_i18n()
        t = translations.get_text
        layout = QVBoxLayout(self)
        self.group = QGroupBox()
        form = QFormLayout(self.group)

        self.crs_line = QLineEdit('EPSG:4326')
        self.layer_name_line = QLineEdit(t('default_layer_name'))
        self.add_layer_check = QCheckBox(t('out_add_layer'))
        self.add_layer_check.setChecked(True)
        self.style_freq_check = QCheckBox(t('out_style_freq'))
        self.style_freq_check.setChecked(True)

        self._add_form_row(form, 'out_crs', self.crs_line)
        self._add_form_row(form, 'out_layer_name', self.layer_name_line)
        self._add_form_row(form, '', self.add_layer_check)
        self._add_form_row(form, '', self.style_freq_check)
        layout.addWidget(self.group)

        self.export_group = QGroupBox()
        eform = QFormLayout(self.export_group)
        self.export_format_combo = StyledComboBox()
        for key, code in (('out_export_none', 'none'),
                          ('out_export_geojson', 'geojson'),
                          ('out_export_graphml', 'graphml'),
                          ('out_export_gpkg', 'gpkg'),
                          ('out_export_shp', 'shp')):
            self.export_format_combo.addItem(t(key), code)
        path_row = QHBoxLayout()
        self.export_path_line = QLineEdit()
        self.export_browse_button = create_styled_button(
            t('out_export_browse'), 'secondary', '📂')
        path_row.addWidget(self.export_path_line, 1)
        path_row.addWidget(self.export_browse_button)
        self._add_form_row(eform, 'out_export_format', self.export_format_combo)
        self._add_form_row(eform, 'out_export_path', path_row)
        layout.addWidget(self.export_group)

        # Промежуточные результаты / чекпоинты (§WS-D/F)
        self.cache_group = QGroupBox()
        cform = QFormLayout(self.cache_group)
        cache_row = QHBoxLayout()
        self.cache_line = QLineEdit()
        self.cache_line.setToolTip(t('tip_cache'))
        self.cache_browse_button = create_styled_button(
            t('out_export_browse'), 'secondary', '📂')
        cache_row.addWidget(self.cache_line, 1)
        cache_row.addWidget(self.cache_browse_button)
        self.start_stage_combo = StyledComboBox()
        for key, code in (('stage_none', ''), ('stage_points', 'points'),
                          ('stage_tracks', 'tracks')):
            self.start_stage_combo.addItem(t(key), code)
        self.stop_after_combo = StyledComboBox()
        for key, code in (('stage_none', ''), ('stage_points', 'points'),
                          ('stage_tracks', 'tracks')):
            self.stop_after_combo.addItem(t(key), code)
        self._add_form_row(cform, 'cache_dir', cache_row)
        self._add_form_row(cform, 'cache_start', self.start_stage_combo)
        self._add_form_row(cform, 'cache_stop', self.stop_after_combo)
        layout.addWidget(self.cache_group)
        self.retranslateUi()

    def retranslateUi(self):
        self._retranslate_bound_widgets()
        t = translations.get_text
        self.group.setTitle(t('out_group'))
        self.export_group.setTitle(t('out_export_group'))
        self.cache_group.setTitle(t('cache_group'))
        self.add_layer_check.setText(t('out_add_layer'))
        self.style_freq_check.setText(t('out_style_freq'))
        self.export_browse_button.setText('📂 ' + t('out_export_browse'))
        self.cache_browse_button.setText('📂 ' + t('out_export_browse'))
        self.cache_line.setToolTip(t('tip_cache'))
        retranslate_combo(
            self.export_format_combo, (('out_export_none', 'none'),
                                       ('out_export_geojson', 'geojson'), ('out_export_graphml', 'graphml'),
                                       ('out_export_gpkg', 'gpkg'), ('out_export_shp', 'shp')))
        stages = (('stage_none', ''), ('stage_points', 'points'), ('stage_tracks', 'tracks'))
        retranslate_combo(self.start_stage_combo, stages)
        retranslate_combo(self.stop_after_combo, stages)

    def set_values(self, s):
        self.crs_line.setText(str(s.get('output_crs', 'EPSG:4326')))
        self.cache_line.setText(str(s.get('cache_dir', '') or ''))

    def get_values(self):
        return {
            'output_crs': self.crs_line.text().strip() or 'EPSG:4326',
            'add_layer': self.add_layer_check.isChecked(),
            'style_freq': self.style_freq_check.isChecked(),
            'layer_name': self.layer_name_line.text().strip()
            or translations.get_text('default_layer_name'),
            'export_format': self.export_format_combo.currentData(),
            'export_path': self.export_path_line.text().strip(),
            'cache_dir': self.cache_line.text().strip(),
            'start_stage': self.start_stage_combo.currentData(),
            'stop_after': self.stop_after_combo.currentData(),
        }
