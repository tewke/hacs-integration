"""Sensor platform for the Tewke integration.

Exposes all numeric fields from the BME680 and ambient light readings returned
by ``tap.get_sensors()``, polled every 10 seconds via TewkeSensorCoordinator.

Disabled-by-default sensors are raw/diagnostic values that most users won't
need day-to-day.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pytewke.data import SensorData

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    CONF_NAME,
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import TewkeSensorCoordinator
    from .data import TewkeConfigEntry


@dataclass(frozen=True, kw_only=True)
class TewkeSensorEntityDescription(SensorEntityDescription):
    """Describes a Tewke sensor entity."""

    value_fn: Callable[[SensorData], float | int | None]


SENSOR_DESCRIPTIONS: tuple[TewkeSensorEntityDescription, ...] = (
    TewkeSensorEntityDescription(
        key="iaq",
        name="Air Quality",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.iaq,
    ),
    TewkeSensorEntityDescription(
        key="static_iaq",
        name="Static IAQ",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.static_iaq,
    ),
    TewkeSensorEntityDescription(
        key="compensated_temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.compensated_temperature,
    ),
    TewkeSensorEntityDescription(
        key="compensated_humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.compensated_humidity,
    ),
    TewkeSensorEntityDescription(
        key="co2_equivalent",
        name="CO₂",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.co2_equivalent,
    ),
    TewkeSensorEntityDescription(
        key="raw_pressure",
        name="Pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PA,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.raw_pressure,
    ),
    TewkeSensorEntityDescription(
        key="gas_percentage",
        name="Gas Percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.gas_percentage,
    ),
    TewkeSensorEntityDescription(
        key="ambient_light",
        name="Ambient Light",
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.ambient_light.lux,
    ),
    # Disabled by default — diagnostic / raw calibration values
    TewkeSensorEntityDescription(
        key="iaq_accuracy",
        name="IAQ Accuracy",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.iaq_accuracy,
    ),
    TewkeSensorEntityDescription(
        key="breath_voc_equivalent",
        name="Breath VOC Equivalent",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.breath_voc_equivalent,
    ),
    TewkeSensorEntityDescription(
        key="raw_temperature",
        name="Raw Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.raw_temperature,
    ),
    TewkeSensorEntityDescription(
        key="raw_humidity",
        name="Raw Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.raw_humidity,
    ),
    TewkeSensorEntityDescription(
        key="raw_gas",
        name="Raw Gas Resistance",
        native_unit_of_measurement="Ω",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.raw_gas,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: TewkeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tewke sensor entities from a config entry."""
    coordinator = entry.runtime_data.sensor_coordinator
    if coordinator.data is None:
        return

    async_add_entities(
        TewkeSensor(coordinator=coordinator, description=description, entry=entry)
        for description in SENSOR_DESCRIPTIONS
    )


class TewkeSensor(CoordinatorEntity["TewkeSensorCoordinator"], SensorEntity):
    """A Tewke BME680 / ambient-light sensor entity."""

    _attr_has_entity_name = True
    entity_description: TewkeSensorEntityDescription

    def __init__(
        self,
        coordinator: TewkeSensorCoordinator,
        description: TewkeSensorEntityDescription,
        entry: TewkeConfigEntry,
    ) -> None:
        """Initialise the sensor."""
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
    def native_value(self) -> float | int | None:
        """Return the sensor reading."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
