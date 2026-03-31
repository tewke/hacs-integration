"""Custom types for the Tewke integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytewke
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import TewkeCoordinator

type TewkeConfigEntry = ConfigEntry[TewkeData]


@dataclass
class TewkeData:
    """Data for the Tewke integration."""

    tap: pytewke.Tap
    coordinator: TewkeCoordinator
    scene_control_types: dict[str, str]
