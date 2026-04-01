"""Scene-based entity classes for the Tewke integration.

Each Tewke scene can be exposed as one of three HA platform types depending on
the control type chosen during config flow:

* ``TewkeSceneSwitch`` — ``SwitchEntity``, no brightness
* ``TewkeSceneLight`` — ``LightEntity``, brightness 0-255 (optimistic)
* ``TewkeSceneFan`` — ``FanEntity``, percentage 0-100 (optimistic)

Scene brightness is write-only on the Tewke API; the last commanded value is
held locally for optimistic rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytewke.error import TewkeError

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.components.switch import SwitchEntity

from .const import LOGGER
from .entity import TewkeEntity

if TYPE_CHECKING:
    from pytewke.data import Scene

    from .coordinator import TewkeCoordinator


def _tewke_to_ha_brightness(value: int) -> int:
    """Convert a Tewke brightness (0-100) to HA brightness (0-255)."""
    return round(value / 100 * 255)


def _ha_to_tewke_brightness(value: int) -> int:
    """Convert a HA brightness (0-255) to a Tewke brightness (0-100)."""
    return round(value / 255 * 100)


class TewkeSceneEntity(TewkeEntity):
    """A Tewke scene base entity."""

    def __init__(self, coordinator: TewkeCoordinator, scene: Scene) -> None:
        """Initialise the scene light."""
        super().__init__(coordinator)
        self._scene_id = scene.id
        self._attr_name = scene.name
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{scene.id}"
        self._brightness: int | None = None

    @property
    def _scene(self) -> Scene | None:
        return self.coordinator.data["scenes"].get(self._scene_id)

    @property
    def is_on(self) -> bool | None:
        """Return True when the scene is active."""
        scene = self._scene
        return scene.is_active if scene is not None else None

    @property
    def brightness(self) -> int | None:
        """Return the last commanded brightness (0-255), or None if unknown."""
        scene = self._scene
        return _tewke_to_ha_brightness(scene.brightness) if scene is not None else None

    @property
    def percentage(self) -> int | None:
        """Return the last commanded fan speed (0-100), or None if unknown."""
        scene = self._scene
        return scene.brightness if scene is not None else None


class TewkeSceneSwitch(TewkeSceneEntity, SwitchEntity):
    """A Tewke scene exposed as a switch."""

    def __init__(self, coordinator: TewkeCoordinator, scene: Scene) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, scene)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the scene."""
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=True, brightness=None
            )
        except TewkeError:
            LOGGER.error("Error activating Tewke scene %s", self._scene_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate the scene."""
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=False, brightness=None
            )
        except TewkeError:
            LOGGER.error("Error deactivating Tewke scene %s", self._scene_id)


class TewkeSceneLight(TewkeSceneEntity, LightEntity):
    """A Tewke scene exposed as a dimmable light.

    The Tewke API does not return scene brightness, so the last commanded
    brightness is held in ``_brightness`` for optimistic rendering.
    """

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator: TewkeCoordinator, scene: Scene) -> None:
        """Initialise the scene light."""
        super().__init__(coordinator, scene)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the scene, optionally at a specific brightness."""
        ha_brightness = kwargs.get(
            ATTR_BRIGHTNESS, self._brightness if self._brightness is not None else 255
        )
        tewke_brightness = _ha_to_tewke_brightness(ha_brightness)
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=True, brightness=tewke_brightness
            )
        except TewkeError:
            LOGGER.error("Error activating Tewke scene %s", self._scene_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate the scene."""
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=False, brightness=None
            )
        except TewkeError:
            LOGGER.error("Error deactivating Tewke scene %s", self._scene_id)


class TewkeSceneFan(TewkeSceneEntity, FanEntity):
    """A Tewke scene exposed as a fan.

    Fan speed percentage (0-100) maps directly to Tewke brightness (0-100).
    The last commanded percentage is stored locally because the Tewke API does
    not return scene brightness.
    """

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: TewkeCoordinator, scene: Scene) -> None:
        """Initialise the scene fan."""
        super().__init__(coordinator, scene)

    async def _async_set_percentage(self, percentage: int | None) -> None:
        """Set fan speed. A percentage of 0 turns the fan off."""
        if percentage == 0:
            await self.async_turn_off()
            return
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=True, brightness=percentage
            )
        except TewkeError:
            LOGGER.error("Error setting speed for Tewke fan scene %s", self._scene_id)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed. A percentage of 0 turns the fan off."""
        return await self._async_set_percentage(percentage)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan, optionally at a specific speed."""
        await self._async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=False, brightness=None
            )
        except TewkeError:
            LOGGER.error("Error turning off Tewke fan scene %s", self._scene_id)
