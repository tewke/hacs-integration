"""The Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytewke
from pytewke.error import TewkeError

from homeassistant.const import CONF_HOST, Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, LOGGER, SCAN_INTERVAL
from .coordinator import TewkeCoordinator
from .data import TewkeConfigEntry, TewkeData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.FAN, Platform.LIGHT, Platform.SWITCH]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TewkeConfigEntry,
) -> bool:
    """Set up a Tewke device from a config entry."""
    tap = pytewke.Tap(entry.data[CONF_HOST])

    try:
        await tap.discover()
    except TewkeError as err:
        raise ConfigEntryNotReady(
            f"Unable to connect to Tewke device at {entry.data[CONF_HOST]}"
        ) from err

    coordinator = TewkeCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=SCAN_INTERVAL,
    )

    entry.runtime_data = TewkeData(
        tap=tap,
        coordinator=coordinator,
        scene_control_types=entry.data.get("scene_control_types", {}),
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    entry.async_on_unload(tap.close)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: TewkeConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: TewkeConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


