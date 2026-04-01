"""
Binary sensor platform for the Tewke integration.

Exposes boolean BME680 calibration status fields, delivered via CoAP
observation (local_push). Both are disabled by default as diagnostic values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .entity import TewkeEntity

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from pytewke.data import SensorData

    from .coordinator import TewkeCoordinator
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
    coordinator = entry.runtime_data.coordinator
    if coordinator.data.get("sensors") is None:
        return

    async_add_entities(
        TewkeBinarySensor(coordinator=coordinator, description=description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class TewkeBinarySensor(TewkeEntity, BinarySensorEntity):
    """A Tewke BME680 calibration status binary sensor."""

    entity_description: TewkeBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: TewkeCoordinator,
        description: TewkeBinarySensorEntityDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        self._attr_unique_id = (
            f"{entry.unique_id or entry.entry_id}_sensor_{description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return the sensor state."""
        sensors: SensorData | None = self.coordinator.data.get("sensors")
        if sensors is None:
            return None
        return self.entity_description.value_fn(sensors)
