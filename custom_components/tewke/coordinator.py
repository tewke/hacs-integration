"""DataUpdateCoordinator for the Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytewke.data import Scene
from pytewke.error import TewkeError

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from .data import TewkeConfigEntry


class TewkeCoordinator(DataUpdateCoordinator[dict[str, Scene]]):
    """Coordinator to manage fetching scene state from a Tewke Tap.

    A single coordinator instance is created per config entry. All switch
    entities share it so the Tap is polled exactly once per interval.
    """

    config_entry: TewkeConfigEntry

    async def _async_update_data(self) -> dict[str, Scene]:
        """Fetch the latest scene states from the Tap."""
        try:
            return await self.config_entry.runtime_data.tap.get_scenes()
        except TewkeError as err:
            raise UpdateFailed(f"Error communicating with Tewke Tap: {err}") from err


