"""DataUpdateCoordinators for the Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytewke.data import SensorData
from pytewke.error import TewkeError

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import LOGGER

if TYPE_CHECKING:
    from .data import TewkeConfigEntry


class TewkeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for scene and target state.

    Only performs an initial fetch on setup. All subsequent state changes are
    delivered via CoAP observation callbacks registered in async_setup_entry,
    which call ``async_set_updated_data`` directly. No periodic polling occurs.

    Returns:
        {"scenes": dict[str, Scene], "targets": dict[int, Target]}
    """

    config_entry: TewkeConfigEntry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the initial scene and target state from the Tap."""
        tap = self.config_entry.runtime_data.tap
        try:
            scenes = await tap.get_scenes()
            targets = await tap.get_targets()
            return {"scenes": scenes, "targets": targets}
        except TewkeError as err:
            raise UpdateFailed(f"Error communicating with Tewke Tap: {err}") from err


class TewkeSensorCoordinator(DataUpdateCoordinator[SensorData | None]):
    """Coordinator for BME680 and ambient-light sensor data.

    Polls ``tap.get_sensors()`` on every update interval. Sensor failure is
    non-fatal — devices without a BME680 return ``None`` and sensor entities
    are simply unavailable.
    """

    config_entry: TewkeConfigEntry

    async def _async_update_data(self) -> SensorData | None:
        """Fetch the latest sensor readings from the Tap."""
        try:
            return await self.config_entry.runtime_data.tap.get_sensors()
        except TewkeError:
            LOGGER.debug("Sensor data not available from Tewke Tap")
            return None
