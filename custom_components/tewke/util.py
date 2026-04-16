"""Utilities for the Tewke integration."""

def _tewke_to_ha_brightness(value: int) -> int:
    """Convert a Tewke brightness (0-100) to HA brightness (0-255)."""
    return round(value / 100 * 255)


def _ha_to_tewke_brightness(value: int) -> int:
    """Convert a HA brightness (0-255) to a Tewke brightness (0-100)."""
    return round(value / 255 * 100)
