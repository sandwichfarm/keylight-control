#!/usr/bin/env python3
"""
Key Light Controller - A modern, cross-platform controller for Key Lights
Compatible with X11, Wayland, and various Linux distributions
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__license__ = "GPL-3.0"

import sys
import os
import json
import asyncio
import socket
import time
import math
from typing import List, Dict, Optional
 

# Import local modules
from config import DeviceConfig
from core.models import KeyLight
from core.discovery import KeyLightDiscovery
from core.service import KeyLightService
from utils.color_utils import (
    elgato_to_kelvin as util_elgato_to_kelvin,
    slider_color_for_temp as util_slider_color_for_temp,
    percent_to_hex_alpha as util_percent_to_hex_alpha,
)
from core.service import KeyLightService

# Check Python version
if sys.version_info < (3, 8):
    print("Error: Python 3.8 or higher is required")
    sys.exit(1)

try:
    import aiohttp
except ImportError:
    print("Error: aiohttp is required. Install with: pip install aiohttp")
    sys.exit(1)

try:
    from zeroconf import ServiceBrowser, Zeroconf
except ImportError:
    print("Error: zeroconf is required. Install with: pip install zeroconf")
    sys.exit(1)

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QSlider, QLabel, QPushButton, QFrame, QSystemTrayIcon, QMenu,
        QScrollArea, QSizePolicy, QDialog, QLineEdit, QDialogButtonBox,
        QCheckBox
    )
    from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject, QSize, QElapsedTimer, QPropertyAnimation, QEasingCurve
    from PySide6.QtGui import QIcon, QPalette, QColor, QAction, QPixmap, QPainter, QBrush, QPen, QKeySequence, QShortcut, QCursor
    from PySide6.QtWidgets import QGraphicsBlurEffect
except ImportError:
    print("Error: PySide6 is required. Install with: pip install PySide6")
    print("Note: On some systems you may need to install qt6-base first")
    sys.exit(1)



class JumpSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            new_val = self.minimum() + (self.maximum() - self.minimum()) * event.position().x() / self.width()
            self.setValue(round(new_val))
            event.accept()
        super().mousePressEvent(event)


class RenameDeviceDialog(QDialog):
    """Simple, functional dialog for renaming devices"""
    
    def __init__(self, current_name: str, original_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rename Device")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Input field
        self.name_input = QLineEdit(current_name)
        self.name_input.selectAll()
        layout.addWidget(self.name_input)
        
        # Clean buttons without icons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        
        # Remove icons from buttons
        ok_button = button_box.button(QDialogButtonBox.Ok)
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        ok_button.setText("Save")
        cancel_button.setText("Cancel")
        ok_button.setIcon(QIcon())  # Remove icon
        cancel_button.setIcon(QIcon())  # Remove icon
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Connect enter key
        self.name_input.returnPressed.connect(self.accept)
        
        # Focus and style
        self.name_input.setFocus()
        self.setStyleSheet("""
            QDialog {
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #00E5FF;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 12px;
                color: #ffffff;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:default {
                background-color: #00E5FF;
                color: #000000;
                font-weight: bold;
            }
        """)
    
    def get_name(self) -> str:
        """Get the entered name"""
        return self.name_input.text().strip()


 

class MasterDeviceWidget(QFrame):
    """Master control widget that looks like a device but controls all devices"""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.ignore_locks = True  # Enabled by default
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI to match device style but with master control styling"""
        self.setObjectName("MasterDeviceWidget")
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)  # Match device widgets
        main_layout.setSpacing(12)  # Match device widgets
        
        # Header with power button, device name, and menu button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Power button (larger than device buttons to stand out) - moved to left
        self.power_button = QPushButton()
        self.power_button.setObjectName("masterPowerButton")
        self.power_button.setCheckable(True)
        self.power_button.setFixedSize(36, 36)  # Same size as device buttons
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
        self.temp_slider.setRange(143, 344)  # Kelvin range mapped to slider
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
        """Update the device count in the master label"""
        device_count = len(self.controller.keylights)
        self.name_label.setText(f"Master ({device_count} devices)")
    
    def toggle_ignore_locks(self):
        """Toggle ignore locks setting"""
        self.ignore_locks = not self.ignore_locks
        # Save setting to config
        self.controller.device_config.set_app_setting('master_ignore_locks', self.ignore_locks)
    
    def show_master_menu(self):
        """Show the master device context menu"""
        menu = QMenu(self)
        
        # Ignore locks toggle action
        ignore_locks_text = 'Disable ignore locks' if self.ignore_locks else 'Enable ignore locks'
        ignore_locks_action = QAction(ignore_locks_text, self)
        ignore_locks_action.triggered.connect(self.toggle_ignore_locks)
        menu.addAction(ignore_locks_action)
        
        # Apply dark theme to menu (same style as device menus)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2a2a2a;
                border: 1px solid #555555;
                color: #ffffff;
            }
            QMenu::item {
                padding: 6px 12px;
            }
            QMenu::item:selected {
                background-color: #00E5FF;
            }
            QMenu::item:disabled {
                color: #888888;
            }
        """)
        
        # Show menu at cursor position
        menu.exec_(QCursor.pos())
    
    def toggle_all_power(self):
        """Toggle power for all devices"""
        if not self.controller.keylights:
            return
        
        new_state = self.power_button.isChecked()
        
        for widget in self.controller.keylight_widgets:
            # Check ignore locks setting
            if not self.ignore_locks and widget.is_locked:
                continue
            
            widget.keylight.on = new_state
            widget.power_button.setChecked(new_state)
            widget.update_power_button_style()
            widget.update_device()
        
        self.update_power_button_style()
    
    def brightness_changed(self, value):
        """Handle brightness slider change"""
        if not self.controller.keylights:
            return
        
        self.brightness_label.setText(f"{value}%")
        
        for widget in self.controller.keylight_widgets:
            # Check ignore locks setting
            if not self.ignore_locks and widget.is_locked:
                continue
            
            widget.keylight.brightness = value
            widget.brightness_slider.setValue(value)
            widget.brightness_label.setText(f"{value}%")
            widget.update_power_button_style()
            widget.update_device()
    
    def temperature_changed(self, value):
        """Handle temperature slider change"""
        if not self.controller.keylights:
            return
        
        kelvin = self.to_kelvin(value)
        self.temp_label.setText(f"{kelvin}K")
        
        for widget in self.controller.keylight_widgets:
            # Check ignore locks setting
            if not self.ignore_locks and widget.is_locked:
                continue
            
            widget.keylight.temperature = value
            widget.temp_slider.setValue(value)
            widget.temp_label.setText(f"{kelvin}K")
            widget.update_power_button_style()
            widget.update_device()
    
    def to_kelvin(self, slider_value):
        """Convert slider value to Kelvin"""
        return int(2900 + (slider_value - 143) * (7000 - 2900) / (344 - 143))
    
    def update_from_devices(self):
        """Update master controls based on device states"""
        if not self.controller.keylights:
            return
        
        # Use first device as reference for initial values
        first_device = self.controller.keylights[0]
        self.power_button.setChecked(first_device.on)
        self.brightness_slider.setValue(first_device.brightness)
        self.brightness_label.setText(f"{first_device.brightness}%")
        self.temp_slider.setValue(first_device.temperature)
        self.temp_label.setText(f"{self.to_kelvin(first_device.temperature)}K")
        self.update_power_button_style()
    
    def update_power_button_style(self):
        """Update power button style based on device states"""
        if not self.controller.keylights:
            return
        
        # Calculate average color from all devices for gradient effect
        total_r, total_g, total_b = 0, 0, 0
        device_count = 0
        
        for widget in self.controller.keylight_widgets:
            if widget.keylight.on:
                brightness = widget.keylight.brightness / 100.0
                temp = widget.keylight.temperature
                
                # Convert temperature to RGB
                kelvin = 2900 + (temp - 143) * (7000 - 2900) / (344 - 143)
                if kelvin <= 6600:
                    r = 255
                    g = int(99.4708025861 * math.log(kelvin / 100) - 161.1195681661) if kelvin > 2000 else 255
                    b = int(138.5177312231 * math.log(kelvin / 100 - 10) - 305.0447927307) if kelvin >= 2000 else 255
                else:
                    r = int(329.698727446 * ((kelvin / 100 - 60) ** -0.1332047592))
                    g = int(288.1221695283 * ((kelvin / 100 - 60) ** -0.0755148492))
                    b = 255
                
                # Apply brightness
                r = int(r * brightness)
                g = int(g * brightness)
                b = int(b * brightness)
                
                total_r += r
                total_g += g
                total_b += b
                device_count += 1
        
        if device_count > 0:
            avg_r = min(255, total_r // device_count)
            avg_g = min(255, total_g // device_count)
            avg_b = min(255, total_b // device_count)
            color = f"rgb({avg_r}, {avg_g}, {avg_b})"
        else:
            color = "#404040"
        
        if self.power_button.isChecked() and device_count > 0:
            self.power_button.setStyleSheet(f"""
                QPushButton#masterPowerButton {{
                    background-color: {color};
                    border: 2px solid #ffffff;
                    border-radius: 18px;
                    font-size: 16px;
                    font-weight: bold;
                }}
                QPushButton#masterPowerButton:hover {{
                    border: 2px solid #cccccc;
                }}
            """)
            self.power_button.setText("●")
        else:
            self.power_button.setStyleSheet("""
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
            """)
            self.power_button.setText("○")


class KeyLightWidget(QFrame):
    """Widget for controlling a single Key Light"""
    power_state_changed = Signal()
    
    def __init__(self, keylight: KeyLight, parent=None):
        super().__init__(parent)
        self.keylight = keylight
        self.is_locked = False  # Lock state for sync protection
        self.pending_update = None
        self.last_update_time = 0
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.process_pending_update)
        self.update_timer.setInterval(50)  # Process updates every 50ms max
        self.setup_ui()
        self.update_from_device()
        self.load_lock_state()
        
    def setup_ui(self):
        """Setup the UI to match Elgato Control Center style"""
        self.setObjectName("KeyLightWidget")
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header with device name and menu button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)  # Reduce default spacing
        
        # Power button (circular with icon)
        self.power_button = QPushButton("⏻")
        self.power_button.setCheckable(True)
        self.power_button.setObjectName("powerButton")
        self.power_button.setFixedSize(36, 36)
        self.power_button.clicked.connect(self.toggle_power)
        
        # Lock icon (hidden by default)
        self.lock_icon = QLabel("🔒")  # Lock symbol
        self.lock_icon.setObjectName("lockIcon")
        self.lock_icon.setVisible(False)  # Hidden by default
        
        # Device name
        self.name_label = QLabel(self.keylight.name)
        self.name_label.setObjectName("deviceName")
        
        # Menu button (three dots)
        self.menu_button = QPushButton("⋮")
        self.menu_button.setObjectName("menuButton")
        self.menu_button.setFixedSize(30, 30)
        self.menu_button.clicked.connect(self.show_device_menu)
        
        header_layout.addWidget(self.power_button)
        header_layout.addWidget(self.lock_icon, 0)  # No stretch, tight spacing
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        header_layout.addWidget(self.menu_button)
        
        layout.addLayout(header_layout)
        
        # Brightness control
        brightness_layout = QHBoxLayout()
        brightness_icon = QLabel("☀")
        brightness_icon.setObjectName("sliderIcon")
        brightness_icon.setFixedWidth(20)
        
        self.brightness_slider = JumpSlider(Qt.Horizontal)
        self.brightness_slider.setRange(1, 100)  # Minimum 1% to prevent turning off via slider
        self.brightness_slider.setValue(max(1, self.keylight.brightness))  # Ensure minimum 1%
        self.brightness_slider.setObjectName("brightnessSlider")
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)
        
        self.brightness_label = QLabel(f"{self.keylight.brightness}%")
        self.brightness_label.setObjectName("sliderValue")
        self.brightness_label.setFixedWidth(40)
        
        brightness_layout.addWidget(brightness_icon)
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_label)
        
        layout.addLayout(brightness_layout)
        
        # Temperature control
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
        
        # Apply frame styling
        self.setStyleSheet("")  # Will be set by the main window

    @staticmethod
    def to_kelvin(value: int) -> int:
        """Convert Elgato temperature value to Kelvin"""
        return util_elgato_to_kelvin(value)

    @staticmethod
    def to_slider_color(value: int) -> tuple[int, int, int]:
        """Interpolate between slider left color (#88aaff) and right color (#ff9944)"""
        return util_slider_color_for_temp(value)

    @staticmethod
    def percent_to_hex_alpha(percent: float):
        """Convert 0-100 percent to two-digit hex alpha ('FF' for 100%, '00' for 0%)"""
        return util_percent_to_hex_alpha(percent)

    def keylight_color(self):
        r, g, b = self.to_slider_color(self.keylight.temperature)
        a = int(255 * (self.keylight.brightness / 100))
        return f"rgba({r}, {g}, {b}, {a})"

    def toggle_power(self):
        """Toggle the power state"""
        self.keylight.on = self.power_button.isChecked()
        self.update_device()
        self.update_power_button_style()
        self.power_state_changed.emit()
        
        # Propagate sync if enabled
        controller = self.parent()
        while controller and not isinstance(controller, KeyLightController):
            controller = controller.parent()
        if controller:
            controller.propagate_sync_changes(self, 'power', self.keylight.on)
        
    def on_brightness_changed(self, value):
        """Handle brightness slider change"""
        self.keylight.brightness = value
        self.brightness_label.setText(f"{value}%")
        self.schedule_update()
        self.update_power_button_style()
        
        # Update master button to reflect new brightness
        controller = self.parent()
        while controller and not isinstance(controller, KeyLightController):
            controller = controller.parent()
        if controller:
            controller.update_master_button_style()
            controller.propagate_sync_changes(self, 'brightness', value)
        
    def on_temperature_changed(self, value):
        """Handle temperature slider change"""
        self.keylight.temperature = value
        self.temp_label.setText(f"{self.to_kelvin(value)}K")
        self.schedule_update()
        self.update_power_button_style()
        
        # Update master button to reflect new temperature/color
        controller = self.parent()
        while controller and not isinstance(controller, KeyLightController):
            controller = controller.parent()
        if controller:
            controller.update_master_button_style()
            controller.propagate_sync_changes(self, 'temperature', value)
        
    def schedule_update(self):
        """Schedule an update with throttling"""
        # Store the pending update
        self.pending_update = {
            'on': self.keylight.on,
            'brightness': self.keylight.brightness,
            'temperature': self.keylight.temperature
        }
        
        # Start the timer if not already running
        if not self.update_timer.isActive():
            self.update_timer.start()
            
    def process_pending_update(self):
        """Process pending update with rate limiting"""
        if self.pending_update:
            current_time = time.time()
            # Ensure at least 100ms between actual device updates
            if current_time - self.last_update_time >= 0.1:
                self.update_device()
                self.last_update_time = current_time
                self.pending_update = None
                self.update_timer.stop()
        
    def update_power_button_style(self):
        """Update power button appearance based on state"""
        if self.keylight.on:
            color = self.keylight_color()
            self.power_button.setStyleSheet(f"""
                QPushButton#powerButton {{
                    background-color: {color};
                    border: 2px solid #ffffff;
                    font-size: 30px;
                    color: #ffffff;
                    padding-bottom: 2px;
                }}
            """)
        else:
            self.power_button.setStyleSheet("""
                QPushButton#powerButton {
                    background-color: transparent;
                    border: 2px solid #555;
                    color: #555;
                    font-size: 30px;
                    padding-bottom: 2px;
                }
            """)
            
    def update_device(self):
        """Send update to the physical device"""
        # Create task but don't await to prevent blocking
        asyncio.create_task(self._update_device_async())
        
    async def _update_device_async(self):
        """Async update to device via service layer"""
        # Locate controller to access service
        controller = self.parent()
        while controller and not isinstance(controller, KeyLightController):
            controller = controller.parent()
        if controller:
            try:
                await controller.service.set_light_state(self.keylight)
            except Exception:
                pass
            
    def update_from_device(self):
        """Fetch current state from device"""
        asyncio.create_task(self._update_from_device_async())
        
    async def _update_from_device_async(self):
        """Async fetch from device via service layer"""
        # Locate controller to access service
        controller = self.parent()
        while controller and not isinstance(controller, KeyLightController):
            controller = controller.parent()
        if not controller:
            return
        try:
            data = await controller.service.fetch_light_state(self.keylight)
            if data and data.get('lights'):
                light_data = data['lights'][0]
                self.keylight.on = bool(light_data.get('on', self.keylight.on))
                self.keylight.brightness = light_data.get('brightness', self.keylight.brightness)
                self.keylight.temperature = light_data.get('temperature', self.keylight.temperature)
                
                # Update UI
                self.power_button.setChecked(self.keylight.on)
                self.brightness_slider.setValue(max(1, self.keylight.brightness))
                self.temp_slider.setValue(self.keylight.temperature)
                self.update_power_button_style()
                self.power_state_changed.emit()
        except Exception:
            pass  # Silently ignore fetch errors to reduce spam
    
    def show_device_menu(self):
        """Show the device context menu"""
        menu = QMenu(self)
        
        # Get controller reference to access device config
        controller = self.parent()
        while controller and not isinstance(controller, KeyLightController):
            controller = controller.parent()
        
        if not controller:
            return
        
        # Rename device action
        rename_action = QAction('Rename Device', self)
        rename_action.triggered.connect(lambda: self.rename_device(controller))
        menu.addAction(rename_action)
        
        # Reset to default action (only enabled if has custom label)
        reset_action = QAction('Reset to Default', self)
        reset_action.triggered.connect(lambda: self.reset_label(controller))
        has_custom = controller.device_config.has_custom_label(self.keylight.mac_address)
        reset_action.setEnabled(has_custom)
        menu.addAction(reset_action)
        
        # Add separator before lock/unlock
        menu.addSeparator()
        
        # Lock/Unlock toggle
        lock_text = 'Unlock Device' if self.is_locked else 'Lock Device'
        lock_action = QAction(lock_text, self)
        lock_action.triggered.connect(self.toggle_lock)
        menu.addAction(lock_action)
        
        # Add separator for sync options (only show if there are multiple devices)
        if len(controller.keylights) > 1:
            menu.addSeparator()
            
            # Sync all settings to other devices
            sync_all_action = QAction('Copy All to Others', self)
            sync_all_action.triggered.connect(lambda: self.sync_to_others(controller, 'all'))
            menu.addAction(sync_all_action)
            
            # Add separator before individual setting syncs
            menu.addSeparator()
            
            # Sync temperature to other devices
            sync_temp_action = QAction('Copy Temperature to Others', self)
            sync_temp_action.triggered.connect(lambda: self.sync_to_others(controller, 'temperature'))
            menu.addAction(sync_temp_action)
            
            # Sync brightness to other devices
            sync_brightness_action = QAction('Copy Brightness to Others', self)
            sync_brightness_action.triggered.connect(lambda: self.sync_to_others(controller, 'brightness'))
            menu.addAction(sync_brightness_action)
        
        # Apply dark theme to menu
        menu.setStyleSheet("""
            QMenu {
                background-color: #2a2a2a;
                border: 1px solid #555555;
                color: #ffffff;
            }
            QMenu::item {
                padding: 6px 12px;
            }
            QMenu::item:selected {
                background-color: #00E5FF;
            }
            QMenu::item:disabled {
                color: #888888;
            }
        """)
        
        # Show menu at cursor position
        menu.exec_(QCursor.pos())
    
    def rename_device(self, controller):
        """Show rename dialog and handle the result"""
        original_name = self.keylight.name
        current_label = controller.device_config.get_label(
            self.keylight.mac_address, 
            self.keylight.name
        )
        
        # Prepare the main window for dialog
        controller.prepare_for_dialog()
        
        try:
            dialog = RenameDeviceDialog(current_label, original_name, controller)
            result = dialog.exec()
            
            if result == QDialog.Accepted:
                new_name = dialog.get_name()
                if new_name and new_name != original_name:
                    # Save the custom label
                    success = controller.device_config.set_label(
                        self.keylight.mac_address,
                        original_name,
                        new_name,
                        self.keylight.ip
                    )
                    if success:
                        # Update the display name
                        self.name_label.setText(new_name)
                    else:
                        print(f"Failed to save custom label for {original_name}")
        finally:
            # Always cleanup when dialog closes
            controller.cleanup_after_dialog()
    
    def reset_label(self, controller):
        """Reset device to original name"""
        original_name = self.keylight.name
        success = controller.device_config.remove_label(self.keylight.mac_address)
        if success:
            # Update the display name back to original
            self.name_label.setText(original_name)
        else:
            print(f"Failed to reset label for {original_name}")
    
    def toggle_lock(self):
        """Toggle the lock state of this device"""
        self.is_locked = not self.is_locked
        self.update_lock_visual()
        self.save_lock_state()
    
    def load_lock_state(self):
        """Load lock state from config"""
        # Get controller reference to access device config
        controller = self.parent()
        while controller and not isinstance(controller, KeyLightController):
            controller = controller.parent()
        
        if controller and controller.device_config:
            self.is_locked = controller.device_config.get_lock_state(self.keylight.mac_address)
            self.update_lock_visual()
    
    def save_lock_state(self):
        """Save lock state to config"""
        # Get controller reference to access device config
        controller = self.parent()
        while controller and not isinstance(controller, KeyLightController):
            controller = controller.parent()
        
        if controller and controller.device_config:
            controller.device_config.set_lock_state(self.keylight.mac_address, self.is_locked)
    
    def update_lock_visual(self):
        """Update visual indication of lock state"""
        if self.is_locked:
            # Show lock icon
            self.lock_icon.setVisible(True)
        else:
            # Hide lock icon
            self.lock_icon.setVisible(False)
    
    def sync_to_others(self, controller, sync_type):
        """Sync this device's settings to all other devices"""
        if len(controller.keylights) < 2:
            return
        
        # Don't allow syncing from locked devices
        if self.is_locked:
            return
        
        source_device = self.keylight
        
        # Find all other devices (excluding this one)
        for i, widget in enumerate(controller.keylight_widgets):
            if widget.keylight.mac_address == source_device.mac_address:
                continue  # Skip self
            
            # Skip locked devices
            if widget.is_locked:
                continue
            
            target_widget = widget
            target_device = widget.keylight
            
            if sync_type == 'all':
                # Sync all settings
                target_device.on = source_device.on
                target_device.brightness = source_device.brightness
                target_device.temperature = source_device.temperature
                
                # Update UI
                target_widget.power_button.setChecked(source_device.on)
                target_widget.brightness_slider.setValue(max(1, source_device.brightness))
                target_widget.brightness_label.setText(f"{source_device.brightness}%")
                target_widget.temp_slider.setValue(source_device.temperature)
                target_widget.temp_label.setText(f"{target_widget.to_kelvin(source_device.temperature)}K")
                
            elif sync_type == 'temperature':
                # Sync only temperature
                target_device.temperature = source_device.temperature
                target_widget.temp_slider.setValue(source_device.temperature)
                target_widget.temp_label.setText(f"{target_widget.to_kelvin(source_device.temperature)}K")
                
            elif sync_type == 'brightness':
                # Sync only brightness
                target_device.brightness = source_device.brightness
                target_widget.brightness_slider.setValue(max(1, source_device.brightness))
                target_widget.brightness_label.setText(f"{source_device.brightness}%")
            
            # Update button style and send to device
            target_widget.update_power_button_style()
            target_widget.update_device()
        
        # Update master button style
        controller.update_master_button_style()


class KeyLightController(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.keylights = []
        self.keylight_widgets = []
        self.device_config = DeviceConfig()
        self.discovery = KeyLightDiscovery()
        self.service = KeyLightService()
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
        
    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("Key Light Control")
        self.setFixedWidth(400)
        self.setMinimumHeight(200)
        
        # Get screen dimensions for dynamic sizing
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.max_height = int(screen_geometry.height() * 0.75)  # 75% of screen height
        self.widget_height = 140  # Approximate height of each KeyLight widget
        
        # Central widget with scroll area
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Master control panel
        self.setup_master_controls()
        main_layout.addWidget(self.master_panel)
        
        # Scroll area for devices
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Container for device widgets
        self.devices_container = QWidget()
        self.devices_container.setStyleSheet("background-color: #1a1a1a;")
        self.devices_layout = QVBoxLayout(self.devices_container)
        self.devices_layout.setContentsMargins(8, 8, 8, 8)
        self.devices_layout.setSpacing(8)
        # Don't add stretch - we want tight packing
        
        # Create master device widget (hidden by default)
        self.master_device_widget = MasterDeviceWidget(self)
        # Load ignore locks setting
        ignore_locks = self.device_config.get_app_setting('master_ignore_locks', True)
        self.master_device_widget.ignore_locks = ignore_locks
        # Load master device visibility setting
        master_device_visible = self.device_config.get_app_setting('master_device_visible', False)
        self.master_device_widget.setVisible(master_device_visible)
        self.devices_layout.addWidget(self.master_device_widget)
        
        # Update master device toggle button appearance
        self.update_master_device_toggle_appearance()
        
        # Apply initial master state to device controls
        self.update_device_controls_for_master_state(master_device_visible)
        
        self.scroll_area.setWidget(self.devices_container)
        main_layout.addWidget(self.scroll_area)
        
    def setup_master_controls(self):
        """Setup master control panel with power and sync controls"""
        self.master_panel = QFrame()
        self.master_panel.setObjectName("MasterPanel")
        self.master_panel.setFixedHeight(70)
        
        master_layout = QHBoxLayout(self.master_panel)
        master_layout.setContentsMargins(16, 8, 16, 8)
        master_layout.setSpacing(8)  # Reduce from 12 to 8 for tighter spacing
        
        # Master power button (30% smaller than device buttons: 36px -> 25px)
        self.master_power_button = QPushButton("⏻")
        self.master_power_button.setCheckable(True)
        self.master_power_button.setObjectName("masterPowerButton")
        self.master_power_button.setFixedSize(25, 25)
        self.master_power_button.clicked.connect(self.toggle_all_lights)
        
        master_layout.addWidget(self.master_power_button)
        
        # Master device toggle button (directly to the right of master power button)
        self.master_device_toggle = QPushButton("M")
        self.master_device_toggle.setObjectName("syncRevealButton")  # Use same style
        self.master_device_toggle.setFixedSize(25, 25)
        self.master_device_toggle.setToolTip("Show master device control")
        self.master_device_toggle.clicked.connect(self.toggle_master_device_control)
        master_layout.addWidget(self.master_device_toggle)
        
        # Sync reveal button
        self.sync_reveal_button = QPushButton("🔗")
        self.sync_reveal_button.setObjectName("syncRevealButton")
        self.sync_reveal_button.setFixedSize(25, 25)
        self.sync_reveal_button.setToolTip("Show sync controls")
        self.sync_reveal_button.clicked.connect(self.toggle_sync_controls)
        master_layout.addWidget(self.sync_reveal_button)
        
        # Hidden sync controls container (appears right after sync button)
        self.sync_container = QWidget()
        self.sync_container.setVisible(False)
        self.sync_container.setStyleSheet("background-color: transparent;")  # Ensure transparent background
        sync_layout = QHBoxLayout(self.sync_container)
        sync_layout.setContentsMargins(0, 0, 0, 0)
        sync_layout.setSpacing(4)  # Reduce spacing from 8 to 4
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setObjectName("separator")
        sync_layout.addWidget(separator)
        
        # Temperature sync toggle button
        self.temp_sync_button = QPushButton("🌡")
        self.temp_sync_button.setCheckable(True)
        self.temp_sync_button.setObjectName("syncButton")
        self.temp_sync_button.setFixedSize(28, 28)
        self.temp_sync_button.setToolTip("Toggle temperature sync (Right-click for one-time sync)")
        self.temp_sync_button.clicked.connect(self.toggle_temp_sync)
        self.temp_sync_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.temp_sync_button.customContextMenuRequested.connect(lambda: self.sync_temperature_once())
        sync_layout.addWidget(self.temp_sync_button)
        
        # Brightness sync toggle button
        self.brightness_sync_button = QPushButton("☀")
        self.brightness_sync_button.setCheckable(True)
        self.brightness_sync_button.setObjectName("syncButton")
        self.brightness_sync_button.setFixedSize(28, 28)
        self.brightness_sync_button.setToolTip("Toggle brightness sync (Right-click for one-time sync)")
        self.brightness_sync_button.clicked.connect(self.toggle_brightness_sync)
        self.brightness_sync_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.brightness_sync_button.customContextMenuRequested.connect(lambda: self.sync_brightness_once())
        sync_layout.addWidget(self.brightness_sync_button)
        
        # Sync all toggle button
        self.sync_all_button = QPushButton("⚡")
        self.sync_all_button.setCheckable(True)
        self.sync_all_button.setObjectName("syncButton")
        self.sync_all_button.setFixedSize(28, 28)
        self.sync_all_button.setToolTip("Toggle all sync (Right-click for one-time sync)")
        self.sync_all_button.clicked.connect(self.toggle_all_sync)
        self.sync_all_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sync_all_button.customContextMenuRequested.connect(lambda: self.sync_all_once())
        sync_layout.addWidget(self.sync_all_button)
        
        # Initialize sync states from config
        self.load_sync_settings()
        
        # Sync throttling
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.process_pending_sync)
        self.sync_timer.setInterval(300)  # 300ms throttle for sync operations
        self.pending_sync_updates = {}
        
        master_layout.addWidget(self.sync_container)
        master_layout.addStretch()
        
    def toggle_all_lights(self):
        """Toggle power state of all connected lights"""
        if not self.keylights:
            return
            
        master_state = self.master_power_button.isChecked()
        
        # Update all device widgets
        for widget in self.keylight_widgets:
            widget.keylight.on = master_state
            widget.power_button.setChecked(master_state)
            widget.update_power_button_style()
            widget.update_device()
            
        self.update_master_button_style()
    
    def toggle_sync_controls(self):
        """Toggle visibility of sync controls"""
        is_visible = self.sync_container.isVisible()
        self.sync_container.setVisible(not is_visible)
        
        # Update button appearance and tooltip
        if not is_visible:
            self.sync_reveal_button.setText("⛓️‍💥")
            self.sync_reveal_button.setToolTip("Hide sync controls")
        else:
            self.sync_reveal_button.setText("🔗")
            self.sync_reveal_button.setToolTip("Show sync controls")
        
        # Save visibility state
        self.save_sync_settings()
    
    def toggle_master_device_control(self):
        """Toggle visibility of master device control"""
        is_visible = self.master_device_widget.isVisible()
        new_visibility = not is_visible
        
        # Show/hide master device widget
        self.master_device_widget.setVisible(new_visibility)
        
        # Update device controls and sync state based on master visibility
        self.update_device_controls_for_master_state(new_visibility)
        
        # Update button appearance and tooltip
        self.update_master_device_toggle_appearance()
        
        # Adjust window size for new state
        self.adjust_window_size()
        
        # Save visibility state
        self.device_config.set_app_setting('master_device_visible', new_visibility)
    
    def update_device_controls_for_master_state(self, master_visible):
        """Update device controls and sync state based on master visibility"""
        if master_visible:
            # When master is enabled:
            # 1. Hide all device controls
            for widget in self.keylight_widgets:
                widget.setVisible(False)
            
            # 2. Store current sync controls visibility state and hide them
            if not hasattr(self, '_sync_controls_state_before_master'):
                self._sync_controls_state_before_master = self.sync_container.isVisible()
            self.sync_container.setVisible(False)
            
            # 3. Disable sync reveal button
            self.sync_reveal_button.setEnabled(False)
            self.sync_reveal_button.setStyleSheet("""
                QPushButton#syncRevealButton {
                    background-color: #2a2a2a;
                    border: 1px solid #444444;
                    border-radius: 12px;
                    color: #666666;
                    font-size: 16px;
                    font-weight: bold;
                }
            """)
        else:
            # When master is disabled:
            # 1. Show all device controls
            for widget in self.keylight_widgets:
                widget.setVisible(True)
            
            # 2. Restore sync controls visibility state
            if hasattr(self, '_sync_controls_state_before_master'):
                self.sync_container.setVisible(self._sync_controls_state_before_master)
                # Update sync reveal button appearance based on restored state
                if self._sync_controls_state_before_master:
                    self.sync_reveal_button.setText("⛓️‍💥")
                    self.sync_reveal_button.setToolTip("Hide sync controls")
                else:
                    self.sync_reveal_button.setText("🔗")
                    self.sync_reveal_button.setToolTip("Show sync controls")
                delattr(self, '_sync_controls_state_before_master')
            
            # 3. Re-enable sync reveal button
            self.sync_reveal_button.setEnabled(True)
            self.sync_reveal_button.setStyleSheet("")  # Reset to default style
    
    def update_master_device_toggle_appearance(self):
        """Update the master device toggle button appearance based on visibility"""
        if hasattr(self, 'master_device_widget') and hasattr(self, 'master_device_toggle'):
            is_visible = self.master_device_widget.isVisible()
            if is_visible:
                self.master_device_toggle.setText("M̄")  # M with overline
                self.master_device_toggle.setToolTip("Hide master device control")
            else:
                self.master_device_toggle.setText("M")
                self.master_device_toggle.setToolTip("Show master device control")
    
    def load_sync_settings(self):
        """Load sync settings from config"""
        self.temp_sync_enabled = self.device_config.get_app_setting('temp_sync_enabled', False)
        self.brightness_sync_enabled = self.device_config.get_app_setting('brightness_sync_enabled', False)
        self.all_sync_enabled = self.device_config.get_app_setting('all_sync_enabled', False)
        sync_controls_visible = self.device_config.get_app_setting('sync_controls_visible', False)
        
        # Apply loaded states to UI
        self.temp_sync_button.setChecked(self.temp_sync_enabled)
        self.brightness_sync_button.setChecked(self.brightness_sync_enabled)
        self.sync_all_button.setChecked(self.all_sync_enabled)
        self.sync_container.setVisible(sync_controls_visible)
        
        # Update sync reveal button appearance
        if sync_controls_visible:
            self.sync_reveal_button.setText("⛓️‍💥")
            self.sync_reveal_button.setToolTip("Hide sync controls")
        else:
            self.sync_reveal_button.setText("🔗")
            self.sync_reveal_button.setToolTip("Show sync controls")
    
    def save_sync_settings(self):
        """Save sync settings to config"""
        self.device_config.set_app_setting('temp_sync_enabled', self.temp_sync_enabled)
        self.device_config.set_app_setting('brightness_sync_enabled', self.brightness_sync_enabled)
        self.device_config.set_app_setting('all_sync_enabled', self.all_sync_enabled)
        self.device_config.set_app_setting('sync_controls_visible', self.sync_container.isVisible())
    
    def toggle_temp_sync(self):
        """Toggle temperature synchronization mode"""
        self.temp_sync_enabled = self.temp_sync_button.isChecked()
        
        # If all sync is enabled, disable it when individual sync is toggled
        if self.all_sync_enabled and self.temp_sync_enabled:
            self.all_sync_enabled = False
            self.sync_all_button.setChecked(False)
        
        # Save settings
        self.save_sync_settings()
    
    def toggle_brightness_sync(self):
        """Toggle brightness synchronization mode"""
        self.brightness_sync_enabled = self.brightness_sync_button.isChecked()
        
        # If all sync is enabled, disable it when individual sync is toggled
        if self.all_sync_enabled and self.brightness_sync_enabled:
            self.all_sync_enabled = False
            self.sync_all_button.setChecked(False)
        
        # Save settings
        self.save_sync_settings()
    
    def toggle_all_sync(self):
        """Toggle all settings synchronization mode"""
        self.all_sync_enabled = self.sync_all_button.isChecked()
        
        # When all sync is enabled, disable individual syncs
        if self.all_sync_enabled:
            self.temp_sync_enabled = False
            self.brightness_sync_enabled = False
            self.temp_sync_button.setChecked(False)
            self.brightness_sync_button.setChecked(False)
        
        # Save settings
        self.save_sync_settings()
    
    def sync_temperature_once(self):
        """One-time temperature sync from first device to all others"""
        if len(self.keylights) < 2:
            return
        
        reference_temp = self.keylights[0].temperature
        for i, widget in enumerate(self.keylight_widgets):
            if i == 0:
                continue
            # Skip locked devices
            if widget.is_locked:
                continue
            widget.keylight.temperature = reference_temp
            widget.temp_slider.setValue(reference_temp)
            widget.temp_label.setText(f"{widget.to_kelvin(reference_temp)}K")
            widget.update_power_button_style()
            widget.update_device()
        self.update_master_button_style()
    
    def sync_brightness_once(self):
        """One-time brightness sync from first device to all others"""
        if len(self.keylights) < 2:
            return
        
        reference_brightness = self.keylights[0].brightness
        for i, widget in enumerate(self.keylight_widgets):
            if i == 0:
                continue
            # Skip locked devices
            if widget.is_locked:
                continue
            widget.keylight.brightness = reference_brightness
            widget.brightness_slider.setValue(max(1, reference_brightness))
            widget.brightness_label.setText(f"{reference_brightness}%")
            widget.update_power_button_style()
            widget.update_device()
        self.update_master_button_style()
    
    def sync_all_once(self):
        """One-time sync of all settings from first device to all others"""
        if len(self.keylights) < 2:
            return
        
        reference_device = self.keylights[0]
        for i, widget in enumerate(self.keylight_widgets):
            if i == 0:
                continue
            
            # Skip locked devices
            if widget.is_locked:
                continue
            
            widget.keylight.on = reference_device.on
            widget.keylight.brightness = reference_device.brightness
            widget.keylight.temperature = reference_device.temperature
            
            widget.power_button.setChecked(reference_device.on)
            widget.brightness_slider.setValue(max(1, reference_device.brightness))
            widget.brightness_label.setText(f"{reference_device.brightness}%")
            widget.temp_slider.setValue(reference_device.temperature)
            widget.temp_label.setText(f"{widget.to_kelvin(reference_device.temperature)}K")
            widget.update_power_button_style()
            widget.update_device()
        
        self.update_master_button_state()
        self.update_master_button_style()
    
    def propagate_sync_changes(self, source_widget, changed_attribute, value):
        """Schedule throttled sync changes to prevent network flooding"""
        if len(self.keylights) < 2:
            return
        
        # Check if sync is enabled for this attribute
        should_sync = False
        if self.all_sync_enabled:
            should_sync = True
        elif self.temp_sync_enabled and changed_attribute == 'temperature':
            should_sync = True
        elif self.brightness_sync_enabled and changed_attribute == 'brightness':
            should_sync = True
        
        if not should_sync:
            return
        
        # Find source widget index
        source_index = -1
        for i, widget in enumerate(self.keylight_widgets):
            if widget == source_widget:
                source_index = i
                break
        
        if source_index == -1:
            return
        
        # Store pending updates (only UI updates immediately, device updates are throttled)
        for i, widget in enumerate(self.keylight_widgets):
            if i == source_index:  # Skip source widget
                continue
            
            # Skip locked devices
            if widget.is_locked:
                continue
            
            # Immediate UI updates (no network calls)
            if self.all_sync_enabled:
                if changed_attribute == 'temperature':
                    widget.keylight.temperature = value
                    widget.temp_slider.setValue(value)
                    widget.temp_label.setText(f"{widget.to_kelvin(value)}K")
                elif changed_attribute == 'brightness':
                    widget.keylight.brightness = value
                    widget.brightness_slider.setValue(max(1, value))
                    widget.brightness_label.setText(f"{value}%")
                elif changed_attribute == 'power':
                    widget.keylight.on = value
                    widget.power_button.setChecked(value)
                
                widget.update_power_button_style()
                # Store for throttled device update
                self.pending_sync_updates[i] = widget
                
            elif self.temp_sync_enabled and changed_attribute == 'temperature':
                widget.keylight.temperature = value
                widget.temp_slider.setValue(value)
                widget.temp_label.setText(f"{widget.to_kelvin(value)}K")
                widget.update_power_button_style()
                self.pending_sync_updates[i] = widget
                
            elif self.brightness_sync_enabled and changed_attribute == 'brightness':
                widget.keylight.brightness = value
                widget.brightness_slider.setValue(max(1, value))
                widget.brightness_label.setText(f"{value}%")
                widget.update_power_button_style()
                self.pending_sync_updates[i] = widget
        
        # Start throttled timer for device updates
        if self.pending_sync_updates and not self.sync_timer.isActive():
            self.sync_timer.start()
        
        self.update_master_button_style()
    
    def process_pending_sync(self):
        """Process pending sync updates to devices (throttled)"""
        if not self.pending_sync_updates:
            self.sync_timer.stop()
            return
        
        # Send updates to devices
        for widget in self.pending_sync_updates.values():
            widget.update_device()
        
        # Clear pending updates
        self.pending_sync_updates.clear()
        self.sync_timer.stop()
        
    def update_master_button_style(self):
        """Update master power button appearance with gradient of all device colors"""
        if self.master_power_button.isChecked() and self.keylights:
            # Get colors from all devices
            device_colors = []
            for widget in self.keylight_widgets:
                if widget.keylight.on:
                    # Get the color from each device
                    r, g, b = widget.to_slider_color(widget.keylight.temperature)
                    alpha = widget.keylight.brightness / 100.0
                    device_colors.append((r, g, b, alpha))
            
            if device_colors:
                if len(device_colors) == 1:
                    # Single device - use its color
                    r, g, b, alpha = device_colors[0]
                    color = f"rgba({r}, {g}, {b}, {alpha})"
                    self.master_power_button.setStyleSheet(f"""
                        QPushButton#masterPowerButton {{
                            background-color: {color};
                            border: 2px solid rgba({r}, {g}, {b}, 1.0);
                            border-radius: 12px;
                            font-size: 20px;
                            color: #ffffff;
                            padding-bottom: 1px;
                        }}
                    """)
                else:
                    # Multiple devices - create gradient
                    gradient_stops = []
                    for i, (r, g, b, alpha) in enumerate(device_colors):
                        position = i / (len(device_colors) - 1)
                        gradient_stops.append(f"stop:{position:.2f} rgba({r}, {g}, {b}, {alpha})")
                    
                    gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:0, " + ", ".join(gradient_stops) + ")"
                    
                    # Average color for border
                    avg_r = sum(r for r, g, b, a in device_colors) // len(device_colors)
                    avg_g = sum(g for r, g, b, a in device_colors) // len(device_colors)
                    avg_b = sum(b for r, g, b, a in device_colors) // len(device_colors)
                    
                    self.master_power_button.setStyleSheet(f"""
                        QPushButton#masterPowerButton {{
                            background: {gradient};
                            border: 2px solid rgb({avg_r}, {avg_g}, {avg_b});
                            border-radius: 12px;
                            font-size: 20px;
                            color: #ffffff;
                            padding-bottom: 1px;
                        }}
                    """)
            else:
                # No devices on - fallback to default
                self._apply_default_master_style()
        else:
            self._apply_default_master_style()
    
    def _apply_default_master_style(self):
        """Apply default master button style when off or no devices"""
        self.master_power_button.setStyleSheet("""
            QPushButton#masterPowerButton {
                background-color: transparent;
                border: 2px solid #555;
                border-radius: 12px;
                color: #555;
                font-size: 20px;
                padding-bottom: 1px;
            }
        """)
    
    def update_master_button_state(self):
        """Update master button state based on all device states"""
        if not self.keylights:
            self.master_power_button.setChecked(False)
            self.update_master_button_style()
            return
            
        # Check if all lights are on
        all_on = all(kl.on for kl in self.keylights)
        self.master_power_button.setChecked(all_on)
        self.update_master_button_style()
    
    def apply_blur_effect(self):
        """Apply blur effect to the application content"""
        # Create blur effect for the entire central widget
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(8)
        
        # Apply blur to the central widget (contains all app content)
        self.centralWidget().setGraphicsEffect(blur_effect)
    
    def remove_blur_effect(self):
        """Remove blur effect from the application content"""
        self.centralWidget().setGraphicsEffect(None)
    
    def prepare_for_dialog(self):
        """Prepare main window for dialog - apply blur and ensure adequate size"""
        self.apply_blur_effect()
        
        # Store original size in case we need to restore it
        self.original_size = self.size()
        
        # Dialog is 350x140, ensure window is large enough
        dialog_height = 140
        current_height = self.height()
        
        # If current window is too small for dialog, grow it
        if current_height < dialog_height + 100:  # Add buffer for dialog positioning
            new_height = dialog_height + 200
            self.resize(self.width(), new_height)
    
    def cleanup_after_dialog(self):
        """Cleanup after dialog closes - remove blur and restore size"""
        self.remove_blur_effect()
        
        # Restore original size if we have it
        if hasattr(self, 'original_size'):
            self.resize(self.original_size)
            delattr(self, 'original_size')
        
    def apply_dark_theme(self):
        """Apply dark theme similar to professional control center apps"""
        style = """
        QMainWindow {
            background-color: #1a1a1a;
        }
        
        QWidget {
            background-color: #1a1a1a;
        }
        
        QScrollArea {
            background-color: #1a1a1a;
            border: none;
        }
        
        QScrollArea > QWidget > QWidget {
            background-color: #1a1a1a;
        }
        
        QScrollArea > QWidget > QViewport {
            background-color: #1a1a1a;
        }
        
        QFrame#KeyLightWidget {
            background-color: #2a2a2a;
            border-radius: 12px;
            border: 1px solid #3a3a3a;
        }
        
        QFrame#KeyLightWidget::hover{
            border: 2px solid #aaaaaa;
        }
        
        QFrame#MasterDeviceWidget {
            background-color: #333333;
            border-radius: 12px;
            border: 1px solid #4a4a4a;
            margin-bottom: 8px;
        }
        
        QFrame#MasterDeviceWidget::hover{
            border: 1px solid #5a5a5a;
            background-color: #3a3a3a;
        }
        
        QFrame#MasterPanel {
            background-color: #2a2a2a;
            border-radius: 12px;
            border: 1px solid #3a3a3a;
            margin: 8px;
        }
        
        QLabel#masterLabel {
            color: #ffffff;
            font-size: 14px;
            font-weight: 500;
        }
        
        QFrame#separator {
            color: #555555;
            background-color: #555555;
            max-width: 1px;
        }
        
        QPushButton#syncRevealButton {
            background-color: #3a3a3a;
            border: 1px solid #555555;
            border-radius: 12px;
            color: #888888;
            font-size: 16px;
            font-weight: bold;
        }
        
        QPushButton#syncRevealButton:hover {
            background-color: #4a4a4a;
            border: 1px solid #666666;
            color: #cccccc;
        }
        
        QPushButton#syncRevealButton:pressed {
            background-color: #00E5FF;
            color: #000000;
            border: 1px solid #00C4E5;
        }
        
        QPushButton#syncButton {
            background-color: transparent;
            border: 1px solid #555555;
            border-radius: 6px;
            color: #cccccc;
            font-size: 14px;
        }
        
        QPushButton#syncButton:hover {
            background-color: #4a4a4a;
            border: 1px solid #666666;
        }
        
        QPushButton#syncButton:pressed {
            background-color: #00E5FF;
            color: #000000;
            border: 1px solid #00C4E5;
        }
        
        QPushButton#syncButton:checked {
            background-color: #00E5FF;
            color: #000000;
            border: 2px solid #00C4E5;
        }
        
        QPushButton#syncButton:checked:hover {
            background-color: #00D4FF;
            border: 2px solid #00B4D5;
        }
        
        QLabel#deviceName {
            color: #ffffff;
            font-size: 14px;
            font-weight: 500;
            margin-left: -2px;
        }
        
        QLabel#lockIcon {
            color: #ff6b35;
            font-size: 14px;
            margin: 0px;
            padding: 0px;
        }
        
        QLabel#sliderIcon {
            color: #888888;
            font-size: 16px;
        }
        
        QLabel#sliderValue {
            color: #aaaaaa;
            font-size: 12px;
        }
        
        QPushButton#powerButton {
            border-radius: 18px;
            background-color: transparent;
            border: 2px solid #555555;
        }
        
        QPushButton#powerButton:checked {
            background-color: #00E5FF;
            border: 2px solid #00E5FF;
        }
        
        QPushButton#menuButton {
            background-color: transparent;
            color: #888888;
            border: none;
            font-size: 18px;
            font-weight: bold;
        }
        
        QSlider {
            min-height: 22px;   /* for the handles to be round */
        }
        
        QPushButton#menuButton:hover {
            color: #ffffff;
        }
        
        QSlider::groove:horizontal {
            height: 6px;
            background: #3a3a3a;
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 9px;
            background: #555555;
            border: 1px solid transparent;
        }
        
        QSlider::handle:horizontal::hover {
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 9px;
            background: #666666;
            border: 1px solid transparent;
        }
        
        QSlider#brightnessSlider::groove:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #222222, stop:1 #ffff88);
        }
        
        
        QSlider#temperatureSlider::groove:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #88aaff, stop:1 #ff9944);
        }
        
        QToolTip {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        }
        """
        self.setStyleSheet(style)
        
    def setup_system_tray(self):
        """Setup system tray icon"""
        # Create a simple icon (circle)
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor("#00E5FF")))
        painter.setPen(QPen(Qt.NoPen))
        painter.drawEllipse(8, 8, 48, 48)
        painter.end()
        
        icon = QIcon(pixmap)
        
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Key Light Control")
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+Q or Cmd+Q to quit
        quit_shortcut = QShortcut(QKeySequence.Quit, self)
        quit_shortcut.activated.connect(self.quit_application)
        
        # Escape to minimize to tray
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self.hide)
        
    def quit_application(self):
        """Properly quit the application"""
        self.discovery.stop_discovery()
        QApplication.quit()
        
    def on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
    
    def fetch_device_mac(self, device_info):
        """Handle MAC address fetch request from discovery thread"""
        asyncio.create_task(self._fetch_and_add_device(device_info))
    
    async def _fetch_and_add_device(self, device_info):
        """Fetch MAC address and add device"""
        mac_address = await self.discovery._get_device_mac_address(
            device_info['ip'], 
            device_info['port']
        )
        device_info['mac_address'] = mac_address
        self.discovery.device_found.emit(device_info)
                
    def add_keylight(self, device_info):
        """Add a discovered Key Light"""
        # Check if already added
        for kl in self.keylights:
            if kl.ip == device_info['ip']:
                return
                
        # Create KeyLight object
        keylight = KeyLight(
            name=device_info['name'],
            ip=device_info['ip'],
            port=device_info.get('port', 9123),
            mac_address=device_info.get('mac_address', '')
        )
        self.keylights.append(keylight)
        
        # Create widget
        widget = KeyLightWidget(keylight, self)
        widget.power_state_changed.connect(self.update_master_button_state)
        
        # Apply custom label if it exists
        custom_label = self.device_config.get_label(keylight.mac_address, keylight.name)
        widget.name_label.setText(custom_label)
        
        self.keylight_widgets.append(widget)
        
        # Add to layout
        self.devices_layout.addWidget(widget)
        
        # Update master device widget
        if self.master_device_widget:
            self.master_device_widget.update_device_count()
            # Update from first device if this is the first device added
            if len(self.keylights) == 1:
                self.master_device_widget.update_from_devices()
        
        # If master is enabled, hide this new device widget
        if hasattr(self, 'master_device_widget') and self.master_device_widget.isVisible():
            widget.setVisible(False)
        
        # Adjust window height dynamically
        self.adjust_window_size()
        
        # Update master button state
        self.update_master_button_state()
        
    def adjust_window_size(self):
        """Dynamically adjust window size based on visible controls"""
        master_panel_height = 60  # Height of master control panel
        title_bar = 35  # Approximate title bar height
        margins = 16  # Top and bottom margins
        
        # Check if master device control is visible
        master_device_visible = (hasattr(self, 'master_device_widget') and 
                               self.master_device_widget.isVisible())
        
        if master_device_visible:
            # Only master device control is visible - calculate height for master only
            master_device_height = 140  # Approximate height of master device widget
            needed_height = master_panel_height + master_device_height + margins + title_bar
        elif len(self.keylights) == 0:
            # No devices, just master panel
            needed_height = master_panel_height + title_bar + margins + 50  # Extra space for empty state
        else:
            # Individual device controls are visible
            num_lights = len(self.keylights)
            spacing_between = (num_lights - 1) * 8 if num_lights > 1 else 0
            needed_height = master_panel_height + (num_lights * self.widget_height) + spacing_between + margins + title_bar
        
        # Cap at maximum height
        new_height = min(needed_height, self.max_height)
        
        # Set the window size
        self.setFixedHeight(new_height)
        
        # If we're at max height, ensure scrolling is enabled
        if needed_height > self.max_height:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
    def closeEvent(self, event):
        """Handle close event - minimize to tray instead"""
        # If Shift is held, quit the app completely
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            self.discovery.stop_discovery()
            QApplication.quit()
            event.accept()
        else:
            # Otherwise minimize to tray
            event.ignore()
            self.hide()
            if self.tray_icon.isSystemTrayAvailable():
                self.tray_icon.showMessage(
                    "Key Light Control",
                    "Application minimized to tray. Right-click tray icon to quit.",
                    QSystemTrayIcon.Information,
                    2000
                )
        
        
from utils.single_instance import SingleInstance


def main():
    """Main entry point"""
    # Handle command-line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Key Light Controller')
    parser.add_argument('--version', action='version', version=f'Key Light Controller {__version__}')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    
    # Check for single instance
    single_instance = SingleInstance()
    
    if single_instance.is_running():
        print("Key Light Control is already running.")
        # Try to bring existing instance to front by sending a signal
        try:
            # Connect to the existing instance's socket to signal it
            signal_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            signal_socket.connect(('127.0.0.1', 45654))
            signal_socket.close()
        except:
            pass
        sys.exit(0)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Key Light Control")
    
    # Set up asyncio integration
    try:
        import qasync
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
    except ImportError:
        print("Warning: qasync not found. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "qasync"])
        import qasync
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
    
    controller = KeyLightController()
    controller.show()
    
    # Set up a timer to check for activation signals from other instances
    def check_for_activation():
        try:
            # Non-blocking accept
            single_instance.socket.setblocking(False)
            conn, addr = single_instance.socket.accept()
            conn.close()
            # Another instance tried to start, bring this one to front
            controller.show()
            controller.raise_()
            controller.activateWindow()
        except:
            pass
    
    from PySide6.QtCore import QTimer
    activation_timer = QTimer()
    activation_timer.timeout.connect(check_for_activation)
    activation_timer.start(100)  # Check every 100ms
    
    try:
        with loop:
            loop.run_forever()
    finally:
        single_instance.cleanup()
        

if __name__ == "__main__":
    main()
