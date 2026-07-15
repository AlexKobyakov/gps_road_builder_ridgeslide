# -*- coding: utf-8 -*-
"""
Main dialog for GPS Road Builder (tabbed, wired to the pipeline).
Главное окно: шапка + пресеты + вкладки этапов + кнопки управления + результаты
(логи, таблица, обзор с гистограммами). Дизайн — по образцу garmin_export.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

from datetime import datetime

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QScrollArea, QWidget,
    QTabWidget, QTabBar, QFrame, QLabel, QComboBox
)

from .gui_components import (
    ModernProgressBar, apply_global_styles, create_styled_button)
from .gui_widgets import (
    HeaderWidget, ControlButtonsWidget, LogTextWidget, ResultsTableWidget,
    DependenciesWidget)
from .tabs import (
    DataTab, PreprocessTab, DensitySlideTab, GraphTab, ScaleTab, OutputTab,
    PostprocessTab)
from .histogram import HistogramWidget
from .gui_handlers import GuiEventHandlers
from ..translation_manager import translations


class RobustTabBar(QTabBar):
    """Панель вкладок с запасом ширины на вкладку — чтобы последняя буква/символ
    никогда не обрезались независимо от рендера шрифта или эмодзи-иконки
    (ADD4 п.7, окончательный структурный фикс)."""

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        size.setWidth(size.width() + 10)
        return size


class GpsRoadBuilderDialog(QDialog):
    """Главное диалоговое окно плагина."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._applySavedLanguage()
        self.setupWindow()
        self.setupUi()
        self.handlers = GuiEventHandlers(self)
        self.connectSignals()
        self.setStyleSheet(apply_global_styles())
        self.retranslateUi()
        self.handlers.load_settings()
        self.handlers.refreshLayerCombos()
        self.log_message('✅ ' + translations.get_text('log_ready'))

    def _applySavedLanguage(self):
        try:
            from ..core.settings_manager import SettingsManager
            saved = SettingsManager().get('language')
            if saved:
                translations.set_language(saved)
        except Exception:
            pass

    def setupWindow(self):
        self.setWindowTitle('🛰️ ' + translations.get_text('window_title'))
        self.setMinimumSize(1040, 780)
        self.resize(1240, 900)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
            | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

    def setupUi(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        self.header = HeaderWidget()
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        self._createSettingsArea()
        self._createControlButtonsArea()
        self._createResultsArea()
        self.main_splitter.addWidget(self.settings_area)
        self.main_splitter.addWidget(self.control_buttons_area)
        self.main_splitter.addWidget(self.results_area)
        self.main_splitter.setSizes([500, 80, 260])

        main_layout.addWidget(self.header)
        main_layout.addWidget(self.main_splitter, 1)

    def _createPresetRow(self):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 0, 4, 0)
        self.preset_label = QLabel(translations.get_text('preset_label'))
        self.preset_combo = QComboBox()
        from ..core.presets import PRESET_ORDER
        for name in PRESET_ORDER:
            self.preset_combo.addItem(
                translations.get_text('preset_' + name), name)
        self.preset_apply_button = create_styled_button(
            translations.get_text('preset_apply'), 'secondary', '🎛️')
        self.preset_save_button = create_styled_button(
            translations.get_text('preset_save'), 'secondary', '💾')
        self.preset_load_button = create_styled_button(
            translations.get_text('preset_load'), 'secondary', '📂')
        layout.addWidget(self.preset_label)
        layout.addWidget(self.preset_combo, 1)
        layout.addWidget(self.preset_apply_button)
        layout.addWidget(self.preset_save_button)
        layout.addWidget(self.preset_load_button)
        return row

    def _createSettingsArea(self):
        # Панель вкладок НЕ заворачиваем во внешний скролл — иначе бар вкладок
        # уезжает при прокрутке (жалоба). Прокрутка — ВНУТРИ каждой вкладки
        # (см. _wrap), бар вкладок остаётся зафиксированным (§WS-U).
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)

        layout.addWidget(self._createPresetRow())

        self.settings_tabs = QTabWidget()
        self.settings_tabs.setTabBar(RobustTabBar())
        self.settings_tabs.setStyleSheet(self._tabStyle())
        # Не обрезать названия вкладок: показывать полностью, при нехватке ширины
        # — стрелки прокрутки бара (а не «...»).
        self.settings_tabs.tabBar().setElideMode(Qt.ElideNone)
        self.settings_tabs.setUsesScrollButtons(True)
        self.data_tab = DataTab()
        self.preprocess_tab = PreprocessTab()
        self.density_tab = DensitySlideTab()
        self.graph_tab = GraphTab()
        self.scale_tab = ScaleTab()
        self.postprocess_tab = PostprocessTab()
        self.output_tab = OutputTab()
        self.deps_widget = DependenciesWidget()

        for icon, widget in (
                ('📁', self.data_tab), ('🧹', self.preprocess_tab),
                ('🌫️', self.density_tab), ('🕸️', self.graph_tab),
                ('🧩', self.scale_tab), ('🛠️', self.postprocess_tab),
                ('📦', self.output_tab), ('⬇️', self.deps_widget)):
            self.settings_tabs.addTab(self._wrap(widget), icon)

        layout.addWidget(self.settings_tabs, 1)
        self.settings_area = container

    def _createControlButtonsArea(self):
        self.control_buttons_area = QFrame()
        self.control_buttons_area.setFixedHeight(80)
        self.control_buttons_area.setStyleSheet(
            'QFrame { background-color: #f8f9fa; '
            'border-top: 2px solid #e9ecef; border-bottom: 2px solid #e9ecef; }')
        layout = QHBoxLayout(self.control_buttons_area)
        layout.setContentsMargins(20, 15, 20, 15)
        self.control_buttons = ControlButtonsWidget()
        self.control_buttons.build_button.setEnabled(True)
        layout.addWidget(self.control_buttons)

    def _createResultsArea(self):
        self.results_area = QWidget()
        layout = QVBoxLayout(self.results_area)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.progress_label = QLabel('📊 ' + translations.get_text('progress'))
        self.progress_label.setStyleSheet('font-weight: bold; color: #2c3e50;')
        self.progress_bar = ModernProgressBar()
        self.progress_bar.setVisible(False)

        self.results_tabs = QTabWidget()
        self.results_tabs.setStyleSheet(self._tabStyle(results=True))
        self.log_text = LogTextWidget()
        self.results_table = ResultsTableWidget()
        self.overview = self._createOverview()
        self.results_tabs.addTab(self.log_text, '📋')
        self.results_tabs.addTab(self.results_table, '📈')
        self.results_tabs.addTab(self.overview, '📊')

        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.results_tabs, 1)

    def _createOverview(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.stats_label = QLabel('—')
        self.stats_label.setStyleSheet('color: #2c3e50;')
        hist_row = QHBoxLayout()
        self.hist_frequency = HistogramWidget(
            translations.get_text('hist_frequency_title'))
        self.hist_length = HistogramWidget(
            translations.get_text('hist_length_title'))
        hist_row.addWidget(self.hist_frequency)
        hist_row.addWidget(self.hist_length)
        layout.addWidget(self.stats_label)
        layout.addLayout(hist_row, 1)
        return widget

    def _wrap(self, widget):
        # Контент вкладки — в собственном скролле, чтобы длинные вкладки
        # прокручивались, а бар вкладок оставался на месте (§WS-U).
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(widget)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(inner)
        return scroll

    @staticmethod
    def _tabStyle(results=False):
        pane_bg = 'white' if results else '#f8f9fa'
        sel_bg = 'white' if results else '#3498db'
        sel_fg = '#2c3e50' if results else 'white'
        return (
            'QTabWidget::pane { border: 2px solid #bdc3c7; border-radius: 8px; '
            'background-color: %s; }'
            # Обычный (не жирный) шрифт: жирный шире, и Qt обрезал последнюю
            # букву активной вкладки; выделение — только цветом фона/текста
            # (ADD4 п.7 — откат «фикса» Спринта 8). Запас ширины даёт padding
            # и RobustTabBar.tabSizeHint (см. gui_main).
            'QTabBar::tab { background: #ecf0f1; border: 1px solid #bdc3c7; '
            'padding: 8px 18px; margin-right: 2px; border-top-left-radius: 6px; '
            'border-top-right-radius: 6px; min-width: 40px; }'
            'QTabBar::tab:selected { background: %s; color: %s; }'
            'QTabBar::tab:hover:!selected { background: #d5dbdb; }'
            % (pane_bg, sel_bg, sel_fg))

    # ------------------------------------------------------------------
    # Значения вкладок
    # ------------------------------------------------------------------

    def collect_values(self):
        """Собрать значения всех вкладок в один словарь."""
        values = {}
        for tab in (self.data_tab, self.preprocess_tab, self.density_tab,
                    self.graph_tab, self.scale_tab, self.postprocess_tab,
                    self.output_tab):
            values.update(tab.get_values())
        return values

    def apply_values(self, s):
        """Разложить настройки по вкладкам."""
        for tab in (self.data_tab, self.preprocess_tab, self.density_tab,
                    self.graph_tab, self.scale_tab, self.postprocess_tab,
                    self.output_tab):
            tab.set_values(s)
        self._syncMethodDependentTabs()

    def _syncMethodDependentTabs(self):
        """Согласовать поля разных вкладок с выбранным методом (Slide/KDE).

        Вкладка «Плотность/Slide» гасит свои поля сама; здесь распространяем
        состояние метода на «Предобработку» (ресэмпл не нужен для KDE).
        """
        is_kde = self.density_tab.current_method() == 'kde'
        self.preprocess_tab.apply_method(is_kde)

    # ------------------------------------------------------------------
    # Сигналы и локализация
    # ------------------------------------------------------------------

    def connectSignals(self):
        self.header.language_combo.currentIndexChanged.connect(
            self.handlers.onLanguageChanged)
        self.header.donation_button.clicked.connect(self.handlers.showDonation)
        self.header.author_button.clicked.connect(self.handlers.showAuthorInfo)
        self.preset_apply_button.clicked.connect(self.handlers.applyPreset)
        self.preset_save_button.clicked.connect(self.handlers.savePreset)
        self.preset_load_button.clicked.connect(self.handlers.loadPreset)
        self.density_tab.method_combo.currentIndexChanged.connect(
            self._syncMethodDependentTabs)
        self.output_tab.cache_browse_button.clicked.connect(
            self.handlers.browseCache)
        self.data_tab.browse_button.clicked.connect(self.handlers.browseFolder)
        self.data_tab.scan_button.clicked.connect(self.handlers.scanFolder)
        self.data_tab.aoi_browse_button.clicked.connect(self.handlers.browseAoi)
        self.data_tab.vfile_browse_button.clicked.connect(self.handlers.browseVfile)
        self.data_tab.source_combo.currentIndexChanged.connect(
            self.handlers.refreshLayerCombos)
        self.postprocess_tab.apply_button.clicked.connect(
            self.handlers.applyPostprocess)
        self.postprocess_tab.source_combo.currentIndexChanged.connect(
            self.handlers.refreshLayerCombos)
        self.data_tab.aoi_source_combo.currentIndexChanged.connect(
            self.handlers.refreshLayerCombos)
        self.output_tab.export_browse_button.clicked.connect(
            self.handlers.browseExport)
        self.control_buttons.build_button.clicked.connect(self.handlers.build)
        self.control_buttons.test_button.clicked.connect(self.handlers.build)
        self.control_buttons.cancel_button.clicked.connect(self.handlers.cancel)
        self.control_buttons.clear_log_button.clicked.connect(
            self.handlers.clearLogs)
        self.deps_widget.install_button.clicked.connect(
            self.handlers.installDependencies)
        self.deps_widget.recheck_button.clicked.connect(
            self.handlers.recheckDependencies)

    def retranslateUi(self):
        t = translations.get_text
        self.setWindowTitle('🛰️ ' + t('window_title'))
        self.header.donation_button.setText('☕ ' + t('header_support'))
        self.header.author_button.setText('👤 ' + t('header_about_author'))
        self.preset_label.setText(t('preset_label'))
        self.preset_apply_button.setText('🎛️ ' + t('preset_apply'))
        self.preset_save_button.setText('💾 ' + t('preset_save'))
        self.preset_load_button.setText('📂 ' + t('preset_load'))
        tabs = [(0, '📁', 'tab_data'), (1, '🧹', 'tab_preprocess'),
                (2, '🌫️', 'tab_density'), (3, '🕸️', 'tab_graph'),
                (4, '🧩', 'tab_scale'), (5, '🛠️', 'tab_postprocess'),
                (6, '📦', 'tab_output'), (7, '⬇️', 'tab_deps')]
        for idx, icon, key in tabs:
            self.settings_tabs.setTabText(idx, '{0} {1}'.format(icon, t(key)))
            self.settings_tabs.setTabToolTip(idx, t(key))
        self.control_buttons.build_button.setText('🚀 ' + t('build_graph'))
        self.control_buttons.test_button.setText('🧪 ' + t('test_run'))
        self.control_buttons.cancel_button.setText('❌ ' + t('cancel'))
        self.control_buttons.clear_log_button.setText('🧹 ' + t('clear_logs'))
        self.progress_label.setText('📊 ' + t('progress'))
        self.results_tabs.setTabText(0, '📋 ' + t('logs'))
        self.results_tabs.setTabText(1, '📈 ' + t('results'))
        self.results_tabs.setTabText(2, '📊 ' + t('tab_overview'))

    # ------------------------------------------------------------------
    # Лог
    # ------------------------------------------------------------------

    def log_message(self, message):
        stamp = datetime.now().strftime('%H:%M:%S')
        if message.startswith(('🚀', '🎉', '✅')):
            color = '#27ae60'
        elif message.startswith('⚠️'):
            color = '#f39c12'
        elif message.startswith(('🔥', '❌')):
            color = '#e74c3c'
        elif message.startswith(('📊', '📁', '📥', '🔄')):
            color = '#3498db'
        else:
            color = '#2c3e50'
        self.log_text.append(
            '<span style="color:#95a5a6;">[{0}]</span> '
            '<span style="color:{1};">{2}</span>'.format(stamp, color, message))
