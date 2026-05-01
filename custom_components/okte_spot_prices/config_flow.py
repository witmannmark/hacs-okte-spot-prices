"""Config flow for OKTE Spot Prices."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, NAME, DEFAULT_SCAN_INTERVAL


class OKTEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OKTE Spot Prices."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=NAME, data=user_input)

        schema = vol.Schema({
            vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): vol.All(
                int, vol.Range(min=15, max=120)
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={"name": NAME},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OKTEOptionsFlow(config_entry)


class OKTEOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Optional(
                "scan_interval",
                default=self.config_entry.options.get(
                    "scan_interval",
                    self.config_entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL)
                ),
            ): vol.All(int, vol.Range(min=15, max=120)),
        })

        return self.async_show_form(step_id="init", data_schema=schema)
