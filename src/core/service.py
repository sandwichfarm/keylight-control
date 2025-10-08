from __future__ import annotations

import asyncio
from typing import Optional

try:
    import aiohttp
except ImportError:  # pragma: no cover
    aiohttp = None  # type: ignore

from .models import KeyLight


class KeyLightService:
    """HTTP service for interacting with Elgato Key Light devices."""

    def __init__(self, timeout_seconds: float = 2.0) -> None:
        self._timeout = timeout_seconds

    async def set_light_state(self, keylight: KeyLight) -> None:
        """Send state update to a device."""
        if aiohttp is None:
            return

        url = f"http://{keylight.ip}:{keylight.port}/elgato/lights"
        data = {
            "numberOfLights": 1,
            "lights": [
                {
                    "on": 1 if keylight.on else 0,
                    "brightness": keylight.brightness,
                    "temperature": keylight.temperature,
                }
            ],
        }
        try:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.put(url, json=data) as response:
                    if response.status != 200:
                        # Keep silent to avoid UI spam in production
                        pass
        except asyncio.TimeoutError:
            pass
        except Exception:
            pass

    async def fetch_light_state(self, keylight: KeyLight) -> Optional[dict]:
        """Fetch current device state. Returns dict or None on failure."""
        if aiohttp is None:
            return None

        url = f"http://{keylight.ip}:{keylight.port}/elgato/lights"
        try:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception:
            pass
        return None

