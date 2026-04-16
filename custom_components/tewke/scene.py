"""
Scene-based entity classes for the Tewke integration.

Each Tewke scene can be exposed as one of three HA platform types depending on
the control type chosen during config flow:

* "TewkeSceneSwitch" — "SwitchEntity", no brightness
* "TewkeSceneLight" — "LightEntity", brightness 0-255 (optimistic)
* "TewkeSceneFan" — "FanEntity", percentage 0-100 (optimistic)

Scene brightness is write-only on the Tewke API; the last commanded value is
held locally for optimistic rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.components.switch import SwitchEntity
from pytewke.error import (
    PyTewkeCoapError,
    PyTewkeInvalidRequestError,
    PyTewkeInvalidResponseError,
    PyTewkeInvalidWallDockError,
    PyTewkeUnknownError,
)

from .const import LOGGER
from .entity import TewkeEntity

if TYPE_CHECKING:
    from pytewke.data import Scene

    from .coordinator import TewkeCoordinator


def _tewke_to_ha_brightness(value: int) -> int:
    """Convert a Tewke brightness (0-100) to HA brightness (0-255)."""
    return round(value / 100 * 255)


def _ha_to_tewke_brightness(value: int | None) -> int | None:
    """Convert a HA brightness (0-255) to a Tewke brightness (0-100)."""
    return round(value / 255 * 100) if value is not None else None


class TewkeSceneEntity(TewkeEntity):
    """A Tewke scene base entity."""

    def __init__(self, coordinator: TewkeCoordinator, scene: Scene) -> None:
        """Initialise the scene light."""
        super().__init__(coordinator)
        self._scene_id = scene.id
        self._attr_name = scene.name
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{scene.id}"
        self._is_on = scene.is_active
        self._brightness: int | None = scene.brightness

    @property
    def _scene(self) -> Scene | None:
        return self.coordinator.data["scenes"].get(self._scene_id)

    @property
    def available(self) -> bool:
        """Return True if the scene is available, False otherwise."""
        if not super().available:
            return False

        return self._scene_id in self.coordinator.data.get("scenes", {})

    @property
    def is_on(self) -> bool | None:
        """Return True when the scene is active."""
        scene = self._scene
        if scene is not None:
            self._is_on = scene.is_active
            self._brightness = scene.brightness
        return self._is_on

    @property
    def brightness(self) -> int | None:
        """Return the last commanded brightness (0-255), or None if unknown."""
        return (
            _tewke_to_ha_brightness(self._brightness)
            if self._brightness is not None
            else None
        )

    @property
    def percentage(self) -> int | None:
        """Return the last commanded fan speed (0-100), or None if unknown."""
        return self._brightness

    async def _async_set_scene(
        self, *, state: bool, brightness: int | None = None
    ) -> None:
        """Set the scene state and brightness."""
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_scene(
                scene_id=self._scene_id, state=state, brightness=brightness
            )
            self._is_on = state
            if state and brightness is not None:
                self._brightness = brightness
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
        except PyTewkeInvalidWallDockError:
            LOGGER.error("Attempted to set Scene while not connected to Wall Dock")
        except (PyTewkeInvalidRequestError, RuntimeError):
            action = "activating" if state else "deactivating"
            LOGGER.exception("Internal error %s Tewke scene %s", action, self._scene_id)
        except (
            PyTewkeCoapError,
            PyTewkeInvalidResponseError,
            PyTewkeUnknownError,
            TimeoutError,
        ):
            action = "activating" if state else "deactivating"
            LOGGER.exception("Error %s Tewke scene %s", action, self._scene_id)


class TewkeSceneSwitch(TewkeSceneEntity, SwitchEntity):
    """A Tewke scene exposed as a switch."""

    def __init__(self, coordinator: TewkeCoordinator, scene: Scene) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, scene)

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Activate the scene."""
        await self._async_set_scene(state=True)

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Deactivate the scene."""
        await self._async_set_scene(state=False)


class TewkeSceneLight(TewkeSceneEntity, LightEntity):
    """
    A Tewke scene exposed as a dimmable light.

    The Tewke API does not return scene brightness, so the last commanded
    brightness is held in "_brightness" for optimistic rendering.
    """

    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, coordinator: TewkeCoordinator, scene: Scene) -> None:
        """Initialise the scene light."""
        super().__init__(coordinator, scene)
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the scene, optionally at a specific brightness."""
        ha_brightness = kwargs.get(ATTR_BRIGHTNESS, 100)
        tewke_brightness = _ha_to_tewke_brightness(ha_brightness)
        await self._async_set_scene(state=True, brightness=tewke_brightness)

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Deactivate the scene."""
        await self._async_set_scene(state=False)


class TewkeSceneFan(TewkeSceneEntity, FanEntity):
    """
    A Tewke scene exposed as a fan.

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
        await self._async_set_scene(state=True, brightness=percentage)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed. A percentage of 0 turns the fan off."""
        return await self._async_set_percentage(percentage)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        """Turn on the fan, optionally at a specific speed."""
        await self._async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Turn off the fan."""
        await self._async_set_scene(state=False)
