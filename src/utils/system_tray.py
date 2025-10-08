from __future__ import annotations

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QBrush,
    QColor,
    QPen,
    QAction,
    QRadialGradient,
    QPainterPath,
)
from PySide6.QtCore import Qt, QPointF


def make_keylight_icon() -> QIcon:
    """Draw a stylized Key Light: tilted dark rectangle on a stand with a bright center."""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    cx = size / 2
    top_y = 14.0
    panel_h = 26.0
    bottom_y = top_y + panel_h
    top_w = 44.0
    bot_w = 34.0

    # Panel shape (trapezoid for perspective)
    panel = QPainterPath()
    points = [
        QPointF(cx - top_w / 2, top_y),
        QPointF(cx + top_w / 2, top_y),
        QPointF(cx + bot_w / 2, bottom_y),
        QPointF(cx - bot_w / 2, bottom_y),
    ]
    panel.moveTo(points[0])
    for pt in points[1:]:
        panel.lineTo(pt)
    panel.closeSubpath()

    # Panel fill
    p.setPen(QPen(QColor("#444444"), 1))
    p.setBrush(QBrush(QColor("#26292d")))
    p.drawPath(panel)

    # Inner glow (bright light) clipped to panel
    p.save()
    p.setClipPath(panel)
    glow_center = QPointF(cx, top_y + panel_h * 0.55)
    glow = QRadialGradient(glow_center, panel_h * 0.7)
    glow.setColorAt(0.0, QColor(255, 255, 255, 235))
    glow.setColorAt(0.35, QColor(240, 250, 255, 180))
    glow.setColorAt(0.65, QColor(0, 229, 255, 90))
    glow.setColorAt(1.0, QColor(0, 229, 255, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(glow))
    # Draw a large ellipse covering panel bounds for gradient
    p.drawEllipse(glow_center, top_w * 0.45, panel_h * 0.6)
    p.restore()

    # Stand (stem + base)
    stem_w = 5
    stem_h = 10
    stem_x = int(cx - stem_w / 2)
    stem_y = int(bottom_y + 4)
    p.setPen(QPen(QColor("#55585d"), 1))
    p.setBrush(QBrush(QColor("#3a3d42")))
    p.drawRoundedRect(stem_x, stem_y, stem_w, stem_h, 2, 2)

    base_w = 26
    base_h = 6
    base_x = int(cx - base_w / 2)
    base_y = stem_y + stem_h - 1
    p.setPen(QPen(QColor("#4a4d52"), 1))
    p.setBrush(QBrush(QColor("#2f3237")))
    p.drawEllipse(base_x, base_y, base_w, base_h)

    p.end()
    return QIcon(pm)


def create_tray_icon(window) -> QSystemTrayIcon:
    """Create and show the system tray icon and menu for the given window."""
    icon = make_keylight_icon()
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
