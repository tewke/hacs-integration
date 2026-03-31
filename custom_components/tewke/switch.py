"""Switch platform for the Tewke integration.

Exposes each Tewke scene as a Home Assistant ``SwitchEntity``. Only scenes
whose control type is ``"switch"`` are created by this platform.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytewke.error import TewkeError

from homeassistant.components.switch import SwitchEntity

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
    """Set up Tewke switch entities from a config entry."""
    coordinator = entry.runtime_data.coordinator
    scene_control_types = entry.runtime_data.scene_control_types

    async_add_entities(
        TewkeSceneSwitch(coordinator=coordinator, scene=scene)
        for scene in coordinator.data["scenes"].values()
        if scene_control_types.get(scene.id, "light") == "switch"
    )


class TewkeSceneSwitch(TewkeEntity, SwitchEntity):
    """A Tewke scene exposed as a switch."""

    def __init__(self, coordinator: TewkeCoordinator, scene: Scene) -> None:
        """Initialise the switch."""
        super().__init__(coordinator)
        self._scene_id = scene.id
        self._attr_name = scene.name
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{scene.id}"

    @property
    def is_on(self) -> bool | None:
        """Return True when the scene is active."""
        scene = self.coordinator.data["scenes"].get(self._scene_id)
        return scene.is_active if scene is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the scene."""
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=True, brightness=None
            )
        except TewkeError:
            LOGGER.error("Error activating Tewke scene %s", self._scene_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate the scene."""
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=False, brightness=None
            )
        except TewkeError:
            LOGGER.error("Error deactivating Tewke scene %s", self._scene_id)
        await self.coordinator.async_request_refresh()
