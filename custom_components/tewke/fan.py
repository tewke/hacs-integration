"""Fan platform for the Tewke integration.

Exposes each Tewke scene whose control type is ``"fan"`` as a Home Assistant
``FanEntity``. Fan speed (0-100 %) maps directly to the Tewke brightness
parameter (0-100). Like scene lights, brightness is write-only on the API, so
the last commanded percentage is tracked locally for optimistic rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytewke.error import TewkeError

from homeassistant.components.fan import FanEntity, FanEntityFeature

from .const import LOGGER
from .entity import TewkeEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from pytewke.data import Scene

    from .coordinator import TewkeCoordinator
    from .data import TewkeConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: TewkeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tewke fan entities from a config entry."""
    coordinator = entry.runtime_data.coordinator
    scene_control_types = entry.runtime_data.scene_control_types

    async_add_entities(
        TewkeSceneFan(coordinator=coordinator, scene=scene)
        for scene in coordinator.data["scenes"].values()
        if scene_control_types.get(scene.id, "light") == "fan"
    )


class TewkeSceneFan(TewkeEntity, FanEntity):
    """A Tewke scene exposed as a fan.

    Fan speed percentage (0-100) maps directly to Tewke brightness (0-100).
    The last commanded percentage is stored locally because the Tewke API does
    not return scene brightness.
    """

    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF

    def __init__(self, coordinator: TewkeCoordinator, scene: Scene) -> None:
        """Initialise the scene fan."""
        super().__init__(coordinator)
        self._scene_id = scene.id
        self._attr_name = scene.name
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{scene.id}"
        self._percentage: int = 100

    @property
    def is_on(self) -> bool | None:
        """Return True when the scene is active."""
        scene = self.coordinator.data["scenes"].get(self._scene_id)
        return scene.is_active if scene is not None else None

    @property
    def percentage(self) -> int:
        """Return the last commanded fan speed percentage (0-100)."""
        return self._percentage

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed. A percentage of 0 turns the fan off."""
        if percentage == 0:
            await self.async_turn_off()
            return
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=True, brightness=percentage
            )
        except TewkeError:
            LOGGER.error(
                "Error setting speed for Tewke fan scene %s", self._scene_id
            )
            return
        self._percentage = percentage
        await self.coordinator.async_request_refresh()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan, optionally at a specific speed."""
        await self.async_set_percentage(
            percentage if percentage is not None else self._percentage
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=False, brightness=None
            )
        except TewkeError:
            LOGGER.error("Error turning off Tewke fan scene %s", self._scene_id)
            return
        await self.coordinator.async_request_refresh()
