"""Run with QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m unittest discover -s tests."""
import unittest
from unittest.mock import Mock

from PySide6.QtWidgets import QApplication, QMainWindow

from core.models import KeyLight
from utils.system_tray import create_tray_icon


def action(menu, label):
    return next(item for item in menu.actions() if item.text() == label)


class TrayControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = QMainWindow()
        self.window.keylights = []
        self.window.device_config = Mock()
        self.window.device_config.get_label.side_effect = lambda mac, name: name
        self.window._api = Mock()
        self.window.quit_application = Mock()
        self.window.on_tray_activated = Mock()
        self.tray = create_tray_icon(self.window)
        self.menu = self.tray.contextMenu()
        self.addCleanup(self.window.deleteLater)
        self.addCleanup(self.tray.hide)

    def discover(self):
        self.window.keylights.extend([
            KeyLight("Left", "127.0.0.1", mac_address="left"),
            KeyLight("Right", "127.0.0.2", mac_address="right", on=True),
        ])
        self.menu.aboutToShow.emit()

    def test_disabled_until_discovery_then_all_power_actions(self):
        self.assertFalse(action(self.menu, "Toggle all lights").isEnabled())
        self.assertFalse(action(self.menu, "Individual lights").isEnabled())
        self.discover()
        action(self.menu, "Toggle all lights").trigger()
        self.window._api.handle_request.assert_called_with("lights.toggle", {})
        for label, state in (("All lights on", True), ("All lights off", False)):
            self.window._api.reset_mock()
            action(self.menu, label).trigger()
            self.assertEqual(self.window._api.handle_request.call_count, 2)
            self.window._api.handle_request.assert_any_call("lights.set", {"id": 0, "on": state})
            self.window._api.handle_request.assert_any_call("lights.set", {"id": 1, "on": state})

    def test_individual_power_and_presets_target_selected_device(self):
        self.discover()
        devices = action(self.menu, "Individual lights").menu()
        for index, name, state in ((0, "Left", True), (1, "Right", False)):
            device = action(devices, name).menu()
            action(device, "On").trigger()
            self.window._api.handle_request.assert_called_with("lights.set", {"id": index, "on": state})
            action(action(device, "Brightness (50%)").menu(), "75%").trigger()
            self.window._api.handle_request.assert_called_with("lights.set", {"id": index, "brightness": 75})
            action(action(device, "Color temperature (5000 K)").menu(), "5600 K").trigger()
            self.window._api.handle_request.assert_called_with("lights.set", {"id": index, "temperature": 179})

    def test_refresh_updates_alias_state_and_tooltip_without_duplicates(self):
        self.discover()
        self.window.device_config.get_label.side_effect = lambda mac, name: "Desk & Key" if mac == "left" else name
        self.window.keylights[0].on = True
        self.menu.aboutToShow.emit()
        devices = action(self.menu, "Individual lights").menu()
        self.assertEqual(len(devices.actions()), 2)
        self.assertTrue(action(action(devices, "Desk && Key").menu(), "On").isChecked())
        self.assertEqual(self.tray.toolTip(), "Key Lights: 2 of 2 on")

    def test_existing_show_hide_and_quit_actions(self):
        action(self.menu, "Show").trigger()
        self.assertTrue(self.window.isVisible())
        self.menu.aboutToShow.emit()
        action(self.menu, "Hide").trigger()
        self.assertFalse(self.window.isVisible())
        action(self.menu, "Quit").trigger()
        self.window.quit_application.assert_called_once()


if __name__ == "__main__":
    unittest.main()
