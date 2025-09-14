# Changelog

All notable changes to Key Light Controller will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-09-14

### Added
- Initial release of Key Light Controller
- Automatic device discovery via mDNS/Bonjour
- Real-time brightness control (0-100%)
- Color temperature control (2900K-7000K)
- Modern dark theme UI matching professional control software
- System tray integration with minimize/restore functionality
- Single instance enforcement
- Keyboard shortcuts:
  - Ctrl+Q: Quit application
  - Escape: Minimize to tray
  - Shift+Click X: Force quit
- Throttled update mechanism to prevent device overload
- Cross-platform support for X11 and Wayland
- Standalone binary distribution via PyInstaller
- Automatic window resizing based on number of devices
- Network timeout handling for robust operation

### Technical Details
- Built with Python 3.8+ and PySide6 (Qt6)
- Async HTTP communication using aiohttp
- Service discovery using zeroconf
- Binary size: ~95MB (includes Python runtime and all dependencies)
- No external dependencies required for binary distribution

### Supported Systems
- Linux x86_64 (Ubuntu, Fedora, Arch, Debian, etc.)
- Display servers: X11, Wayland, XWayland
- Python 3.8 or higher (for source installation)

### Known Limitations
- Only supports Key Light devices with standard API
- Maximum window height limited to 75% of screen height
- Binary is Linux-only (no Windows/macOS support yet)

---

## Version History Format

### [X.Y.Z] - YYYY-MM-DD
#### Added
- New features

#### Changed
- Changes in existing functionality

#### Deprecated
- Soon-to-be removed features

#### Removed
- Removed features

#### Fixed
- Bug fixes

#### Security
- Security fixes