"""Binary sensor platform for the Tewke integration.

Exposes the boolean BME680 calibration status fields as binary sensor entities.
Both are disabled by default as they are diagnostic values.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pytewke.data import SensorData

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import CONF_NAME
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import TewkeSensorCoordinator
    from .data import TewkeConfigEntry


@dataclass(frozen=True, kw_only=True)
class TewkeBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Tewke binary sensor entity."""

    value_fn: Callable[[SensorData], bool | None]


BINARY_SENSOR_DESCRIPTIONS: tuple[TewkeBinarySensorEntityDescription, ...] = (
    TewkeBinarySensorEntityDescription(
        key="stabilisation_status",
        name="Stabilisation Status",
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.stabilisation_status,
    ),
    TewkeBinarySensorEntityDescription(
        key="run_in_status",
        name="Run-in Status",
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.run_in_status,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: TewkeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tewke binary sensor entities from a config entry."""
    coordinator = entry.runtime_data.sensor_coordinator
    if coordinator.data is None:
        return

    async_add_entities(
        TewkeBinarySensor(coordinator=coordinator, description=description, entry=entry)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class TewkeBinarySensor(CoordinatorEntity["TewkeSensorCoordinator"], BinarySensorEntity):
    """A Tewke BME680 calibration status binary sensor."""

    _attr_has_entity_name = True
    entity_description: TewkeBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: TewkeSensorCoordinator,
        description: TewkeBinarySensorEntityDescription,
        entry: TewkeConfigEntry,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{entry.unique_id or entry.entry_id}_sensor_{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.data.get(CONF_NAME, "Tewke"),
        )

    @property
    def is_on(self) -> bool | None:
        """Return the sensor state."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
