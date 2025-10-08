from __future__ import annotations

import asyncio
import time
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMenu,
)
from PySide6.QtGui import QAction, QCursor

from core.models import KeyLight
from ui.widgets.jump_slider import JumpSlider
from ui.widgets.rename_dialog import RenameDeviceDialog
from utils.color_utils import (
    elgato_to_kelvin as util_elgato_to_kelvin,
    slider_color_for_temp as util_slider_color_for_temp,
    percent_to_hex_alpha as util_percent_to_hex_alpha,
)


class KeyLightWidget(QFrame):
    """Widget for controlling a single Key Light."""

    power_state_changed = Signal()

    def __init__(self, keylight: KeyLight, parent=None):
        super().__init__(parent)
        self.keylight = keylight
        self.is_locked = False  # Lock state for sync protection
        self.pending_update = None
        self.last_update_time = 0.0
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.process_pending_update)
        self.update_timer.setInterval(50)  # Process updates every 50ms max
        self.setup_ui()
        self.update_from_device()
        self.load_lock_state()

    # ----- Utilities -----
    def _find_controller(self):
        controller = self.parent()
        while controller is not None and getattr(controller.__class__, "__name__", "") != "KeyLightController":
            controller = controller.parent()
        return controller

    @staticmethod
    def to_kelvin(value: int) -> int:
        """Convert Elgato temperature value to Kelvin."""
        return util_elgato_to_kelvin(value)

    @staticmethod
    def to_slider_color(value: int) -> Tuple[int, int, int]:
        """Interpolate between left (#88aaff) and right (#ff9944) slider colors."""
        return util_slider_color_for_temp(value)

    @staticmethod
    def percent_to_hex_alpha(percent: float) -> str:
        """Convert 0-100 percent to two-digit hex alpha."""
        return util_percent_to_hex_alpha(percent)

    def keylight_color(self) -> str:
        r, g, b = self.to_slider_color(self.keylight.temperature)
        a = int(255 * (self.keylight.brightness / 100))
        return f"rgba({r}, {g}, {b}, {a})"

    # ----- UI Setup -----
    def setup_ui(self) -> None:
        self.setObjectName("KeyLightWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.power_button = QPushButton("⏻")
        self.power_button.setCheckable(True)
        self.power_button.setObjectName("powerButton")
        self.power_button.setFixedSize(36, 36)
        self.power_button.clicked.connect(self.toggle_power)

        self.lock_icon = QLabel("🔒")
        self.lock_icon.setObjectName("lockIcon")
        self.lock_icon.setVisible(False)

        self.name_label = QLabel(self.keylight.name)
        self.name_label.setObjectName("deviceName")

        self.menu_button = QPushButton("⋮")
        self.menu_button.setObjectName("menuButton")
        self.menu_button.setFixedSize(30, 30)
        self.menu_button.clicked.connect(self.show_device_menu)

        header_layout.addWidget(self.power_button)
        header_layout.addWidget(self.lock_icon, 0)
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        header_layout.addWidget(self.menu_button)

        layout.addLayout(header_layout)

        # Brightness
        brightness_layout = QHBoxLayout()
        brightness_icon = QLabel("☀")
        brightness_icon.setObjectName("sliderIcon")
        brightness_icon.setFixedWidth(20)

        self.brightness_slider = JumpSlider(Qt.Horizontal)
        self.brightness_slider.setRange(1, 100)
        self.brightness_slider.setValue(max(1, self.keylight.brightness))
        self.brightness_slider.setObjectName("brightnessSlider")
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)

        self.brightness_label = QLabel(f"{self.keylight.brightness}%")
        self.brightness_label.setObjectName("sliderValue")
        self.brightness_label.setFixedWidth(40)

        brightness_layout.addWidget(brightness_icon)
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_label)
        layout.addLayout(brightness_layout)

        # Temperature
        temp_layout = QHBoxLayout()
        temp_icon = QLabel("🌡")
        temp_icon.setObjectName("sliderIcon")
        temp_icon.setFixedWidth(20)

        self.temp_slider = JumpSlider(Qt.Horizontal)
        self.temp_slider.setRange(143, 344)
        self.temp_slider.setValue(self.keylight.temperature)
        self.temp_slider.setObjectName("temperatureSlider")
        self.temp_slider.valueChanged.connect(self.on_temperature_changed)

        self.temp_label = QLabel(f"{self.to_kelvin(self.keylight.temperature)}K")
        self.temp_label.setObjectName("sliderValue")
        self.temp_label.setFixedWidth(40)

        temp_layout.addWidget(temp_icon)
        temp_layout.addWidget(self.temp_slider)
        temp_layout.addWidget(self.temp_label)
        layout.addLayout(temp_layout)

        self.setStyleSheet("")

    # ----- Actions -----
    def toggle_power(self) -> None:
        self.keylight.on = self.power_button.isChecked()
        self.update_device()
        self.update_power_button_style()
        self.power_state_changed.emit()

        controller = self._find_controller()
        if controller:
            controller.propagate_sync_changes(self, "power", self.keylight.on)

    def on_brightness_changed(self, value: int) -> None:
        self.keylight.brightness = value
        self.brightness_label.setText(f"{value}%")
        self.schedule_update()
        self.update_power_button_style()

        controller = self._find_controller()
        if controller:
            controller.update_master_button_style()
            controller.propagate_sync_changes(self, "brightness", value)

    def on_temperature_changed(self, value: int) -> None:
        self.keylight.temperature = value
        self.temp_label.setText(f"{self.to_kelvin(value)}K")
        self.schedule_update()
        self.update_power_button_style()

        controller = self._find_controller()
        if controller:
            controller.update_master_button_style()
            controller.propagate_sync_changes(self, "temperature", value)

    # ----- Update Throttling -----
    def schedule_update(self) -> None:
        self.pending_update = {
            "on": self.keylight.on,
            "brightness": self.keylight.brightness,
            "temperature": self.keylight.temperature,
        }
        if not self.update_timer.isActive():
            self.update_timer.start()

    def process_pending_update(self) -> None:
        if self.pending_update:
            current_time = time.time()
            if current_time - self.last_update_time >= 0.1:
                self.update_device()
                self.last_update_time = current_time
                self.pending_update = None
                self.update_timer.stop()

    # ----- Device I/O -----
    def update_power_button_style(self) -> None:
        if self.keylight.on:
            color = self.keylight_color()
            self.power_button.setStyleSheet(
                f"""
                QPushButton#powerButton {{
                    background-color: {color};
                    border: 2px solid #ffffff;
                    font-size: 30px;
                    color: #ffffff;
                    padding-bottom: 2px;
                }}
                """
            )
        else:
            self.power_button.setStyleSheet(
                """
                QPushButton#powerButton {
                    background-color: transparent;
                    border: 2px solid #555;
                    color: #555;
                    font-size: 30px;
                    padding-bottom: 2px;
                }
                """
            )

    def update_device(self) -> None:
        asyncio.create_task(self._update_device_async())

    async def _update_device_async(self) -> None:
        controller = self._find_controller()
        if controller:
            try:
                await controller.service.set_light_state(self.keylight)
            except Exception:
                pass

    def update_from_device(self) -> None:
        asyncio.create_task(self._update_from_device_async())

    async def _update_from_device_async(self) -> None:
        controller = self._find_controller()
        if not controller:
            return
        try:
            data = await controller.service.fetch_light_state(self.keylight)
            if data and data.get("lights"):
                light_data = data["lights"][0]
                self.keylight.on = bool(light_data.get("on", self.keylight.on))
                self.keylight.brightness = light_data.get("brightness", self.keylight.brightness)
                self.keylight.temperature = light_data.get("temperature", self.keylight.temperature)

                self.power_button.setChecked(self.keylight.on)
                self.brightness_slider.setValue(max(1, self.keylight.brightness))
                self.temp_slider.setValue(self.keylight.temperature)
                self.update_power_button_style()
                self.power_state_changed.emit()
        except Exception:
            pass

    # ----- Menus & Locking -----
    def show_device_menu(self) -> None:
        menu = QMenu(self)

        controller = self._find_controller()
        if not controller:
            return

        rename_action = QAction("Rename Device", self)
        rename_action.triggered.connect(lambda: self.rename_device(controller))
        menu.addAction(rename_action)

        reset_action = QAction("Reset to Default", self)
        reset_action.triggered.connect(lambda: self.reset_label(controller))
        has_custom = controller.device_config.has_custom_label(self.keylight.mac_address)
        reset_action.setEnabled(has_custom)
        menu.addAction(reset_action)

        menu.addSeparator()

        lock_text = "Unlock Device" if self.is_locked else "Lock Device"
        lock_action = QAction(lock_text, self)
        lock_action.triggered.connect(self.toggle_lock)
        menu.addAction(lock_action)

        if len(controller.keylights) > 1:
            menu.addSeparator()
            sync_temp_action = QAction("Copy temperature to devices", self)
            sync_temp_action.triggered.connect(lambda: self.sync_to_others(controller, "temperature"))
            menu.addAction(sync_temp_action)

            sync_brightness_action = QAction("Copy brightness to devices", self)
            sync_brightness_action.triggered.connect(lambda: self.sync_to_others(controller, "brightness"))
            menu.addAction(sync_brightness_action)

            sync_all_action = QAction("Copy all settings to devices", self)
            sync_all_action.triggered.connect(lambda: self.sync_to_others(controller, "all"))
            menu.addAction(sync_all_action)

        menu.exec_(QCursor.pos())

    def rename_device(self, controller) -> None:
        original_name = controller.device_config.get_label(self.keylight.mac_address, self.keylight.name)
        controller.show_blur_overlay()
        try:
            controller.adjust_window_size_for_dialog()
            dialog = RenameDeviceDialog(original_name, self.keylight.name, controller)
            if dialog.exec():
                new_name = dialog.get_name()
                if new_name and new_name != original_name:
                    success = controller.device_config.set_label(
                        self.keylight.mac_address, original_name, new_name, self.keylight.ip
                    )
                    if success:
                        self.name_label.setText(new_name)
                    else:
                        print(f"Failed to save custom label for {original_name}")
        finally:
            controller.cleanup_after_dialog()

    def reset_label(self, controller) -> None:
        original_name = self.keylight.name
        success = controller.device_config.remove_label(self.keylight.mac_address)
        if success:
            self.name_label.setText(original_name)
        else:
            print(f"Failed to reset label for {original_name}")

    def toggle_lock(self) -> None:
        self.is_locked = not self.is_locked
        self.update_lock_visual()
        self.save_lock_state()

    def load_lock_state(self) -> None:
        controller = self._find_controller()
        if controller and controller.device_config:
            self.is_locked = controller.device_config.get_lock_state(self.keylight.mac_address)
            self.update_lock_visual()

    def save_lock_state(self) -> None:
        controller = self._find_controller()
        if controller and controller.device_config:
            controller.device_config.set_lock_state(self.keylight.mac_address, self.is_locked)

    def update_lock_visual(self) -> None:
        self.lock_icon.setVisible(bool(self.is_locked))

    def sync_to_others(self, controller, sync_type: str) -> None:
        if len(controller.keylights) < 2:
            return
        if self.is_locked:
            return

        source_device = self.keylight
        for i, widget in enumerate(controller.keylight_widgets):
            if widget.keylight.mac_address == source_device.mac_address:
                continue
            if widget.is_locked:
                continue

            target_widget = widget
            target_device = widget.keylight

            if sync_type == "all":
                target_device.on = source_device.on
                target_device.brightness = source_device.brightness
                target_device.temperature = source_device.temperature

                target_widget.power_button.setChecked(source_device.on)
                b_old = target_widget.brightness_slider.blockSignals(True)
                target_widget.brightness_slider.setValue(max(1, source_device.brightness))
                target_widget.brightness_slider.blockSignals(b_old)
                target_widget.brightness_label.setText(f"{source_device.brightness}%")
                t_old = target_widget.temp_slider.blockSignals(True)
                target_widget.temp_slider.setValue(source_device.temperature)
                target_widget.temp_slider.blockSignals(t_old)
                target_widget.temp_label.setText(f"{target_widget.to_kelvin(source_device.temperature)}K")

            elif sync_type == "temperature":
                target_device.temperature = source_device.temperature
                t_old = target_widget.temp_slider.blockSignals(True)
                target_widget.temp_slider.setValue(source_device.temperature)
                target_widget.temp_slider.blockSignals(t_old)
                target_widget.temp_label.setText(f"{target_widget.to_kelvin(source_device.temperature)}K")

            elif sync_type == "brightness":
                target_device.brightness = source_device.brightness
                b_old = target_widget.brightness_slider.blockSignals(True)
                target_widget.brightness_slider.setValue(max(1, source_device.brightness))
                target_widget.brightness_slider.blockSignals(b_old)
                target_widget.brightness_label.setText(f"{source_device.brightness}%")

            target_widget.update_power_button_style()
            target_widget.schedule_update()

        controller.update_master_button_style()
