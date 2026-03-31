"""Light platform for the Tewke integration.

Two kinds of light entity are registered here:

* ``TewkeSceneLight`` — one entity per scene whose control type is ``"light"``.
  Brightness is write-only on the Tewke API (scenes don't report it back), so
  the last commanded brightness is tracked locally using optimistic state.

* ``TewkeTargetLight`` — one entity per physical output (target). Target state
  and brightness are reported by the Tap and updated on every coordinator poll.
  Dimmable targets expose ``ColorMode.BRIGHTNESS``; non-dimmable ones expose
  ``ColorMode.ONOFF``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytewke.error import TewkeError

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity

from .const import LOGGER
from .entity import TewkeEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from pytewke.data import Scene, Target

    from .coordinator import TewkeCoordinator
    from .data import TewkeConfigEntry


def _tewke_to_ha_brightness(value: int) -> int:
    """Convert a Tewke brightness (0-100) to HA brightness (0-255)."""
    return round(value / 100 * 255)


def _ha_to_tewke_brightness(value: int) -> int:
    """Convert a HA brightness (0-255) to a Tewke brightness (0-100)."""
    return round(value / 255 * 100)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: TewkeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tewke light entities from a config entry."""
    coordinator = entry.runtime_data.coordinator
    scene_control_types = entry.runtime_data.scene_control_types

    entities: list[LightEntity] = [
        TewkeSceneLight(coordinator=coordinator, scene=scene)
        for scene in coordinator.data["scenes"].values()
        if scene_control_types.get(scene.id, "light") == "light"
    ]
    entities += [
        TewkeTargetLight(coordinator=coordinator, target=target)
        for target in coordinator.data["targets"].values()
    ]
    async_add_entities(entities)


class TewkeSceneLight(TewkeEntity, LightEntity):
    """A Tewke scene exposed as a dimmable light.

    The Tewke API does not return scene brightness, so the last commanded
    brightness is held in ``_brightness`` for optimistic rendering.
    """

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator: TewkeCoordinator, scene: Scene) -> None:
        """Initialise the scene light."""
        super().__init__(coordinator)
        self._scene_id = scene.id
        self._attr_name = scene.name
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{scene.id}"
        self._brightness: int = 255

    @property
    def is_on(self) -> bool | None:
        """Return True when the scene is active."""
        scene = self.coordinator.data["scenes"].get(self._scene_id)
        return scene.is_active if scene is not None else None

    @property
    def brightness(self) -> int:
        """Return the last commanded brightness (0-255)."""
        return self._brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the scene, optionally at a specific brightness."""
        ha_brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
        tewke_brightness = _ha_to_tewke_brightness(ha_brightness)
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=True, brightness=tewke_brightness
            )
        except TewkeError:
            LOGGER.error("Error activating Tewke scene %s", self._scene_id)
            return
        self._brightness = ha_brightness
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate the scene."""
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=False, brightness=None
            )
        except TewkeError:
            LOGGER.error("Error deactivating Tewke scene %s", self._scene_id)
            return
        await self.coordinator.async_request_refresh()


class TewkeTargetLight(TewkeEntity, LightEntity):
    """A Tewke physical output (target) exposed as a light."""

    def __init__(self, coordinator: TewkeCoordinator, target: Target) -> None:
        """Initialise the target light."""
        super().__init__(coordinator)
        self._target_index = target.index
        self._attr_name = f"Output {target.index}"
        entry = coordinator.config_entry
        self._attr_unique_id = (
            f"{entry.unique_id or entry.entry_id}_target_{target.index}"
        )
        if target.is_dimmable:
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        else:
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def _target(self) -> Target | None:
        return self.coordinator.data["targets"].get(self._target_index)

    @property
    def is_on(self) -> bool | None:
        """Return True when the output is on."""
        target = self._target
        return target.is_on if target is not None else None

    @property
    def brightness(self) -> int | None:
        """Return the current brightness (0-255)."""
        target = self._target
        if target is None or not target.is_dimmable:
            return None
        return _tewke_to_ha_brightness(target.brightness)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the output, optionally at a specific brightness."""
        target = self._target
        if target is None:
            return
        if ATTR_BRIGHTNESS in kwargs:
            tewke_brightness = _ha_to_tewke_brightness(kwargs[ATTR_BRIGHTNESS])
        elif target.is_dimmable:
            tewke_brightness = target.brightness if target.brightness > 0 else 100
        else:
            tewke_brightness = 100
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_target(
                target=self._target_index, brightness=tewke_brightness
            )
        except TewkeError:
            LOGGER.error("Error turning on Tewke target %s", self._target_index)
            return
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the output."""
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_target(
                target=self._target_index, brightness=0
            )
        except TewkeError:
            LOGGER.error("Error turning off Tewke target %s", self._target_index)
            return
        await self.coordinator.async_request_refresh()
