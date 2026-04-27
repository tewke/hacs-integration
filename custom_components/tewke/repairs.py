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
    from pytewke.data import Scene

    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResult

    from .data import TewkeConfigEntry

_CONTROL_TYPE_OPTIONS = [
    selector.SelectOptionDict(value="light", label="Light"),
    selector.SelectOptionDict(value="switch", label="Switch"),
    selector.SelectOptionDict(value="fan", label="Fan"),
]

_CONTROL_TYPE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=_CONTROL_TYPE_OPTIONS,
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)

# Maximum scenes handled in one batch step; must match the scene_N entries in strings.json.
_MAX_BATCH_SCENES = 50


class TewkeNewSceneRepairFlow(RepairsFlow):
    """Repair flow to configure pending scenes for a device, up to one batch per invocation."""

    def __init__(self, entry: TewkeConfigEntry) -> None:
        """Initialise the flow."""
        self.entry = entry
        self._pending_list: list[tuple[str, Scene]] = []

    async def async_step_init(
        self,
        user_input: dict[str, str] | None = None,  # noqa: ARG002
    ) -> FlowResult:
        """Load pending scenes and hand off to the batch configuration step."""
        pending: dict[str, Scene] = (
            self.entry.runtime_data.pending_scenes
            if hasattr(self.entry, "runtime_data")
            else {}
        )

        if not pending:
            return self.async_abort(reason="no_new_scenes")

        self._pending_list = list(pending.items())[:_MAX_BATCH_SCENES]
        return await self.async_step_configure_scenes()

    async def async_step_configure_scenes(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Show a single form with one dropdown per pending scene."""
        if user_input is not None:
            return await self._async_apply_results(user_input)

        # Re-filter against current pending_scenes to drop any externally removed scenes.
        pending: dict[str, Scene] = (
            self.entry.runtime_data.pending_scenes
            if hasattr(self.entry, "runtime_data")
            else {}
        )
        self._pending_list = [
            (sid, scene) for sid, scene in self._pending_list if sid in pending
        ]

        if not self._pending_list:
            return self.async_abort(reason="no_new_scenes")

        schema = vol.Schema(
            {
                vol.Required(f"scene_{i}", default="light"): _CONTROL_TYPE_SELECTOR
                for i in range(len(self._pending_list))
            }
        )

        return self.async_show_form(
            step_id="configure_scenes",
            data_schema=schema,
            description_placeholders={
                "name": self.entry.title,
                **{
                    f"scene_{i}": scene.name
                    for i, (_, scene) in enumerate(self._pending_list)
                },
            },
        )

    async def _async_apply_results(self, user_input: dict[str, str]) -> FlowResult:
        """Commit all configured scene control types and update HA state."""
        pending: dict[str, Scene] = self.entry.runtime_data.pending_scenes
        new_control_types = self.entry.runtime_data.scene_control_types.copy()
        added_scenes: list[Scene] = []

        for i, (scene_id, scene) in enumerate(self._pending_list):
            control_type = user_input.get(f"scene_{i}", "light")
            if scene_id in pending:
                added_scenes.append(scene)
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
            sid: scene for sid, scene in scenes_all.items() if sid in new_control_types
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


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> TewkeNewSceneRepairFlow | None:
    """Create a repair flow to configure new scenes."""
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
