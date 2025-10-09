from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox
from PySide6.QtGui import QIcon


class RenameDeviceDialog(QDialog):
    """Simple, functional dialog for renaming devices."""

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
        self.setStyleSheet(
            """
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
            """
        )

    def get_name(self) -> str:
        """Get the entered name."""
        return self.name_input.text().strip()

