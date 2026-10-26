"""Run with QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m unittest discover -s tests."""
import os
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMainWindow

from config import DeviceConfig
from core.models import KeyLight
from ui.widgets.keylight_widget import KeyLightWidget


class DeviceRenameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {"XDG_CONFIG_HOME": self.directory.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.window = QMainWindow()
        self.window.device_config = DeviceConfig()
        self.light = KeyLight("Original", "127.0.0.1", mac_address="test-mac")
        with patch.object(KeyLightWidget, "update_from_device"), patch.object(KeyLightWidget, "load_lock_state"):
            self.widget = KeyLightWidget(self.light, self.window)
        self.addCleanup(self.window.deleteLater)

    def rename(self, name, accept=True):
        self.widget.rename_device(self.window)
        dialog = self.widget._rename_dialog
        dialog.name_input.setText(name)
        if accept:
            dialog.accept()
        else:
            dialog.reject()

    def test_save_updates_display_and_survives_reload(self):
        self.rename("Desk Light")
        self.assertEqual(self.widget.name_label.text(), "Desk Light")
        self.assertEqual(DeviceConfig().get_label("test-mac", "Original"), "Desk Light")
        self.rename("New Alias")
        self.assertEqual(DeviceConfig().get_all_devices()["test-mac"]["original_name"], "Original")

    def test_cancel_and_empty_name_preserve_alias(self):
        self.rename("Desk Light")
        self.rename("Cancelled", accept=False)
        self.rename("   ")
        self.assertEqual(self.widget.name_label.text(), "Desk Light")
        self.assertEqual(DeviceConfig().get_label("test-mac", "Original"), "Desk Light")

    def test_save_failure_preserves_label_and_reports_error(self):
        with patch.object(self.window.device_config, "set_label", return_value=False), patch("ui.widgets.keylight_widget.QMessageBox.warning") as warning:
            self.rename("Unsaved")
        self.assertEqual(self.widget.name_label.text(), "Original")
        warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
