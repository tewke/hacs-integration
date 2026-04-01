"""Config flow for the Tewke integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytewke
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers import selector

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

_CONTROL_TYPE_OPTIONS = [
    selector.SelectOptionDict(value="light", label="Light"),
    selector.SelectOptionDict(value="switch", label="Switch"),
    selector.SelectOptionDict(value="fan", label="Fan"),
]


class TewkeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tewke."""

    VERSION = 1

    _discovered_host: str
    _discovered_name: str
    _room_name: str | None = None
    _scene_control_types: dict[str, str]
    _tap: pytewke.Tap | None = None

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        LOGGER.debug("Zeroconf discovery: %s", discovery_info)

        unique_id = discovery_info.properties.get("hardwareId")
        if not unique_id:
            LOGGER.error("Failed to get unique ID from mDNS TXT records")
            return self.async_abort(reason="cannot_identify")

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.host})

        self._discovered_host = discovery_info.host
        self._discovered_name = discovery_info.properties.get(
            "name"
        ) or discovery_info.name.replace("._tewke-coap._udp.local.", "")
        self._room_name = discovery_info.properties.get("room") or None

        display_name = (
            f"{self._discovered_name} ({self._room_name})"
            if self._room_name
            else self._discovered_name
        )
        self.context["title_placeholders"] = {"name": display_name}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the discovered device and proceed to scene setup."""
        if user_input is not None:
            return await self.async_step_confirm_control_types()

        room_suffix = f", in room **{self._room_name}**" if self._room_name else ""
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "name": self._discovered_name,
                "room_suffix": room_suffix,
            },
        )

    async def async_step_confirm_control_types(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Assign a Home Assistant platform type to each scene."""
        tap = self._tap if self._tap is not None else pytewke.Tap(self._discovered_host)
        self._tap = tap

        if not tap.resources:
            await tap.discover()

        scenes = await tap.get_scenes()
        LOGGER.debug("Discovered scenes: %s", scenes)

        if user_input is not None:
            name_to_id = {scene.name: scene_id for scene_id, scene in scenes.items()}
            self._scene_control_types = {
                name_to_id[name]: control_type
                for name, control_type in user_input.items()
                if name in name_to_id
            }
            return await self.async_step_placeholder()

        if not scenes:
            return await self.async_step_placeholder()

        return self.async_show_form(
            step_id="confirm_control_types",
            data_schema=vol.Schema(
                {
                    vol.Required(scene.name, default="light"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=_CONTROL_TYPE_OPTIONS,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                    for scene in scenes.values()
                }
            ),
        )

    async def async_step_placeholder(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Final confirmation before creating the config entry."""  # noqa: D401
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_name,
                data={
                    CONF_HOST: self._discovered_host,
                    CONF_NAME: self._discovered_name,
                    "scene_control_types": self._scene_control_types or {},
                },
            )

        return self.async_show_form(
            step_id="placeholder",
            description_placeholders={"name": self._discovered_name},
        )
