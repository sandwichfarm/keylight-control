from __future__ import annotations

def elgato_to_kelvin(value: int) -> int:
    """Convert Elgato temperature value (143-344) to Kelvin (~2900K-7000K)."""
    return round((-4100 * value) / 201 + 1993300 / 201)


def slider_color_for_temp(value: int) -> tuple[int, int, int]:
    """Interpolate color between #88aaff and #ff9944 for temperature slider."""
    left = (136, 170, 255)  # #88aaff
    right = (255, 153, 68)  # #ff9944
    t = (value - 143) / (344 - 143)
    r = int(left[0] + (right[0] - left[0]) * t)
    g = int(left[1] + (right[1] - left[1]) * t)
    b = int(left[2] + (right[2] - left[2]) * t)
    return r, g, b


def percent_to_hex_alpha(percent: float) -> str:
    """Convert 0-100 percent to two-digit hex alpha ('FF' for 100%, '00' for 0%)."""
    percent = max(0.0, min(100.0, percent))
    alpha = int(round((percent / 100) * 255))
    return f"{alpha:02X}"

