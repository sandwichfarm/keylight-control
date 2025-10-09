from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QCheckBox,
    QDialogButtonBox,
    QLabel,
    QSpinBox,
    QComboBox,
)

from core.preferences import PreferencesService


class SettingsDialog(QDialog):
    def __init__(self, prefs: PreferencesService, parent=None) -> None:
        super().__init__(parent)
        self.prefs = prefs
        self.setWindowTitle("Preferences")
        self.resize(520, 360)

        root = QVBoxLayout(self)
        tabs = QTabWidget()
        root.addWidget(tabs)

        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_features_tab(), "Features")
        tabs.addTab(self._build_performance_tab(), "Performance")
        tabs.addTab(self._build_advanced_tab(), "Advanced")

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.Close).setText("Close")
        root.addWidget(buttons)

    # --- tabs ---
    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        hide_on_esc = QCheckBox("Hide window on Escape")
        hide_on_esc.setChecked(bool(self.prefs.get("general.hide_on_esc", True)))
        hide_on_esc.toggled.connect(lambda v: self.prefs.set("general.hide_on_esc", bool(v)))
        l.addWidget(hide_on_esc)

        tray_enabled = QCheckBox("Enable tray icon")
        tray_enabled.setChecked(bool(self.prefs.get("general.tray_icon_enabled", True)))
        tray_enabled.toggled.connect(lambda v: self.prefs.set("general.tray_icon_enabled", bool(v)))
        l.addWidget(tray_enabled)

        show_master_default = QCheckBox("Show master device control by default")
        show_master_default.setChecked(bool(self.prefs.get("general.show_master_device_default", False)))
        show_master_default.toggled.connect(lambda v: self.prefs.set("general.show_master_device_default", bool(v)))
        l.addWidget(show_master_default)

        show_sync_default = QCheckBox("Show sync controls by default")
        show_sync_default.setChecked(bool(self.prefs.get("general.show_sync_controls_default", False)))
        show_sync_default.toggled.connect(lambda v: self.prefs.set("general.show_sync_controls_default", bool(v)))
        l.addWidget(show_sync_default)
        l.addStretch(1)
        return w

    def _build_features_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        show_sync = QCheckBox("Show sync controls")
        show_sync.setChecked(bool(self.prefs.get("features.show_sync_buttons", True)))
        show_sync.toggled.connect(lambda v: self.prefs.set("features.show_sync_buttons", bool(v)))
        l.addWidget(show_sync)

        show_master_control = QCheckBox("Enable master device control feature")
        show_master_control.setChecked(bool(self.prefs.get("features.show_master_device_control", True)))
        show_master_control.toggled.connect(lambda v: self.prefs.set("features.show_master_device_control", bool(v)))
        l.addWidget(show_master_control)

        show_rename = QCheckBox("Show Rename Device action")
        show_rename.setChecked(bool(self.prefs.get("features.show_rename_action", True)))
        show_rename.toggled.connect(lambda v: self.prefs.set("features.show_rename_action", bool(v)))
        l.addWidget(show_rename)

        enable_discovery = QCheckBox("Enable device discovery")
        enable_discovery.setChecked(bool(self.prefs.get("features.enable_discovery", True)))
        enable_discovery.toggled.connect(lambda v: self.prefs.set("features.enable_discovery", bool(v)))
        l.addWidget(enable_discovery)

        enable_auto_sync = QCheckBox("Enable live sync while adjusting")
        enable_auto_sync.setChecked(bool(self.prefs.get("features.enable_auto_sync", True)))
        enable_auto_sync.toggled.connect(lambda v: self.prefs.set("features.enable_auto_sync", bool(v)))
        l.addWidget(enable_auto_sync)

        enable_shortcuts = QCheckBox("Enable keyboard shortcuts")
        enable_shortcuts.setChecked(bool(self.prefs.get("features.enable_keyboard_shortcuts", True)))
        enable_shortcuts.toggled.connect(lambda v: self.prefs.set("features.enable_keyboard_shortcuts", bool(v)))
        l.addWidget(enable_shortcuts)
        l.addStretch(1)
        return w

    def _build_performance_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("Widget update interval (ms)"))
        interval = QSpinBox()
        interval.setRange(10, 2000)
        interval.setSingleStep(10)
        interval.setValue(int(self.prefs.get("perf.widget_update_interval_ms", 50)))
        interval.valueChanged.connect(lambda v: self.prefs.set("perf.widget_update_interval_ms", int(v)))
        l.addWidget(interval)

        l.addWidget(QLabel("Minimum device update spacing (ms)"))
        minspace = QSpinBox()
        minspace.setRange(0, 1000)
        minspace.setSingleStep(10)
        minspace.setValue(int(self.prefs.get("perf.widget_min_update_spacing_ms", 100)))
        minspace.valueChanged.connect(lambda v: self.prefs.set("perf.widget_min_update_spacing_ms", int(v)))
        l.addWidget(minspace)

        l.addWidget(QLabel("Sync batch interval (ms)"))
        syncint = QSpinBox()
        syncint.setRange(50, 2000)
        syncint.setSingleStep(50)
        syncint.setValue(int(self.prefs.get("perf.sync_timer_interval_ms", 300)))
        syncint.valueChanged.connect(lambda v: self.prefs.set("perf.sync_timer_interval_ms", int(v)))
        l.addWidget(syncint)

        l.addWidget(QLabel("HTTP request timeout (s)"))
        http_to = QSpinBox()
        http_to.setRange(1, 30)
        http_to.setSingleStep(1)
        http_to.setValue(int(self.prefs.get("perf.http_timeout_s", 2)))
        http_to.valueChanged.connect(lambda v: self.prefs.set("perf.http_timeout_s", int(v)))
        l.addWidget(http_to)
        l.addStretch(1)
        return w

    def _build_advanced_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("Master power semantics"))
        combo = QComboBox()
        combo.addItem("Any device on => Master ON", "AnyOn")
        combo.addItem("All devices on => Master ON (else OFF)", "AllOn")
        current = str(self.prefs.get("advanced.master_power_semantics", "AnyOn"))
        idx = combo.findData(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(lambda _i: self.prefs.set("advanced.master_power_semantics", combo.currentData()))
        l.addWidget(combo)

        debug_log = QCheckBox("Enable debug logging")
        debug_log.setChecked(bool(self.prefs.get("advanced.enable_debug_logging", False)))
        debug_log.toggled.connect(lambda v: self.prefs.set("advanced.enable_debug_logging", bool(v)))
        l.addWidget(debug_log)
        l.addStretch(1)
        return w
