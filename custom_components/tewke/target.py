"""
Target-based entity classes for the Tewke integration.

Each Tewke physical output (target) is exposed as a "LightEntity". Targets
are disabled by default because most users will prefer to control their device
via scenes; targets are an advanced option for direct output control.

Dimmable targets expose "ColorMode.BRIGHTNESS"; non-dimmable ones expose
"ColorMode.ONOFF". Brightness values are converted between the Tewke scale
(0-100) and the HA scale (0-255).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from pytewke.error import TewkeError

from .const import LOGGER
from .entity import TewkeEntity

if TYPE_CHECKING:
    from pytewke.data import Target

    from .coordinator import TewkeCoordinator


def _tewke_to_ha_brightness(value: int) -> int:
    """Convert a Tewke brightness (0-100) to HA brightness (0-255)."""
    return round(value / 100 * 255)


def _ha_to_tewke_brightness(value: int) -> int:
    """Convert a HA brightness (0-255) to a Tewke brightness (0-100)."""
    return round(value / 255 * 100)


class TewkeTargetLight(TewkeEntity, LightEntity):
    """
    A Tewke physical output (target) exposed as a light.

    Disabled by default — targets are an advanced interface for direct output
    control. Most users should use scenes instead.
    """

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Disable target entities by default."""
        return False

    def __init__(self, coordinator: TewkeCoordinator, target: Target) -> None:
        """Initialise the target light."""
        super().__init__(coordinator)
        self._target_index = target.index
        self._attr_name = target.name
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

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the output."""
        try:
            await self.coordinator.config_entry.runtime_data.tap.set_target(
                target=self._target_index, brightness=0
            )
        except TewkeError:
            LOGGER.error("Error turning off Tewke target %s", self._target_index)
