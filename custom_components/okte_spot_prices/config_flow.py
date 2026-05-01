"""Config flow for OKTE Spot Prices."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, NAME, DEFAULT_FETCH_HOUR, DEFAULT_FETCH_MINUTE


class OKTEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OKTE Spot Prices."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=NAME, data=user_input)

        schema = vol.Schema({
            vol.Optional("fetch_hour", default=DEFAULT_FETCH_HOUR): vol.All(int, vol.Range(min=0, max=23)),
            vol.Optional("fetch_minute", default=DEFAULT_FETCH_MINUTE): vol.All(int, vol.Range(min=0, max=59)),
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
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Optional(
                "fetch_hour",
                default=self.config_entry.options.get("fetch_hour", self.config_entry.data.get("fetch_hour", DEFAULT_FETCH_HOUR)),
            ): vol.All(int, vol.Range(min=0, max=23)),
            vol.Optional(
                "fetch_minute",
                default=self.config_entry.options.get("fetch_minute", self.config_entry.data.get("fetch_minute", DEFAULT_FETCH_MINUTE)),
            ): vol.All(int, vol.Range(min=0, max=59)),
        })

        return self.async_show_form(step_id="init", data_schema=schema)
