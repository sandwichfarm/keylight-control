#!/usr/bin/env python3
"""
Key Light Controller - Entry point
Minimal launcher that wires the application and starts the UI.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__license__ = "GPL-3.0"

import sys
import socket
import asyncio
import signal

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from utils.single_instance import SingleInstance
from ui.main_window import KeyLightController


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Key Light Controller")
    parser.add_argument("--version", action="version", version=f"Key Light Controller {__version__}")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.parse_args()

    # Enforce single instance
    single_instance = SingleInstance()
    if single_instance.is_running():
        print("Key Light Control is already running.")
        try:
            signal_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            signal_socket.connect(("127.0.0.1", 45654))
            signal_socket.close()
        except Exception:
            pass
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setApplicationName("Key Light Control")

    # Integrate asyncio event loop with Qt
    try:
        import qasync
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
    except ImportError:
        # Fallback: run without qasync (reduced async integration)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    controller = KeyLightController()
    controller.show()

    # Graceful signal handling (SIGINT/SIGTERM) to quit cleanly
    def _handle_signal(signum, _frame):
        try:
            # Stop discovery and request app quit
            try:
                controller.quit_application()
            except Exception:
                pass
            # Stop asyncio loop if present
            try:
                loop.stop()
            except Exception:
                pass
        except Exception:
            pass

    try:
        signal.signal(signal.SIGINT, _handle_signal)
    except Exception:
        pass
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, _handle_signal)
        except Exception:
            pass

    # Allow secondary invocations to activate existing window
    def check_for_activation():
        try:
            single_instance.socket.setblocking(False)
            conn, _addr = single_instance.socket.accept()
            conn.close()
            controller.show()
            controller.raise_()
            controller.activateWindow()
        except Exception:
            pass

    activation_timer = QTimer()
    activation_timer.timeout.connect(check_for_activation)
    activation_timer.start(100)

    try:
        with loop:
            loop.run_forever()
    finally:
        single_instance.cleanup()


if __name__ == "__main__":
    main()
