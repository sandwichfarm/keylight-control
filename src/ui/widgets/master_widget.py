from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSlider,
    QMenu,
)
from PySide6.QtGui import QAction, QCursor
import math


class MasterDeviceWidget(QFrame):
    """Master control widget that looks like a device but controls all devices."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.ignore_locks = True  # Enabled by default
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI to match device style but with master control styling."""
        self.setObjectName("MasterDeviceWidget")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header with power button, device name, and menu button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Power button
        self.power_button = QPushButton("○")
        self.power_button.setObjectName("masterPowerButton")
        self.power_button.setCheckable(True)
        self.power_button.setFixedSize(36, 36)
        self.power_button.clicked.connect(self.toggle_all_power)
        header_layout.addWidget(self.power_button)

        # Device name
        device_count = len(self.controller.keylights)
        self.name_label = QLabel(f"Master ({device_count} devices)")
        self.name_label.setObjectName("deviceName")
        header_layout.addWidget(self.name_label)

        header_layout.addStretch()

        # Menu button (three dots)
        self.menu_button = QPushButton("⋮")
        self.menu_button.setObjectName("menuButton")
        self.menu_button.setFixedSize(24, 24)
        self.menu_button.clicked.connect(self.show_master_menu)
        header_layout.addWidget(self.menu_button)

        main_layout.addLayout(header_layout)

        # Brightness control
        brightness_layout = QHBoxLayout()
        brightness_layout.setContentsMargins(0, 0, 0, 0)

        brightness_icon = QLabel("☀")
        brightness_icon.setObjectName("sliderIcon")
        brightness_icon.setFixedSize(20, 20)
        brightness_layout.addWidget(brightness_icon)

        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setObjectName("brightnessSlider")
        self.brightness_slider.setRange(1, 100)
        self.brightness_slider.setValue(50)
        self.brightness_slider.valueChanged.connect(self.brightness_changed)
        brightness_layout.addWidget(self.brightness_slider)

        self.brightness_label = QLabel("50%")
        self.brightness_label.setObjectName("sliderValue")
        self.brightness_label.setFixedWidth(40)
        brightness_layout.addWidget(self.brightness_label)

        main_layout.addLayout(brightness_layout)

        # Temperature control
        temp_layout = QHBoxLayout()
        temp_layout.setContentsMargins(0, 0, 0, 0)

        temp_icon = QLabel("🌡")
        temp_icon.setObjectName("sliderIcon")
        temp_icon.setFixedSize(20, 20)
        temp_layout.addWidget(temp_icon)

        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setObjectName("temperatureSlider")
        self.temp_slider.setRange(143, 344)
        self.temp_slider.setValue(250)
        self.temp_slider.valueChanged.connect(self.temperature_changed)
        temp_layout.addWidget(self.temp_slider)

        self.temp_label = QLabel("5000K")
        self.temp_label.setObjectName("sliderValue")
        self.temp_label.setFixedWidth(50)
        temp_layout.addWidget(self.temp_label)

        main_layout.addLayout(temp_layout)

        self.update_power_button_style()

    def update_device_count(self):
        device_count = len(self.controller.keylights)
        self.name_label.setText(f"Master ({device_count} devices)")

    def toggle_ignore_locks(self):
        self.ignore_locks = not self.ignore_locks
        self.controller.device_config.set_app_setting("master_ignore_locks", self.ignore_locks)

    def show_master_menu(self):
        menu = QMenu(self)

        ignore_locks_text = "Disable ignore locks" if self.ignore_locks else "Enable ignore locks"
        ignore_locks_action = QAction(ignore_locks_text, self)
        ignore_locks_action.triggered.connect(self.toggle_ignore_locks)
        menu.addAction(ignore_locks_action)

        menu.setStyleSheet(
            """
            QMenu {
                background-color: #2a2a2a;
                border: 1px solid #555555;
                color: #ffffff;
            }
            QMenu::item { padding: 6px 12px; }
            QMenu::item:selected { background-color: #00E5FF; }
            QMenu::item:disabled { color: #888888; }
            """
        )

        menu.exec_(QCursor.pos())

    def toggle_all_power(self):
        if not self.controller.keylights:
            return
        new_state = self.power_button.isChecked()
        for widget in self.controller.keylight_widgets:
            if not self.ignore_locks and getattr(widget, "is_locked", False):
                continue
            widget.keylight.on = new_state
            widget.power_button.setChecked(new_state)
            widget.update_power_button_style()
            widget.schedule_update()
        self.update_power_button_style()

    def brightness_changed(self, value):
        if not self.controller.keylights:
            return
        self.brightness_label.setText(f"{value}%")
        for widget in self.controller.keylight_widgets:
            if not self.ignore_locks and getattr(widget, "is_locked", False):
                continue
            widget.keylight.brightness = value
            old = widget.brightness_slider.blockSignals(True)
            widget.brightness_slider.setValue(value)
            widget.brightness_slider.blockSignals(old)
            widget.brightness_label.setText(f"{value}%")
            widget.update_power_button_style()
            widget.schedule_update()

    def temperature_changed(self, value):
        if not self.controller.keylights:
            return
        kelvin = self.to_kelvin(value)
        self.temp_label.setText(f"{kelvin}K")
        for widget in self.controller.keylight_widgets:
            if not self.ignore_locks and getattr(widget, "is_locked", False):
                continue
            widget.keylight.temperature = value
            old = widget.temp_slider.blockSignals(True)
            widget.temp_slider.setValue(value)
            widget.temp_slider.blockSignals(old)
            widget.temp_label.setText(f"{kelvin}K")
            widget.update_power_button_style()
            widget.schedule_update()

    def to_kelvin(self, slider_value):
        return int(2900 + (slider_value - 143) * (7000 - 2900) / (344 - 143))

    def update_from_devices(self):
        if not self.controller.keylights:
            return
        first_device = self.controller.keylights[0]
        self.power_button.setChecked(first_device.on)
        self.brightness_slider.setValue(first_device.brightness)
        self.brightness_label.setText(f"{first_device.brightness}%")
        self.temp_slider.setValue(first_device.temperature)
        self.temp_label.setText(f"{self.to_kelvin(first_device.temperature)}K")
        self.update_power_button_style()

    def update_power_button_style(self):
        if not self.controller.keylights:
            return
        total_r, total_g, total_b = 0, 0, 0
        device_count = 0
        for widget in self.controller.keylight_widgets:
            if widget.keylight.on:
                brightness = widget.keylight.brightness / 100.0
                temp = widget.keylight.temperature
                kelvin = 2900 + (temp - 143) * (7000 - 2900) / (344 - 143)
                if kelvin <= 6600:
                    r = 255
                    g = int(99.4708025861 * math.log(kelvin / 100) - 161.1195681661) if kelvin > 2000 else 255
                    b = int(138.5177312231 * math.log(kelvin / 100 - 10) - 305.0447927307) if kelvin >= 2000 else 255
                else:
                    r = int(329.698727446 * ((kelvin / 100 - 60) ** -0.1332047592))
                    g = int(288.1221695283 * ((kelvin / 100 - 60) ** -0.0755148492))
                    b = 255
                r = int(r * brightness)
                g = int(g * brightness)
                b = int(b * brightness)
                total_r += r
                total_g += g
                total_b += b
                device_count += 1
        color = "#404040"
        if device_count > 0:
            avg_r = min(255, total_r // device_count)
            avg_g = min(255, total_g // device_count)
            avg_b = min(255, total_b // device_count)
            color = f"rgb({avg_r}, {avg_g}, {avg_b})"
        if self.power_button.isChecked() and device_count > 0:
            self.power_button.setStyleSheet(
                f"""
                QPushButton#masterPowerButton {{
                    background-color: {color};
                    border: 2px solid #ffffff;
                    border-radius: 18px;
                    font-size: 16px;
                    font-weight: bold;
                    color: #ffffff;
                }}
                QPushButton#masterPowerButton:hover {{
                    border: 2px solid #cccccc;
                }}
                """
            )
            self.power_button.setText("●")
        else:
            self.power_button.setStyleSheet(
                """
                QPushButton#masterPowerButton {
                    background-color: #404040;
                    border: 2px solid #666666;
                    border-radius: 18px;
                    color: #888888;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton#masterPowerButton:hover {
                    background-color: #4a4a4a;
                    border: 2px solid #777777;
                }
                """
            )
            self.power_button.setText("○")
