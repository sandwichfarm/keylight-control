from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import KeyLightController
    from ui.widgets.keylight_widget import KeyLightWidget
    from core.models import KeyLight


class KeyLightAPI:
    """Transport-agnostic API core for controlling Key Lights."""

    def __init__(self, controller: KeyLightController) -> None:
        self._controller = controller

    def handle_request(self, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatch a command and return a JSON-serializable result."""
        params = params or {}

        handlers = {
            "lights.list": self._lights_list,
            "lights.get": self._lights_get,
            "lights.set": self._lights_set,
            "lights.toggle": self._lights_toggle,
        }

        handler = handlers.get(command)
        if handler is None:
            return {"ok": False, "error": f"Unknown command: {command}"}

        try:
            result = handler(params)
            return {"ok": True, **result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _device_to_dict(self, keylight: KeyLight, index: int) -> Dict[str, Any]:
        return {
            "index": index,
            "name": keylight.name,
            "ip": keylight.ip,
            "port": keylight.port,
            "mac": keylight.mac_address,
            "on": keylight.on,
            "brightness": keylight.brightness,
            "temperature": keylight.temperature,
        }

    def _resolve_device(self, params: Dict[str, Any]) -> Tuple[int, KeyLight, KeyLightWidget]:
        """Resolve a device by id (MAC address or 0-based index)."""
        device_id = params.get("id")
        if device_id is None:
            raise ValueError("Missing required parameter: id")

        controller = self._controller

        # Try as integer index
        if isinstance(device_id, int) or (isinstance(device_id, str) and device_id.isdigit()):
            idx = int(device_id)
            if 0 <= idx < len(controller.keylights):
                return idx, controller.keylights[idx], controller.keylight_widgets[idx]
            raise ValueError(f"Device index {idx} out of range (0-{len(controller.keylights) - 1})")

        # Try as MAC address
        for i, kl in enumerate(controller.keylights):
            if kl.mac_address == device_id:
                return i, kl, controller.keylight_widgets[i]

        raise ValueError(f"Device not found: {device_id}")

    def _lights_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        devices = []
        for i, kl in enumerate(self._controller.keylights):
            devices.append(self._device_to_dict(kl, i))
        return {"devices": devices}

    def _lights_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        idx, kl, _widget = self._resolve_device(params)
        return {"device": self._device_to_dict(kl, idx)}

    def _lights_set(self, params: Dict[str, Any]) -> Dict[str, Any]:
        idx, kl, widget = self._resolve_device(params)

        changed = False
        if "on" in params:
            new_on = bool(params["on"])
            if kl.on != new_on:
                kl.on = new_on
                widget.power_button.setChecked(new_on)
                widget.update_power_button_style()
                widget.power_state_changed.emit()
                changed = True

        if "brightness" in params:
            new_brightness = max(1, min(100, int(params["brightness"])))
            if kl.brightness != new_brightness:
                kl.brightness = new_brightness
                old = widget.brightness_slider.blockSignals(True)
                widget.brightness_slider.setValue(new_brightness)
                widget.brightness_slider.blockSignals(old)
                widget.brightness_label.setText(f"{new_brightness}%")
                widget.update_power_button_style()
                changed = True

        if "temperature" in params:
            new_temp = max(143, min(344, int(params["temperature"])))
            if kl.temperature != new_temp:
                kl.temperature = new_temp
                old = widget.temp_slider.blockSignals(True)
                widget.temp_slider.setValue(new_temp)
                widget.temp_slider.blockSignals(old)
                widget.temp_label.setText(f"{widget.to_kelvin(new_temp)}K")
                widget.update_power_button_style()
                changed = True

        if changed:
            widget.schedule_update()
            self._controller.update_master_button_state()
            self._controller.update_master_button_style()

        return {"device": self._device_to_dict(kl, idx)}

    def _lights_toggle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if "id" in params:
            # Toggle individual device
            idx, kl, widget = self._resolve_device(params)
            kl.on = not kl.on
            widget.power_button.setChecked(kl.on)
            widget.update_power_button_style()
            widget.power_state_changed.emit()
            widget.schedule_update()
            self._controller.update_master_button_state()
            self._controller.update_master_button_style()
            return {"device": self._device_to_dict(kl, idx)}
        else:
            # Master toggle
            self._controller.toggle_all_lights()
            devices = []
            for i, kl in enumerate(self._controller.keylights):
                devices.append(self._device_to_dict(kl, i))
            return {"devices": devices}
