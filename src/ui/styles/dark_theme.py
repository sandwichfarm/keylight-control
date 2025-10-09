def get_style() -> str:
    return """
    QMainWindow {
        background-color: #1a1a1a;
    }

    QWidget {
        background-color: #1a1a1a;
        color: #e6e6e6;
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
        /* layout spacing controls separation; no extra margin here */
        margin: 0;
    }

    QFrame#MasterDeviceWidget::hover{
        border: 1px solid #5a5a5a;
        background-color: #3a3a3a;
    }

    QFrame#MasterPanel {
        background-color: #2a2a2a;
        border-radius: 12px;
        border: 1px solid #3a3a3a;
        /* avoid double spacing with container margins */
        margin: 0;
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

    /* Settings button styling */
    QPushButton#settingsButton {
        background-color: #3a3a3a;
        border: 1px solid #555555;
        border-radius: 12px;
        color: #dddddd;
        font-size: 16px;
        font-weight: bold;
    }

    QPushButton#settingsButton:hover {
        background-color: #4a4a4a;
        border: 1px solid #666666;
        color: #ffffff;
    }

    /* Preferences dialog + tabs */
    QDialog {
        background-color: #1a1a1a;
        color: #e6e6e6;
    }

    QTabWidget::pane {
        border: 1px solid #3a3a3a;
    }

    QTabBar::tab {
        background: #2a2a2a;
        color: #cccccc;
        padding: 6px 10px;
        border: 1px solid #3a3a3a;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }

    QTabBar::tab:selected {
        background: #3a3a3a;
        color: #ffffff;
        border: 1px solid #555555;
    }

    QSpinBox, QComboBox {
        background-color: #2a2a2a;
        color: #e6e6e6;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 2px 6px;
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

    /* Menus */
    QMenu {
        background-color: #2a2a2a;
        border: 1px solid #555555;
        color: #ffffff;
    }

    QMenu::item {
        padding: 6px 12px;
        color: #ffffff;
    }

    QMenu::item:selected {
        background-color: #00E5FF;
        color: #000000;
    }

    QMenu::item:disabled {
        color: #888888;
    }
    """
