"""Repairs for the Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers import selector
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DISPATCHER_ADD_SCENES, DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResult

    from .data import TewkeConfigEntry

_CONTROL_TYPE_OPTIONS = [
    selector.SelectOptionDict(value="light", label="Light"),
    selector.SelectOptionDict(value="switch", label="Switch"),
    selector.SelectOptionDict(value="fan", label="Fan"),
]


class TewkeNewSceneRepairFlow(RepairsFlow):
    """Repair flow to add new scenes."""

    def __init__(self, entry: TewkeConfigEntry) -> None:
        """Initialise the flow."""
        self.entry = entry

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """
        Handle the configuration of new scenes.

        This step is displayed when new scenes are discovered on the Tewke device.
        It allows the user to assign a Home Assistant platform type (light, switch,
        or fan) to each new scene.
        """
        if hasattr(self.entry, "runtime_data"):
            pending = self.entry.runtime_data.pending_scenes
        else:
            pending = {}

        if user_input is not None and any(k in pending for k in user_input):
            new_control_types = self.entry.runtime_data.scene_control_types.copy()
            added_scenes = []

            for scene_id, control_type in user_input.items():
                if scene_id in pending:
                    added_scenes.append(pending[scene_id])
                    new_control_types[scene_id] = control_type
                    del pending[scene_id]

            self.hass.config_entries.async_update_entry(
                self.entry,
                data={**self.entry.data, "scene_control_types": new_control_types},
            )

            self.entry.runtime_data.scene_control_types = new_control_types

            coordinator = self.entry.runtime_data.coordinator
            scenes_all = coordinator.data.get("scenes_all", {})
            configured_scenes = {
                scene_id: scene
                for scene_id, scene in scenes_all.items()
                if scene_id in new_control_types
            }

            coordinator.async_set_updated_data(
                {
                    **coordinator.data,
                    "scenes": configured_scenes,
                }
            )

            if added_scenes:
                async_dispatcher_send(self.hass, DISPATCHER_ADD_SCENES, added_scenes)

            if not pending:
                ir.async_delete_issue(
                    self.hass, DOMAIN, f"new_scenes_found_{self.entry.entry_id}"
                )

            return self.async_create_entry(data={})

        if not pending:
            return self.async_abort(reason="no_new_scenes")

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(scene_id, default=str(pending[scene_id].name)): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=_CONTROL_TYPE_OPTIONS,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                    for scene_id in pending
                }
            ),
            description_placeholders={"name": self.entry.title},
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> TewkeNewSceneRepairFlow | None:
    """Create a repair flow to add new scenes."""
    if issue_id.startswith("new_scenes_found"):
        if data is None:
            return None
        entry_id = data.get("entry_id")
        if not isinstance(entry_id, str):
            return None

        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            return None

        return TewkeNewSceneRepairFlow(entry)
    LOGGER.warning("Unhandled issue ID %s", issue_id)
    return None
