"""TewkeEntity base class."""

from __future__ import annotations

from homeassistant.const import CONF_NAME
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TewkeCoordinator


class TewkeEntity(CoordinatorEntity[TewkeCoordinator]):
    """
    Base class for Tewke entities.

    Each subclass represents a single scene or target output exposed as a HA
    platform entity (switch, light, fan). State is fetched via the shared
    coordinator.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: TewkeCoordinator) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        tap = entry.runtime_data.tap
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.data.get(CONF_NAME, "Tewke"),
            manufacturer="Tewke",
            model="Tap",
            sw_version=tap.tewke_os_version,
            suggested_area=entry.data.get("room_name"),
        )
