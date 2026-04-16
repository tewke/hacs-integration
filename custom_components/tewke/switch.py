"""Switch platform for the Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DISPATCHER_ADD_SCENES
from .scene import TewkeSceneSwitch

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from pytewke.data import Scene

    from .data import TewkeConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
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

    @callback
    def _async_add_new_scenes(scenes: list[Scene]) -> None:
        async_add_entities(
            TewkeSceneSwitch(coordinator=coordinator, scene=scene)
            for scene in scenes
            if scene_control_types.get(scene.id, "light") == "switch"
        )

    entry.async_on_unload(
        async_dispatcher_connect(hass, DISPATCHER_ADD_SCENES, _async_add_new_scenes)
    )
