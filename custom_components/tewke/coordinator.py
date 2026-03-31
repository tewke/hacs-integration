"""DataUpdateCoordinator for the Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytewke.error import TewkeError

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from .data import TewkeConfigEntry


class TewkeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Tewke scene and target state.

    State is delivered via CoAP observe push notifications registered in
    async_setup_entry.  No periodic polling is performed; update_interval is
    intentionally left as None.

    Returns:
        {
            "scenes": dict[str, Scene],
            "targets": dict[int, Target],
        }
    """

    config_entry: TewkeConfigEntry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the initial scene and target states from the Tap.

        This is called once during setup (async_config_entry_first_refresh).
        Subsequent updates arrive via push callbacks registered in
        async_setup_entry, which call async_set_updated_data directly.
        """
        tap = self.config_entry.runtime_data.tap
        try:
            scenes = await tap.get_scenes()
            targets = await tap.get_targets()
            return {"scenes": scenes, "targets": targets}
        except TewkeError as err:
            raise UpdateFailed(f"Error communicating with Tewke Tap: {err}") from err


