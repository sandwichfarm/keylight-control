from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider


class JumpSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            new_val = self.minimum() + (self.maximum() - self.minimum()) * event.position().x() / self.width()
            self.setValue(round(new_val))
            event.accept()
        super().mousePressEvent(event)

