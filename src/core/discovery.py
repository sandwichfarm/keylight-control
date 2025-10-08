from __future__ import annotations

import asyncio
from typing import Dict

try:
    import aiohttp
except ImportError:  # pragma: no cover - runtime dependency
    aiohttp = None  # type: ignore

from zeroconf import ServiceBrowser, Zeroconf, ServiceStateChange
from PySide6.QtCore import QObject, Signal


class KeyLightDiscovery(QObject):
    """Discovers Key Light devices on the network using mDNS.

    Emits:
      - device_found(dict): when a device is fully identified
      - mac_fetch_requested(dict): when MAC lookup should be performed
    """

    device_found = Signal(dict)
    mac_fetch_requested = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.zeroconf = Zeroconf()
        self.browser: ServiceBrowser | None = None

    def start_discovery(self) -> None:
        """Start discovering Key Light devices."""
        self.browser = ServiceBrowser(
            self.zeroconf,
            "_elg._tcp.local.",
            handlers=[self._on_service_state_change],
        )

    def _on_service_state_change(self, zeroconf, service_type, name, state_change):
        """Handle service discovery events."""
        if state_change == ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info and info.addresses:
                device_info: Dict[str, str | int] = {
                    "name": name.replace("._elg._tcp.local.", ""),
                    "ip": ".".join(map(str, info.addresses[0])),
                    "port": info.port,
                }
                # Request MAC address fetch from main thread
                self.mac_fetch_requested.emit(device_info)

    async def _fetch_mac_address(self, device_info: Dict):
        """Fetch MAC address from device and emit the complete device info."""
        mac_address = await self._get_device_mac_address(
            device_info["ip"], device_info["port"]
        )
        device_info["mac_address"] = mac_address
        self.device_found.emit(device_info)

    async def _get_device_mac_address(self, ip: str, port: int) -> str:
        """Get MAC address from device API or ARP table."""
        # Try the device's accessory-info endpoint
        try:
            if aiohttp is None:
                raise RuntimeError("aiohttp not available")
            url = f"http://{ip}:{port}/elgato/accessory-info"
            timeout = aiohttp.ClientTimeout(total=3)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        mac = (
                            data.get("macAddress")
                            or data.get("mac")
                            or data.get("serialNumber")
                        )
                        if mac:
                            return mac.upper().replace(":", "").replace("-", "")
        except Exception:
            pass

        # Fallback: ARP table
        try:
            import subprocess

            result = subprocess.run(
                ["arp", "-n", ip], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if ip in line and "incomplete" not in line.lower():
                        parts = line.split()
                        for part in parts:
                            if ":" in part and len(part.replace(":", "")) == 12:
                                return part.upper().replace(":", "")
        except Exception:
            pass

        # Last resort: use IP address as a fallback identifier
        return f"IP_{ip.replace('.', '_')}"

    def stop_discovery(self) -> None:
        """Stop discovery and cleanup."""
        if self.browser:
            self.browser.cancel()
        self.zeroconf.close()

