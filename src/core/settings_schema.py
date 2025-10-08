from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Dict, Any


MasterPowerSemantics = Literal["AnyOn", "AllOn"]


@dataclass
class GeneralSettings:
    launch_minimized: bool = False
    hide_on_esc: bool = True
    show_master_device_default: bool = False
    show_sync_controls_default: bool = False
    tray_icon_enabled: bool = True
    single_instance: bool = True


@dataclass
class FeatureSettings:
    show_rename_action: bool = True
    show_master_device_control: bool = True
    show_sync_buttons: bool = True
    enable_discovery: bool = True
    enable_auto_sync: bool = True
    enable_keyboard_shortcuts: bool = True


@dataclass
class PerformanceSettings:
    widget_update_interval_ms: int = 50
    widget_min_update_spacing_ms: int = 100
    sync_timer_interval_ms: int = 300
    http_timeout_s: float = 2.0


@dataclass
class AdvancedSettings:
    master_power_semantics: MasterPowerSemantics = "AnyOn"
    enable_debug_logging: bool = False


def defaults_dict() -> Dict[str, Any]:
    g = GeneralSettings()
    f = FeatureSettings()
    p = PerformanceSettings()
    a = AdvancedSettings()
    return {
        # General
        "general.launch_minimized": g.launch_minimized,
        "general.hide_on_esc": g.hide_on_esc,
        "general.show_master_device_default": g.show_master_device_default,
        "general.show_sync_controls_default": g.show_sync_controls_default,
        "general.tray_icon_enabled": g.tray_icon_enabled,
        "general.single_instance": g.single_instance,
        # Features
        "features.show_rename_action": f.show_rename_action,
        "features.show_master_device_control": f.show_master_device_control,
        "features.show_sync_buttons": f.show_sync_buttons,
        "features.enable_discovery": f.enable_discovery,
        "features.enable_auto_sync": f.enable_auto_sync,
        "features.enable_keyboard_shortcuts": f.enable_keyboard_shortcuts,
        # Performance
        "perf.widget_update_interval_ms": p.widget_update_interval_ms,
        "perf.widget_min_update_spacing_ms": p.widget_min_update_spacing_ms,
        "perf.sync_timer_interval_ms": p.sync_timer_interval_ms,
        "perf.http_timeout_s": p.http_timeout_s,
        # Advanced
        "advanced.master_power_semantics": a.master_power_semantics,
        "advanced.enable_debug_logging": a.enable_debug_logging,
    }

