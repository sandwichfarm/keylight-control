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
        l.addStretch(1)
        return w

    def _build_features_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        show_sync = QCheckBox("Show sync controls")
        show_sync.setChecked(bool(self.prefs.get("features.show_sync_buttons", True)))
        show_sync.toggled.connect(lambda v: self.prefs.set("features.show_sync_buttons", bool(v)))
        l.addWidget(show_sync)
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
        l.addStretch(1)
        return w

