"""OKTE Spot Prices - manual refresh button."""
from __future__ import annotations

import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([OKTERefreshButton(coordinator, config_entry.entry_id)])


class OKTERefreshButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Refresh Prices"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_refresh_button_{entry_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": NAME,
            "manufacturer": "OKTE, a.s.",
            "configuration_url": "https://www.okte.sk",
        }

    async def async_press(self) -> None:
        """Manually trigger a fresh fetch from OKTE."""
        _LOGGER.info("OKTE: manual refresh triggered")
        await self.coordinator.async_refresh()
