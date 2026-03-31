"""TewkeEntity base class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_NAME
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TewkeCoordinator

if TYPE_CHECKING:
    from pytewke.data import Scene


class TewkeEntity(CoordinatorEntity[TewkeCoordinator]):
    """Base class for Tewke entities.

    Each subclass represents a single scene exposed as a HA platform entity
    (switch, light, fan). State is fetched via the shared coordinator.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: TewkeCoordinator, scene: Scene) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._scene_id = scene.id
        entry = coordinator.config_entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.data.get(CONF_NAME, "Tewke"),
        )
