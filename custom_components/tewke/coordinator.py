"""DataUpdateCoordinator for the Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytewke.error import TewkeError

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from .data import TewkeConfigEntry


class TewkeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching scene and target state from a Tewke Tap.

    Returns:
        {
            "scenes": dict[str, Scene],
            "targets": dict[int, Target],
        }
    """

    config_entry: TewkeConfigEntry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest scene and target states from the Tap."""
        tap = self.config_entry.runtime_data.tap
        try:
            scenes = await tap.get_scenes()
            targets = await tap.get_targets()
            return {"scenes": scenes, "targets": targets}
        except TewkeError as err:
            raise UpdateFailed(f"Error communicating with Tewke Tap: {err}") from err


