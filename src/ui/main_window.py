from __future__ import annotations

import asyncio
import sys
import socket

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QPushButton,
    QLabel,
    QScrollArea,
    QSystemTrayIcon,
    QGraphicsBlurEffect,
)
from PySide6.QtWidgets import QMenu  # kept for type hints elsewhere if needed
from utils.system_tray import create_tray_icon

from config import DeviceConfig
from core.models import KeyLight
from core.discovery import KeyLightDiscovery
from core.service import KeyLightService
from core.preferences import PreferencesService
from ui.widgets.master_widget import MasterDeviceWidget
from ui.widgets.keylight_widget import KeyLightWidget
from ui.preferences.settings_dialog import SettingsDialog


class KeyLightController(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.keylights = []
        self.keylight_widgets = []
        self.device_config = DeviceConfig()
        self.discovery = KeyLightDiscovery()
        self.service = KeyLightService()
        self.prefs = PreferencesService(self.device_config)
        self.master_device_widget = None  # Will be created in setup_ui
        self.setup_ui()
        self.apply_dark_theme()
        self.setup_system_tray()

        # Connect discovery signals
        self.discovery.device_found.connect(self.add_keylight)
        self.discovery.mac_fetch_requested.connect(self.fetch_device_mac)

        # Start discovery
        self.discovery.start_discovery()

        # Add keyboard shortcuts
        self.setup_shortcuts()

        # Apply preferences on startup and subscribe to changes
        self._apply_all_preferences()
        self.prefs.setting_changed.connect(self._on_setting_changed)

    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("Key Light Control")
        self.setFixedWidth(400)
        self.setMinimumHeight(200)

        # Screen geom for dynamic sizing
        screen = self.screen() or self.windowHandle().screen()
        screen_geometry = screen.geometry() if screen else None
        self.max_height = int(screen_geometry.height() * 0.75) if screen_geometry else 800
        self.widget_height = 140

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Master controls row inside a container that provides L/T/R margins only
        self.setup_master_controls()
        self.master_row_container = QWidget()
        master_row_layout = QHBoxLayout(self.master_row_container)
        master_row_layout.setContentsMargins(8, 8, 8, 0)  # left, top, right; no bottom
        master_row_layout.setSpacing(0)
        master_row_layout.addWidget(self.master_panel)
        main_layout.addWidget(self.master_row_container)

        # Scroll area for devices
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Device container
        self.devices_container = QWidget()
        self.devices_container.setStyleSheet("background-color: #1a1a1a;")
        self.devices_layout = QVBoxLayout(self.devices_container)
        self.devices_layout.setContentsMargins(8, 8, 8, 8)
        self.devices_layout.setSpacing(8)

        # Master device widget (hidden by default)
        self.master_device_widget = MasterDeviceWidget(self)
        ignore_locks = self.device_config.get_app_setting("master_ignore_locks", True)
        self.master_device_widget.ignore_locks = ignore_locks
        master_device_visible = self.device_config.get_app_setting("master_device_visible", False)
        self.master_device_widget.setVisible(master_device_visible)
        self.devices_layout.addWidget(self.master_device_widget)

        self.update_master_device_toggle_appearance()
        self.update_device_controls_for_master_state(master_device_visible)

        self.scroll_area.setWidget(self.devices_container)
        main_layout.addWidget(self.scroll_area)

    def setup_master_controls(self):
        self.master_panel = QFrame()
        self.master_panel.setObjectName("MasterPanel")
        # Slightly thinner top bar
        self.master_panel.setFixedHeight(56)

        master_layout = QHBoxLayout(self.master_panel)
        # Reduce internal padding for a tighter bar
        master_layout.setContentsMargins(8, 4, 8, 4)
        master_layout.setSpacing(8)

        self.master_power_button = QPushButton("⏻")
        self.master_power_button.setCheckable(True)
        self.master_power_button.setObjectName("masterPowerButton")
        self.master_power_button.setFixedSize(25, 25)
        self.master_power_button.clicked.connect(self.toggle_all_lights)
        master_layout.addWidget(self.master_power_button)

        self.master_device_toggle = QPushButton("M")
        self.master_device_toggle.setObjectName("syncRevealButton")
        self.master_device_toggle.setFixedSize(25, 25)
        self.master_device_toggle.setToolTip("Show master device control")
        self.master_device_toggle.clicked.connect(self.toggle_master_device_control)
        master_layout.addWidget(self.master_device_toggle)

        self.sync_reveal_button = QPushButton("🔗")
        self.sync_reveal_button.setObjectName("syncRevealButton")
        self.sync_reveal_button.setFixedSize(25, 25)
        self.sync_reveal_button.setToolTip("Show sync controls")
        self.sync_reveal_button.clicked.connect(self.toggle_sync_controls)
        master_layout.addWidget(self.sync_reveal_button)

        self.sync_container = QWidget()
        self.sync_container.setVisible(False)
        self.sync_container.setStyleSheet("background-color: transparent;")
        sync_layout = QHBoxLayout(self.sync_container)
        sync_layout.setContentsMargins(0, 0, 0, 0)
        sync_layout.setSpacing(4)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setObjectName("separator")
        sync_layout.addWidget(separator)

        self.temp_sync_button = QPushButton("🌡")
        self.temp_sync_button.setCheckable(True)
        self.temp_sync_button.setObjectName("syncButton")
        self.temp_sync_button.setFixedSize(28, 28)
        self.temp_sync_button.setToolTip("Toggle temperature sync (Right-click for one-time sync)")
        self.temp_sync_button.clicked.connect(self.toggle_temp_sync)
        self.temp_sync_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.temp_sync_button.customContextMenuRequested.connect(lambda: self.sync_temperature_once())
        sync_layout.addWidget(self.temp_sync_button)

        self.brightness_sync_button = QPushButton("☀")
        self.brightness_sync_button.setCheckable(True)
        self.brightness_sync_button.setObjectName("syncButton")
        self.brightness_sync_button.setFixedSize(28, 28)
        self.brightness_sync_button.setToolTip("Toggle brightness sync (Right-click for one-time sync)")
        self.brightness_sync_button.clicked.connect(self.toggle_brightness_sync)
        self.brightness_sync_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.brightness_sync_button.customContextMenuRequested.connect(lambda: self.sync_brightness_once())
        sync_layout.addWidget(self.brightness_sync_button)

        self.sync_all_button = QPushButton("⚡")
        self.sync_all_button.setCheckable(True)
        self.sync_all_button.setObjectName("syncButton")
        self.sync_all_button.setFixedSize(28, 28)
        self.sync_all_button.setToolTip("Toggle all sync (Right-click for one-time sync)")
        self.sync_all_button.clicked.connect(self.toggle_all_sync)
        self.sync_all_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sync_all_button.customContextMenuRequested.connect(lambda: self.sync_all_once())
        sync_layout.addWidget(self.sync_all_button)

        self.load_sync_settings()

        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.process_pending_sync)
        self.sync_timer.setInterval(300)
        self.pending_sync_updates = {}

        master_layout.addWidget(self.sync_container)

        # Settings button (three dots)
        self.settings_button = QPushButton("⋯")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setFixedSize(25, 25)
        self.settings_button.setToolTip("Settings")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        master_layout.addWidget(self.settings_button)

        master_layout.addStretch()

    # --- actions and helpers ---
    def toggle_all_lights(self):
        if not self.keylights:
            return
        master_state = self.master_power_button.isChecked()
        for widget in self.keylight_widgets:
            widget.keylight.on = master_state
            widget.power_button.setChecked(master_state)
            widget.update_power_button_style()
            widget.schedule_update()
        self.update_master_button_style()

    def toggle_sync_controls(self):
        is_visible = self.sync_container.isVisible()
        self.sync_container.setVisible(not is_visible)
        if not is_visible:
            self.sync_reveal_button.setText("⛓️‍💥")
            self.sync_reveal_button.setToolTip("Hide sync controls")
        else:
            self.sync_reveal_button.setText("🔗")
            self.sync_reveal_button.setToolTip("Show sync controls")
        self.save_sync_settings()

    def toggle_master_device_control(self):
        is_visible = self.master_device_widget.isVisible()
        new_visibility = not is_visible
        self.master_device_widget.setVisible(new_visibility)
        self.update_device_controls_for_master_state(new_visibility)
        self.update_master_device_toggle_appearance()
        self.adjust_window_size()
        self.device_config.set_app_setting("master_device_visible", new_visibility)

    def update_device_controls_for_master_state(self, master_visible):
        if master_visible:
            for widget in self.keylight_widgets:
                widget.setVisible(False)
            if not hasattr(self, "_sync_controls_state_before_master"):
                self._sync_controls_state_before_master = self.sync_container.isVisible()
            self.sync_container.setVisible(False)
            self.sync_reveal_button.setEnabled(False)
            self.sync_reveal_button.setStyleSheet(
                """
                QPushButton#syncRevealButton {
                    background-color: #2a2a2a;
                    border: 1px solid #444444;
                    border-radius: 12px;
                    color: #666666;
                    font-size: 16px;
                    font-weight: bold;
                }
                """
            )
        else:
            for widget in self.keylight_widgets:
                widget.setVisible(True)
            if hasattr(self, "_sync_controls_state_before_master"):
                self.sync_container.setVisible(self._sync_controls_state_before_master)
                if self._sync_controls_state_before_master:
                    self.sync_reveal_button.setText("⛓️‍💥")
                    self.sync_reveal_button.setToolTip("Hide sync controls")
                else:
                    self.sync_reveal_button.setText("🔗")
                    self.sync_reveal_button.setToolTip("Show sync controls")
                delattr(self, "_sync_controls_state_before_master")
            self.sync_reveal_button.setEnabled(True)
            self.sync_reveal_button.setStyleSheet("")

    def update_master_device_toggle_appearance(self):
        if hasattr(self, "master_device_widget") and hasattr(self, "master_device_toggle"):
            is_visible = self.master_device_widget.isVisible()
            if is_visible:
                self.master_device_toggle.setText("M̄")
                self.master_device_toggle.setToolTip("Hide master device control")
            else:
                self.master_device_toggle.setText("M")
                self.master_device_toggle.setToolTip("Show master device control")

    def load_sync_settings(self):
        self.temp_sync_enabled = self.device_config.get_app_setting("temp_sync_enabled", False)
        self.brightness_sync_enabled = self.device_config.get_app_setting("brightness_sync_enabled", False)
        self.all_sync_enabled = self.device_config.get_app_setting("all_sync_enabled", False)
        sync_controls_visible = self.device_config.get_app_setting("sync_controls_visible", False)
        self.temp_sync_button.setChecked(self.temp_sync_enabled)
        self.brightness_sync_button.setChecked(self.brightness_sync_enabled)
        self.sync_all_button.setChecked(self.all_sync_enabled)
        self.sync_container.setVisible(sync_controls_visible)
        if sync_controls_visible:
            self.sync_reveal_button.setText("⛓️‍💥")
            self.sync_reveal_button.setToolTip("Hide sync controls")
        else:
            self.sync_reveal_button.setText("🔗")
            self.sync_reveal_button.setToolTip("Show sync controls")

    def save_sync_settings(self):
        self.device_config.set_app_setting("temp_sync_enabled", self.temp_sync_button.isChecked())
        self.device_config.set_app_setting("brightness_sync_enabled", self.brightness_sync_button.isChecked())
        self.device_config.set_app_setting("all_sync_enabled", self.sync_all_button.isChecked())
        self.device_config.set_app_setting("sync_controls_visible", self.sync_container.isVisible())

    def toggle_temp_sync(self):
        self.temp_sync_enabled = self.temp_sync_button.isChecked()
        if self.all_sync_enabled and self.temp_sync_enabled:
            self.all_sync_enabled = False
            self.sync_all_button.setChecked(False)
        self.save_sync_settings()

    def toggle_brightness_sync(self):
        self.brightness_sync_enabled = self.brightness_sync_button.isChecked()
        if self.all_sync_enabled and self.brightness_sync_enabled:
            self.all_sync_enabled = False
            self.sync_all_button.setChecked(False)
        self.save_sync_settings()

    def toggle_all_sync(self):
        self.all_sync_enabled = self.sync_all_button.isChecked()
        if self.all_sync_enabled:
            self.temp_sync_enabled = False
            self.brightness_sync_enabled = False
            self.temp_sync_button.setChecked(False)
            self.brightness_sync_button.setChecked(False)
        self.save_sync_settings()

    def sync_temperature_once(self):
        if len(self.keylights) < 2:
            return
        reference_temp = self.keylights[0].temperature
        for i, widget in enumerate(self.keylight_widgets):
            if i == 0 or widget.is_locked:
                continue
            widget.keylight.temperature = reference_temp
            old = widget.temp_slider.blockSignals(True)
            widget.temp_slider.setValue(reference_temp)
            widget.temp_slider.blockSignals(old)
            widget.temp_label.setText(f"{widget.to_kelvin(reference_temp)}K")
            widget.update_power_button_style()
            widget.schedule_update()
        self.update_master_button_style()

    def sync_brightness_once(self):
        if len(self.keylights) < 2:
            return
        reference_brightness = self.keylights[0].brightness
        for i, widget in enumerate(self.keylight_widgets):
            if i == 0 or widget.is_locked:
                continue
            widget.keylight.brightness = reference_brightness
            old = widget.brightness_slider.blockSignals(True)
            widget.brightness_slider.setValue(max(1, reference_brightness))
            widget.brightness_slider.blockSignals(old)
            widget.brightness_label.setText(f"{reference_brightness}%")
            widget.update_power_button_style()
            widget.schedule_update()
        self.update_master_button_style()

    def sync_all_once(self):
        if len(self.keylights) < 2:
            return
        reference_device = self.keylights[0]
        for i, widget in enumerate(self.keylight_widgets):
            if i == 0 or widget.is_locked:
                continue
            widget.keylight.on = reference_device.on
            widget.keylight.brightness = reference_device.brightness
            widget.keylight.temperature = reference_device.temperature
            widget.power_button.setChecked(reference_device.on)
            b_old = widget.brightness_slider.blockSignals(True)
            widget.brightness_slider.setValue(max(1, reference_device.brightness))
            widget.brightness_slider.blockSignals(b_old)
            widget.brightness_label.setText(f"{reference_device.brightness}%")
            t_old = widget.temp_slider.blockSignals(True)
            widget.temp_slider.setValue(reference_device.temperature)
            widget.temp_slider.blockSignals(t_old)
            widget.temp_label.setText(f"{widget.to_kelvin(reference_device.temperature)}K")
            widget.update_power_button_style()
            widget.schedule_update()
        self.update_master_button_state()
        self.update_master_button_style()

    def propagate_sync_changes(self, source_widget, changed_attribute, value):
        if len(self.keylights) < 2:
            return
        should_sync = False
        if self.all_sync_enabled:
            should_sync = True
        elif self.temp_sync_enabled and changed_attribute == "temperature":
            should_sync = True
        elif self.brightness_sync_enabled and changed_attribute == "brightness":
            should_sync = True
        if not should_sync:
            return
        source_index = -1
        for i, widget in enumerate(self.keylight_widgets):
            if widget == source_widget:
                source_index = i
                break
        if source_index == -1:
            return
        for i, widget in enumerate(self.keylight_widgets):
            if i == source_index or widget.is_locked:
                continue
            if self.all_sync_enabled:
                if changed_attribute == "temperature":
                    widget.keylight.temperature = value
                    old = widget.temp_slider.blockSignals(True)
                    widget.temp_slider.setValue(value)
                    widget.temp_slider.blockSignals(old)
                    widget.temp_label.setText(f"{widget.to_kelvin(value)}K")
                elif changed_attribute == "brightness":
                    widget.keylight.brightness = value
                    old = widget.brightness_slider.blockSignals(True)
                    widget.brightness_slider.setValue(max(1, value))
                    widget.brightness_slider.blockSignals(old)
                    widget.brightness_label.setText(f"{value}%")
                elif changed_attribute == "power":
                    widget.keylight.on = value
                    widget.power_button.setChecked(value)
                widget.update_power_button_style()
                self.pending_sync_updates[i] = widget
            elif self.temp_sync_enabled and changed_attribute == "temperature":
                widget.keylight.temperature = value
                old = widget.temp_slider.blockSignals(True)
                widget.temp_slider.setValue(value)
                widget.temp_slider.blockSignals(old)
                widget.temp_label.setText(f"{widget.to_kelvin(value)}K")
                widget.update_power_button_style()
                self.pending_sync_updates[i] = widget
            elif self.brightness_sync_enabled and changed_attribute == "brightness":
                widget.keylight.brightness = value
                old = widget.brightness_slider.blockSignals(True)
                widget.brightness_slider.setValue(max(1, value))
                widget.brightness_slider.blockSignals(old)
                widget.brightness_label.setText(f"{value}%")
                widget.update_power_button_style()
                self.pending_sync_updates[i] = widget
        if self.pending_sync_updates and not self.sync_timer.isActive():
            self.sync_timer.start()
        self.update_master_button_style()

    def process_pending_sync(self):
        if not self.pending_sync_updates:
            self.sync_timer.stop()
            return
        for widget in self.pending_sync_updates.values():
            widget.schedule_update()
        self.pending_sync_updates.clear()
        self.sync_timer.stop()

    def update_master_button_style(self):
        if self.master_power_button.isChecked() and self.keylights:
            device_colors = []
            for widget in self.keylight_widgets:
                if widget.keylight.on:
                    r, g, b = widget.to_slider_color(widget.keylight.temperature)
                    alpha = widget.keylight.brightness / 100.0
                    device_colors.append((r, g, b, alpha))
            if device_colors:
                if len(device_colors) == 1:
                    r, g, b, alpha = device_colors[0]
                    color = f"rgba({r}, {g}, {b}, {alpha})"
                    self.master_power_button.setStyleSheet(
                        f"""
                        QPushButton#masterPowerButton {{
                            background-color: {color};
                            border: 2px solid rgba({r}, {g}, {b}, 1.0);
                            border-radius: 12px;
                            font-size: 20px;
                            color: #ffffff;
                            padding-bottom: 1px;
                        }}
                        """
                    )
                else:
                    gradient_stops = []
                    for i, (r, g, b, alpha) in enumerate(device_colors):
                        position = i / (len(device_colors) - 1)
                        gradient_stops.append(f"stop:{position:.2f} rgba({r}, {g}, {b}, {alpha})")
                    gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:0, " + ", ".join(gradient_stops) + ")"
                    avg_r = sum(r for r, g, b, a in device_colors) // len(device_colors)
                    avg_g = sum(g for r, g, b, a in device_colors) // len(device_colors)
                    avg_b = sum(b for r, g, b, a in device_colors) // len(device_colors)
                    self.master_power_button.setStyleSheet(
                        f"""
                        QPushButton#masterPowerButton {{
                            background: {gradient};
                            border: 2px solid rgb({avg_r}, {avg_g}, {avg_b});
                            border-radius: 12px;
                            font-size: 20px;
                            color: #ffffff;
                            padding-bottom: 1px;
                        }}
                        """
                    )
            else:
                self._apply_default_master_style()
        else:
            self._apply_default_master_style()

    def _apply_default_master_style(self):
        self.master_power_button.setStyleSheet(
            """
            QPushButton#masterPowerButton {
                background-color: transparent;
                border: 2px solid #555;
                border-radius: 12px;
                color: #555;
                font-size: 20px;
                padding-bottom: 1px;
            }
            """
        )

    def update_master_button_state(self):
        """Master button is ON if any device is ON; OFF only if all are OFF."""
        if not self.keylights:
            self.master_power_button.setChecked(False)
            self.update_master_button_style()
            return
        try:
            semantics = str(self.prefs.get("advanced.master_power_semantics", "AnyOn"))
        except Exception:
            semantics = "AnyOn"
        if semantics == "AllOn":
            state = all(kl.on for kl in self.keylights)
        else:
            state = any(kl.on for kl in self.keylights)
        self.master_power_button.setChecked(state)
        self.update_master_button_style()

    def apply_blur_effect(self):
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(8)
        self.centralWidget().setGraphicsEffect(blur_effect)

    def remove_blur_effect(self):
        self.centralWidget().setGraphicsEffect(None)

    def prepare_for_dialog(self):
        self.apply_blur_effect()
        self.original_size = self.size()
        dialog_height = 140
        current_height = self.height()
        if current_height < dialog_height + 100:
            new_height = dialog_height + 200
            self.resize(self.width(), new_height)

    def cleanup_after_dialog(self):
        self.remove_blur_effect()
        if hasattr(self, "original_size"):
            self.resize(self.original_size)
            delattr(self, "original_size")

    def apply_dark_theme(self):
        from ui.styles.dark_theme import get_style
        self.setStyleSheet(get_style())

    def setup_system_tray(self):
        self.tray_icon = create_tray_icon(self)

    def setup_shortcuts(self):
        quit_shortcut = QShortcut(QKeySequence.Quit, self)
        quit_shortcut.activated.connect(self.quit_application)
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self._on_escape)

    def _on_escape(self):
        if hasattr(self, 'prefs') and bool(self.prefs.get("general.hide_on_esc", True)):
            self.hide()
        else:
            pass

    def quit_application(self):
        self.discovery.stop_discovery()
        from PySide6.QtWidgets import QApplication as _QApp
        _QApp.quit()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()

    # ---- Preferences application ----
    def open_settings_dialog(self):
        dlg = SettingsDialog(self.prefs, self)
        dlg.exec()

    def _apply_all_preferences(self):
        self._apply_features_visibility()
        self._apply_widget_update_interval()
        self.update_master_button_state()

    def _on_setting_changed(self, key: str, _value):
        if key.startswith("features."):
            self._apply_features_visibility()
        elif key == "perf.widget_update_interval_ms":
            self._apply_widget_update_interval()
        elif key == "advanced.master_power_semantics":
            self.update_master_button_state()

    def _apply_features_visibility(self):
        show_sync = True
        try:
            show_sync = bool(self.prefs.get("features.show_sync_buttons", True))
        except Exception:
            pass
        self.sync_reveal_button.setVisible(show_sync)
        if not show_sync:
            self.sync_container.setVisible(False)

    def _apply_widget_update_interval(self):
        try:
            interval = int(self.prefs.get("perf.widget_update_interval_ms", 50))
        except Exception:
            interval = 50
        for w in self.keylight_widgets:
            try:
                w.update_timer.setInterval(interval)
            except Exception:
                pass

    def fetch_device_mac(self, device_info):
        asyncio.create_task(self._fetch_and_add_device(device_info))

    async def _fetch_and_add_device(self, device_info):
        mac_address = await self.discovery._get_device_mac_address(
            device_info["ip"], device_info["port"]
        )
        device_info["mac_address"] = mac_address
        self.discovery.device_found.emit(device_info)

    def add_keylight(self, device_info):
        for kl in self.keylights:
            if kl.ip == device_info["ip"]:
                return
        keylight = KeyLight(
            name=device_info["name"],
            ip=device_info["ip"],
            port=device_info.get("port", 9123),
            mac_address=device_info.get("mac_address", ""),
        )
        self.keylights.append(keylight)
        widget = KeyLightWidget(keylight, self)
        widget.power_state_changed.connect(self.update_master_button_state)
        custom_label = self.device_config.get_label(keylight.mac_address, keylight.name)
        widget.name_label.setText(custom_label)
        self.keylight_widgets.append(widget)
        self.devices_layout.addWidget(widget)
        if self.master_device_widget:
            self.master_device_widget.update_device_count()
            if len(self.keylights) == 1:
                self.master_device_widget.update_from_devices()
        if hasattr(self, "master_device_widget") and self.master_device_widget.isVisible():
            widget.setVisible(False)
        self.adjust_window_size()
        self.update_master_button_state()

    def adjust_window_size(self):
        master_panel_height = 60
        title_bar = 35
        margins = 16
        master_device_visible = hasattr(self, "master_device_widget") and self.master_device_widget.isVisible()
        if master_device_visible:
            master_device_height = 140
            needed_height = master_panel_height + master_device_height + margins + title_bar
        elif len(self.keylights) == 0:
            needed_height = master_panel_height + title_bar + margins + 50
        else:
            num_lights = len(self.keylights)
            spacing_between = (num_lights - 1) * 8 if num_lights > 1 else 0
            needed_height = master_panel_height + (num_lights * self.widget_height) + spacing_between + margins + title_bar
        new_height = min(needed_height, self.max_height)
        self.setFixedHeight(new_height)
        if needed_height > self.max_height:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def closeEvent(self, event):
        from PySide6.QtWidgets import QApplication as _QApp
        modifiers = _QApp.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            self.discovery.stop_discovery()
            _QApp.quit()
            event.accept()
        else:
            event.ignore()
            self.hide()
            if self.tray_icon.isSystemTrayAvailable():
                self.tray_icon.showMessage(
                    "Key Light Control",
                    "Application minimized to tray. Right-click tray icon to quit.",
                    QSystemTrayIcon.Information,
                    2000,
                )
