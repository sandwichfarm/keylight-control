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
from typing import List, Dict, Optional
from dataclasses import dataclass

# Import local modules
from config import DeviceConfig

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
        QScrollArea, QSizePolicy, QDialog, QLineEdit, QDialogButtonBox
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


@dataclass
class KeyLight:
    """Represents a Key Light device"""
    name: str
    ip: str
    port: int = 9123
    mac_address: str = ""
    on: bool = False
    brightness: int = 50
    temperature: int = 200  # 143-344 range (7000K-2900K)
    

class KeyLightDiscovery(QObject):
    """Discovers Key Lights on the network using mDNS"""
    device_found = Signal(dict)
    mac_fetch_requested = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.zeroconf = Zeroconf()
        self.browser = None
        
    def start_discovery(self):
        """Start discovering Key Light devices"""
        self.browser = ServiceBrowser(
            self.zeroconf,
            "_elg._tcp.local.",
            handlers=[self._on_service_state_change]
        )
        
    def _on_service_state_change(self, zeroconf, service_type, name, state_change):
        """Handle service discovery events"""
        from zeroconf import ServiceStateChange
        if state_change == ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                device_info = {
                    'name': name.replace('._elg._tcp.local.', ''),
                    'ip': '.'.join(map(str, info.addresses[0])),
                    'port': info.port
                }
                # Request MAC address fetch from main thread
                self.mac_fetch_requested.emit(device_info)
    
    async def _fetch_mac_address(self, device_info):
        """Fetch MAC address from device and emit the complete device info"""
        mac_address = await self._get_device_mac_address(device_info['ip'], device_info['port'])
        device_info['mac_address'] = mac_address
        self.device_found.emit(device_info)
    
    async def _get_device_mac_address(self, ip: str, port: int) -> str:
        """Get MAC address from device API or ARP table"""
        # First try to get it from the device's accessory-info endpoint
        try:
            url = f"http://{ip}:{port}/elgato/accessory-info"
            timeout = aiohttp.ClientTimeout(total=3)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Look for MAC address in various possible fields
                        mac = data.get('macAddress') or data.get('mac') or data.get('serialNumber')
                        if mac:
                            return mac.upper().replace(':', '').replace('-', '')
        except Exception:
            pass
        
        # Fallback: try to get MAC from ARP table using system command
        try:
            import subprocess
            result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if ip in line and 'incomplete' not in line.lower():
                        parts = line.split()
                        for part in parts:
                            if ':' in part and len(part.replace(':', '')) == 12:
                                return part.upper().replace(':', '')
        except Exception:
            pass
        
        # Last resort: use IP address as a fallback identifier
        return f"IP_{ip.replace('.', '_')}"
                
    def stop_discovery(self):
        """Stop discovery and cleanup"""
        if self.browser:
            self.browser.cancel()
        self.zeroconf.close()


class KeyLightWidget(QFrame):
    """Widget for controlling a single Key Light"""
    power_state_changed = Signal()
    
    def __init__(self, keylight: KeyLight, parent=None):
        super().__init__(parent)
        self.keylight = keylight
        self.pending_update = None
        self.last_update_time = 0
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.process_pending_update)
        self.update_timer.setInterval(50)  # Process updates every 50ms max
        self.setup_ui()
        self.update_from_device()
        
    def setup_ui(self):
        """Setup the UI to match Elgato Control Center style"""
        self.setObjectName("KeyLightWidget")
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header with device name and menu button
        header_layout = QHBoxLayout()
        
        # Power button (circular with icon)
        self.power_button = QPushButton("⏻")
        self.power_button.setCheckable(True)
        self.power_button.setObjectName("powerButton")
        self.power_button.setFixedSize(36, 36)
        self.power_button.clicked.connect(self.toggle_power)
        
        # Device name
        self.name_label = QLabel(self.keylight.name)
        self.name_label.setObjectName("deviceName")
        
        # Menu button (three dots)
        self.menu_button = QPushButton("⋮")
        self.menu_button.setObjectName("menuButton")
        self.menu_button.setFixedSize(30, 30)
        self.menu_button.clicked.connect(self.show_device_menu)
        
        header_layout.addWidget(self.power_button)
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
        return round((-4100 * value) / 201 + 1993300 / 201)

    @staticmethod
    def to_slider_color(value: int) -> tuple[int, int, int]:
        """Interpolate between slider left color (#88aaff) and right color (#ff9944)"""
        left = (136, 170, 255)  # #88aaff
        right = (255, 153, 68)  # #ff9944
        t = (value - 143) / (344 - 143)
        r = int(left[0] + (right[0] - left[0]) * t)
        g = int(left[1] + (right[1] - left[1]) * t)
        b = int(left[2] + (right[2] - left[2]) * t)
        return r, g, b

    @staticmethod
    def percent_to_hex_alpha(percent: float):
        """Convert 0-100 percent to two-digit hex alpha ('FF' for 100%, '00' for 0%)"""
        # Clamp percent to 0-100
        percent = max(0.0, min(100.0, percent))
        alpha = int(round((percent / 100) * 255))
        return f"{alpha:02X}"

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
        """Async update to device via HTTP API"""
        url = f"http://{self.keylight.ip}:{self.keylight.port}/elgato/lights"
        data = {
            "numberOfLights": 1,
            "lights": [{
                "on": 1 if self.keylight.on else 0,
                "brightness": self.keylight.brightness,
                "temperature": self.keylight.temperature
            }]
        }
        
        try:
            # Set a timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=2)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.put(url, json=data) as response:
                    if response.status != 200:
                        print(f"Failed to update {self.keylight.name}: {response.status}")
        except asyncio.TimeoutError:
            print(f"Timeout updating {self.keylight.name}")
        except Exception as e:
            print(f"Error updating {self.keylight.name}: {e}")
            
    def update_from_device(self):
        """Fetch current state from device"""
        asyncio.create_task(self._update_from_device_async())
        
    async def _update_from_device_async(self):
        """Async fetch from device via HTTP API"""
        url = f"http://{self.keylight.ip}:{self.keylight.port}/elgato/lights"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        light_data = data['lights'][0]
                        self.keylight.on = bool(light_data['on'])
                        self.keylight.brightness = light_data['brightness']
                        self.keylight.temperature = light_data['temperature']
                        
                        # Update UI
                        self.power_button.setChecked(self.keylight.on)
                        self.brightness_slider.setValue(max(1, self.keylight.brightness))  # Ensure min 1%
                        self.temp_slider.setValue(self.keylight.temperature)
                        self.update_power_button_style()
                        self.power_state_changed.emit()
        except Exception as e:
            print(f"Error fetching state from {self.keylight.name}: {e}")
    
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


class KeyLightController(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.keylights = []
        self.keylight_widgets = []
        self.device_config = DeviceConfig()
        self.discovery = KeyLightDiscovery()
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
        
        self.scroll_area.setWidget(self.devices_container)
        main_layout.addWidget(self.scroll_area)
        
    def setup_master_controls(self):
        """Setup master control panel with 30% smaller buttons"""
        self.master_panel = QFrame()
        self.master_panel.setObjectName("MasterPanel")
        self.master_panel.setFixedHeight(60)
        
        master_layout = QHBoxLayout(self.master_panel)
        master_layout.setContentsMargins(16, 8, 16, 8)
        master_layout.setSpacing(12)
        
        # Master power button (30% smaller than device buttons: 36px -> 25px)
        self.master_power_button = QPushButton("⏻")
        self.master_power_button.setCheckable(True)
        self.master_power_button.setObjectName("masterPowerButton")
        self.master_power_button.setFixedSize(25, 25)
        self.master_power_button.clicked.connect(self.toggle_all_lights)
        
        master_layout.addWidget(self.master_power_button)
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
        
        QLabel#deviceName {
            color: #ffffff;
            font-size: 14px;
            font-weight: 500;
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
        
        # Adjust window height dynamically
        self.adjust_window_size()
        
        # Update master button state
        self.update_master_button_state()
        
    def adjust_window_size(self):
        """Dynamically adjust window size based on number of lights"""
        num_lights = len(self.keylights)
        
        if num_lights == 0:
            # Show master panel even with no devices
            master_panel_height = 60
            title_bar = 35
            margins = 16
            self.setFixedHeight(master_panel_height + title_bar + margins + 50)  # Extra space for empty state
            return
        
        # Calculate needed height (widgets + spacing + margins)
        # master panel + widget_height * num_lights + spacing between widgets + top/bottom margins + title bar
        master_panel_height = 60  # Height of master control panel
        spacing_between = (num_lights - 1) * 8 if num_lights > 1 else 0
        margins = 16  # 8px top + 8px bottom
        title_bar = 35  # Approximate title bar height
        
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
        
        
class SingleInstance:
    """Ensures only one instance of the application runs"""
    def __init__(self, port=45654):
        self.port = port
        self.socket = None
        
    def is_running(self):
        """Check if another instance is already running"""
        try:
            # Try to bind to a local socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(('127.0.0.1', self.port))
            self.socket.listen(1)
            return False  # We successfully bound, so no other instance is running
        except OSError:
            return True  # Another instance is already running
            
    def cleanup(self):
        """Clean up the socket"""
        if self.socket:
            self.socket.close()


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