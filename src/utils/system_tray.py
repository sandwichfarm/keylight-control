from __future__ import annotations

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QPen, QAction
from PySide6.QtCore import Qt


def make_circle_icon(color: str = "#00E5FF") -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(QPen(Qt.NoPen))
    painter.drawEllipse(8, 8, 48, 48)
    painter.end()
    return QIcon(pixmap)


def create_tray_icon(window) -> QSystemTrayIcon:
    """Create and show the system tray icon and menu for the given window."""
    icon = make_circle_icon("#00E5FF")
    tray = QSystemTrayIcon(icon, window)
    tray.setToolTip("Key Light Control")

    menu = QMenu()

    show_action = QAction("Show", window)
    show_action.triggered.connect(window.show)
    menu.addAction(show_action)

    quit_action = QAction("Quit", window)
    quit_action.triggered.connect(window.quit_application)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)
    tray.activated.connect(window.on_tray_activated)
    tray.show()

    return tray

