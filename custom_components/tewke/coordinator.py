"""DataUpdateCoordinator for the Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pytewke.error import TewkeError

from .const import LOGGER

if TYPE_CHECKING:
    from pytewke.data import SensorData

    from .data import TewkeConfigEntry


class TewkeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    Coordinator for all Tewke state (scenes, targets, sensors).

    All updates are push-based via CoAP observation callbacks registered in
    ``async_setup_entry`` — no periodic polling occurs. The initial data fetch
    in ``_async_update_data`` runs once on setup, after which
    "async_set_updated_data" is called by each observation callback.

    Returns:
        {
            "scenes": dict[str, Scene],
            "targets": dict[int, Target],
            "sensors": SensorData | None,
        }

    """

    config_entry: TewkeConfigEntry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch initial state for all resources."""
        tap = self.config_entry.runtime_data.tap
        try:
            scenes = await tap.get_scenes()
            targets = await tap.get_targets()
        except TewkeError as err:
            msg = f"Error communicating with Tewke Tap: {err}"
            raise UpdateFailed(msg) from err

        try:
            sensors: SensorData | None = await tap.get_sensors()
        except TewkeError:
            LOGGER.debug("Sensor data not available from Tewke Tap")
            sensors = None

        return {"scenes": scenes, "targets": targets, "sensors": sensors}
