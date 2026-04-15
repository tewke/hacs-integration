"""The Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytewke
from homeassistant.const import CONF_HOST, Platform
from homeassistant.exceptions import ConfigEntryNotReady
from pytewke.error import PyTewkeDiscoveryError

from .const import DOMAIN, LOGGER
from .coordinator import TewkeCoordinator
from .data import TewkeConfigEntry, TewkeData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytewke.data import (
        ConfigData,
        EnergyData,
        RadarData,
        Scene,
        SensorData,
        Target,
    )

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.FAN,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TewkeConfigEntry,
) -> bool:
    """Set up a Tewke device from a config entry."""
    tap = pytewke.Tap(entry.data[CONF_HOST])

    try:
        await tap.discover()
    except PyTewkeDiscoveryError as err:
        msg = f"Unable to connect to Tewke device at {entry.data[CONF_HOST]}"
        raise ConfigEntryNotReady(msg) from err

    tewke_coordinator = TewkeCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
    )

    entry.runtime_data = TewkeData(
        tap=tap,
        coordinator=tewke_coordinator,
        scene_control_types=entry.data.get("scene_control_types", {}),
    )

    await tewke_coordinator.async_config_entry_first_refresh()

    def _on_scene_update(scenes: dict[str, Scene]) -> None:
        if tewke_coordinator.data is None:
            return

        ha_scenes = tewke_coordinator.data["scenes"]

        new_scenes = {
            scene_id: scene
            for scene_id, scene in scenes.items()
            if scene_id not in entry.runtime_data.scene_control_types
            and scene_id not in entry.runtime_data.pending_scenes
        }

        if new_scenes:
            LOGGER.info("Discovered new scenes, pending configuration: %s", new_scenes)
        stale_scene_ids = set(ha_scenes.keys()) - set(scenes.keys())
        if stale_scene_ids:
            LOGGER.debug("Removing stale scenes: %s", stale_scene_ids)

        configured_scenes = {
            scene_id: scene
            for scene_id, scene in scenes.items()
            if scene_id in entry.runtime_data.scene_control_types
        }
        tewke_coordinator.async_set_updated_data(
            {
                **tewke_coordinator.data,
                "scenes": configured_scenes,
            }
        )

    def _on_target_update(targets: dict[int, Target]) -> None:
        if tewke_coordinator.data is None:
            return
        for target in targets.values():
            tewke_coordinator.async_set_updated_data(
                {
                    **tewke_coordinator.data,
                    "targets": {
                        **tewke_coordinator.data["targets"],
                        target.index: target,
                    },
                }
            )

    def _on_sensor_update(sensor_data: SensorData) -> None:
        if tewke_coordinator.data is None:
            return
        tewke_coordinator.async_set_updated_data(
            {**tewke_coordinator.data, "sensors": sensor_data}
        )

    def _on_radar_update(radar_data: RadarData) -> None:
        if tewke_coordinator.data is None:
            return
        tewke_coordinator.async_set_updated_data(
            {**tewke_coordinator.data, "radar": radar_data}
        )

    def _on_energy_update(energy_data: EnergyData) -> None:
        if tewke_coordinator.data is None:
            return
        tewke_coordinator.async_set_updated_data(
            {**tewke_coordinator.data, "energy": energy_data}
        )

    def _on_config_update(config_data: ConfigData) -> None:
        if tewke_coordinator.data is None:
            return
        tewke_coordinator.async_set_updated_data(
            {**tewke_coordinator.data, "config": config_data}
        )

    await tap.observe(
        scene_callback=_on_scene_update,
        target_callback=_on_target_update,
        sensor_callback=_on_sensor_update,
        radar_callback=_on_radar_update,
        energy_callback=_on_energy_update,
        config_change_callback=_on_config_update,
    )

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
