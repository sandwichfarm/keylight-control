from __future__ import annotations

from typing import Any, Dict
from PySide6.QtCore import QObject, Signal

from config import DeviceConfig
from .settings_schema import defaults_dict


class PreferencesService(QObject):
    """Central preferences manager with persistence and change signals."""

    setting_changed = Signal(str, object)  # key, value
    settings_applied = Signal(dict)  # full dict snapshot

    def __init__(self, device_config: DeviceConfig | None = None) -> None:
        super().__init__()
        self._config = device_config or DeviceConfig()
        self._defaults: Dict[str, Any] = defaults_dict()
        self._cache: Dict[str, Any] = {}
        self._load()

    # --- API ---
    def get(self, key: str, default: Any | None = None) -> Any:
        if key in self._cache:
            return self._cache[key]
        return self._defaults.get(key, default)

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        if key in self._defaults:
            # Optionally: validate types here
            pass
        current = self._cache.get(key)
        if current == value:
            return
        self._cache[key] = value
        if persist:
            self._persist_one(key, value)
        self.setting_changed.emit(key, value)

    def all(self) -> Dict[str, Any]:
        return dict(self._cache)

    def apply(self, values: Dict[str, Any], persist: bool = True) -> None:
        changed: Dict[str, Any] = {}
        for k, v in values.items():
            if self._cache.get(k) != v:
                self._cache[k] = v
                changed[k] = v
        if persist and changed:
            for k, v in changed.items():
                self._persist_one(k, v)
        if changed:
            for k, v in changed.items():
                self.setting_changed.emit(k, v)
            self.settings_applied.emit(dict(self._cache))

    def reset_to_defaults(self) -> None:
        self.apply(self._defaults, persist=True)

    # --- internals ---
    def _load(self) -> None:
        # Initialize from config, falling back to defaults
        for key, def_val in self._defaults.items():
            val = self._config.get_app_setting(key, def_val)
            self._cache[key] = val
            # Ensure defaults are written at least once
            if val == def_val:
                self._config.set_app_setting(key, val)

    def _persist_one(self, key: str, value: Any) -> None:
        self._config.set_app_setting(key, value)

