"""Fan platform for the Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    CONF_DEFAULT_SCENE_FAN_DIMMING,
    DEFAULT_SCENE_FAN_DIMMING,
    DISPATCHER_ADD_SCENES,
)
from .scene import TewkeSceneFan

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
    """Set up Tewke fan entities from a config entry."""
    coordinator = entry.runtime_data.coordinator
    scene_control_types = entry.runtime_data.scene_control_types

    fan_default_speeds: dict[str, int] = entry.options.get(
        CONF_DEFAULT_SCENE_FAN_DIMMING
    ) or entry.data.get(CONF_DEFAULT_SCENE_FAN_DIMMING, {})

    async_add_entities(
        TewkeSceneFan(
            coordinator=coordinator,
            scene=scene,
            default_dimming=fan_default_speeds.get(scene_id, DEFAULT_SCENE_FAN_DIMMING),
        )
        for scene_id, scene in coordinator.data["scenes"].items()
        if scene_control_types.get(scene_id) == "fan"
    )

    @callback
    def _async_add_new_scenes(scenes: list[Scene]) -> None:
        current_dimming: dict[str, int] = entry.options.get(
            CONF_DEFAULT_SCENE_FAN_DIMMING
        ) or entry.data.get(CONF_DEFAULT_SCENE_FAN_DIMMING, {})
        async_add_entities(
            TewkeSceneFan(
                coordinator=coordinator,
                scene=scene,
                default_dimming=current_dimming.get(
                    scene.id, DEFAULT_SCENE_FAN_DIMMING
                ),
            )
            for scene in scenes
            if scene_control_types.get(scene.id) == "fan"
        )

    entry.async_on_unload(
        async_dispatcher_connect(hass, DISPATCHER_ADD_SCENES, _async_add_new_scenes)
    )
