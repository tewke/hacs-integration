"""Utilities for the Tewke integration."""


def _tewke_to_ha_brightness(value: int) -> int:
    """
    Convert a Tewke brightness (0-100) to HA brightness (0-255).

    The input value is clamped to the range [0, 100].
    """
    value = max(0, min(100, value))
    return round(value / 100 * 255)


def _ha_to_tewke_brightness(value: int) -> int:
    """
    Convert a HA brightness (0-255) to a Tewke brightness (0-100).

    The input value is clamped to the range [0, 255].
    """
    value = max(0, min(255, value))
    return round(value / 255 * 100)
