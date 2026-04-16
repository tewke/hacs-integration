"""Light platform for the Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DISPATCHER_ADD_SCENES
from .scene import TewkeSceneLight
from .target import TewkeTargetLight

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from pytewke.data import Scene

    from .data import TewkeConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: TewkeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tewke light entities from a config entry."""
    coordinator = entry.runtime_data.coordinator
    scene_control_types = entry.runtime_data.scene_control_types

    entities = [
        TewkeSceneLight(coordinator=coordinator, scene=scene)
        for scene in coordinator.data["scenes"].values()
        if scene_control_types.get(scene.id, "light") == "light"
    ]
    entities += [
        TewkeTargetLight(coordinator=coordinator, target=target)
        for target in coordinator.data["targets"].values()
    ]
    async_add_entities(entities)

    @callback
    def _async_add_new_scenes(scenes: list[Scene]) -> None:
        async_add_entities(
            TewkeSceneLight(coordinator=coordinator, scene=scene)
            for scene in scenes
            if scene_control_types.get(scene.id, "light") == "light"
        )

    entry.async_on_unload(
        async_dispatcher_connect(hass, DISPATCHER_ADD_SCENES, _async_add_new_scenes)
    )
