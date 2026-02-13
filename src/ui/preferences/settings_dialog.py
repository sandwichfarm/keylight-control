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
        self._tabs = QTabWidget()
        root.addWidget(self._tabs)

        self._tabs.addTab(self._build_general_tab(), "General")
        self._tabs.addTab(self._build_features_tab(), "Features")
        self._tabs.addTab(self._build_performance_tab(), "Performance")
        self._tabs.addTab(self._build_advanced_tab(), "Advanced")

        # Reset buttons row
        from PySide6.QtWidgets import QPushButton
        reset_row = QHBoxLayout()
        self.reset_tab_btn = QPushButton("Reset This Tab")
        self.reset_all_btn = QPushButton("Reset All")
        self.reset_tab_btn.clicked.connect(self._reset_current_tab)
        self.reset_all_btn.clicked.connect(self._reset_all)
        reset_row.addStretch(1)
        reset_row.addWidget(self.reset_tab_btn)
        reset_row.addWidget(self.reset_all_btn)
        root.addLayout(reset_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.Close).setText("Close")
        root.addWidget(buttons)

    # --- resets ---
    def _reset_current_tab(self):
        idx = self._tabs.currentIndex()
        prefix = "general."
        if idx == 0:
            prefix = "general."
        elif idx == 1:
            prefix = "features."
        elif idx == 2:
            prefix = "perf."
        elif idx == 3:
            prefix = "advanced."
        self.prefs.reset_section(prefix)

    def _reset_all(self):
        self.prefs.reset_to_defaults()

    # --- tabs ---
    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        launch_minimized = QCheckBox("Launch minimized to tray")
        launch_minimized.setChecked(bool(self.prefs.get("general.launch_minimized", False)))
        launch_minimized.toggled.connect(lambda v: self.prefs.set("general.launch_minimized", bool(v)))
        l.addWidget(launch_minimized)

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

        hide_on_disc_off = QCheckBox("Hide devices when discovery disabled")
        hide_on_disc_off.setChecked(bool(self.prefs.get("features.hide_devices_when_discovery_disabled", False)))
        hide_on_disc_off.toggled.connect(lambda v: self.prefs.set("features.hide_devices_when_discovery_disabled", bool(v)))
        l.addWidget(hide_on_disc_off)

        dim_on_disc_off = QCheckBox("Dim (disable) devices when discovery disabled")
        dim_on_disc_off.setChecked(bool(self.prefs.get("features.dim_devices_when_discovery_disabled", True)))
        dim_on_disc_off.toggled.connect(lambda v: self.prefs.set("features.dim_devices_when_discovery_disabled", bool(v)))
        l.addWidget(dim_on_disc_off)

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
        combo.addItem("Any device ON ⇒ Master ON (click: turn ONs OFF)", "AnyOn")
        combo.addItem("Any device OFF ⇒ Master OFF (click: turn OFFs ON)", "AnyOff")
        current = str(self.prefs.get("advanced.master_power_semantics", "AnyOn"))
        # Backward compat for earlier value
        if current == "AllOn":
            current = "AnyOff"
        idx = combo.findData(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(lambda _i: self.prefs.set("advanced.master_power_semantics", combo.currentData()))
        l.addWidget(combo)

        debug_log = QCheckBox("Enable debug logging")
        debug_log.setChecked(bool(self.prefs.get("advanced.enable_debug_logging", False)))
        debug_log.toggled.connect(lambda v: self.prefs.set("advanced.enable_debug_logging", bool(v)))
        l.addWidget(debug_log)

        # --- Local API section ---
        l.addWidget(QLabel(""))  # spacer
        l.addWidget(QLabel("Local API"))

        api_enabled = QCheckBox("Enable local API")
        api_enabled.setChecked(bool(self.prefs.get("advanced.api_enabled", True)))
        api_enabled.toggled.connect(lambda v: self.prefs.set("advanced.api_enabled", bool(v)))
        l.addWidget(api_enabled)

        api_unix = QCheckBox("Unix socket transport")
        api_unix.setChecked(bool(self.prefs.get("advanced.api_unix_socket", True)))
        api_unix.toggled.connect(lambda v: self.prefs.set("advanced.api_unix_socket", bool(v)))
        l.addWidget(api_unix)

        api_http = QCheckBox("HTTP transport (localhost only)")
        api_http.setChecked(bool(self.prefs.get("advanced.api_http", False)))
        api_http.toggled.connect(lambda v: self.prefs.set("advanced.api_http", bool(v)))
        l.addWidget(api_http)

        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("HTTP port"))
        api_port = QSpinBox()
        api_port.setRange(1024, 65535)
        api_port.setValue(int(self.prefs.get("advanced.api_http_port", 27301)))
        api_port.valueChanged.connect(lambda v: self.prefs.set("advanced.api_http_port", int(v)))
        port_row.addWidget(api_port)
        l.addLayout(port_row)

        l.addStretch(1)
        return w
