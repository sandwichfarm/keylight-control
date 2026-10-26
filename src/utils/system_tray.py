from __future__ import annotations

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QBrush,
    QColor,
    QPen,
    QRadialGradient,
    QPainterPath,
)
from PySide6.QtCore import Qt, QPointF, QTimer


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

    menu = QMenu(window)
    toggle_action = menu.addAction("Toggle all lights")
    toggle_action.triggered.connect(lambda: window._api.handle_request("lights.toggle", {}))

    def set_all(on):
        for index in range(len(window.keylights)):
            window._api.handle_request("lights.set", {"id": index, "on": on})

    on_action = menu.addAction("All lights on", lambda: set_all(True))
    off_action = menu.addAction("All lights off", lambda: set_all(False))
    menu.addSeparator()
    devices_menu = menu.addMenu("Individual lights")
    menu.addSeparator()
    show_action = menu.addAction("Show")

    def show_controls():
        if window.isVisible():
            window.hide()
        else:
            window.show()
            window.raise_()
            window.activateWindow()

    show_action.triggered.connect(show_controls)
    menu.addAction("Quit", window.quit_application)
    # Keep menu actions alive: KDE exports them over D-Bus. Update their
    # labels/state instead of rebuilding the menu while it may be open.
    entries = {}

    def refresh():
        show_action.setText("Hide" if window.isVisible() else "Show")
        available = bool(window.keylights)
        for action in (toggle_action, on_action, off_action):
            action.setEnabled(available)
        devices_menu.setEnabled(available)
        for index, light in enumerate(window.keylights):
            if index not in entries:
                sub = devices_menu.addMenu(light.name)
                power = sub.addAction("On")
                power.setCheckable(True)
                power.triggered.connect(
                    lambda checked, i=index: window._api.handle_request("lights.set", {"id": i, "on": checked})
                )
                brightness = sub.addMenu("Brightness")
                for percent in (10, 25, 50, 75, 100):
                    brightness.addAction(f"{percent}%",
                        lambda checked=False, i=index, value=percent: window._api.handle_request("lights.set", {"id": i, "brightness": value}))
                temperature = sub.addMenu("Color temperature")
                for kelvin in (2900, 3200, 4000, 5000, 5600, 6500, 7000):
                    temperature.addAction(f"{kelvin} K",
                        lambda checked=False, i=index, value=kelvin: window._api.handle_request("lights.set", {"id": i, "temperature": round(1000000 / value)}))
                entries[index] = (sub, power, brightness, temperature)
            sub, power, brightness, temperature = entries[index]
            name = window.device_config.get_label(light.mac_address, light.name)
            sub.setTitle(name.replace("&", "&&"))
            power.setChecked(light.on)
            brightness.setTitle(f"Brightness ({light.brightness}%)")
            temperature.setTitle(f"Color temperature ({round(1000000 / light.temperature)} K)")
        count_on = sum(light.on for light in window.keylights)
        tray.setToolTip(f"Key Lights: {count_on} of {len(window.keylights)} on")

    # Plasma may use its exported menu without emitting QMenu.aboutToShow.
    # Refresh cached device state as well; this does not issue network reads.
    timer = QTimer(tray)
    timer.timeout.connect(refresh)
    timer.start(500)
    menu.aboutToShow.connect(refresh)
    refresh()
    tray.setContextMenu(menu)
    tray.activated.connect(window.on_tray_activated)
    tray.show()
    return tray
