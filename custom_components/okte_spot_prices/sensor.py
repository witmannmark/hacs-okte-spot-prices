"""OKTE Spot Prices - sensor platform."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME

SENSOR_TYPES = [
    SensorEntityDescription(
        key="current_price",
        name="Current Price",
        native_unit_of_measurement="\u20ac/MWh",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:currency-eur",
    ),
    SensorEntityDescription(
        key="next_price",
        name="Next Price",
        native_unit_of_measurement="\u20ac/MWh",
        icon="mdi:clock-outline",
    ),
    SensorEntityDescription(
        key="min_price",
        name="Today Min",
        native_unit_of_measurement="\u20ac/MWh",
        icon="mdi:trending-down",
    ),
    SensorEntityDescription(
        key="max_price",
        name="Today Max",
        native_unit_of_measurement="\u20ac/MWh",
        icon="mdi:trending-up",
    ),
    SensorEntityDescription(
        key="avg_price",
        name="Today Average",
        native_unit_of_measurement="\u20ac/MWh",
        icon="mdi:chart-line",
    ),
    SensorEntityDescription(
        key="price_count",
        name="Price Count",
        icon="mdi:numeric",
    ),
    SensorEntityDescription(
        key="negative_now",
        name="Negative Price",
        icon="mdi:check-circle-outline",
    ),
    SensorEntityDescription(
        key="negative_next",
        name="Negative Price Next 5",
        icon="mdi:check-circle-outline",
    ),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        OKTESensor(coordinator, description, config_entry.entry_id)
        for description in SENSOR_TYPES
    )


class OKTESensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, description, entry_id):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}_{entry_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": NAME,
            "manufacturer": "OKTE, a.s.",
            "configuration_url": "https://www.okte.sk",
        }

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        key = self.entity_description.key
        val = data.get(key)
        if val is None:
            return None
        if key in ("negative_now", "negative_next"):
            return val
        if isinstance(val, float):
            return round(val, 2)
        return val

    @property
    def icon(self):
        key = self.entity_description.key
        if key in ("negative_now", "negative_next"):
            return "mdi:alert-circle" if self.native_value == "Yes" else "mdi:check-circle-outline"
        return self.entity_description.icon

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "date": data.get("date"),
            "prices": data.get("prices", []),
            "current_index": data.get("current_index"),
            "negative_now": data.get("negative_now"),
            "negative_next": data.get("negative_next"),
        }
