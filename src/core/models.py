from dataclasses import dataclass


@dataclass
class KeyLight:
    """Represents a Key Light device and its state."""
    name: str
    ip: str
    port: int = 9123
    mac_address: str = ""
    on: bool = False
    brightness: int = 50
    temperature: int = 200  # 143-344 (Elgato units, ~7000K-2900K)

