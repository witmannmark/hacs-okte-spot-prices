"""OKTE Spot Prices - Slovak electricity day-ahead prices.

Data source: https://isot.okte.sk/api/v1/dam/results/detail?deliveryDay=YYYY-MM-DD
Official OKTE REST API - no HTML scraping needed.
"""
from __future__ import annotations

from datetime import datetime
import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.event import async_track_time_change

from .const import DOMAIN, DEFAULT_FETCH_HOUR, DEFAULT_FETCH_MINUTE

_LOGGER = logging.getLogger(__name__)
OKTE_API_URL = "https://isot.okte.sk/api/v1/dam/results/detail"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    fetch_hour = entry.options.get("fetch_hour", entry.data.get("fetch_hour", DEFAULT_FETCH_HOUR))
    fetch_minute = entry.options.get("fetch_minute", entry.data.get("fetch_minute", DEFAULT_FETCH_MINUTE))

    coordinator = OKTEDataUpdateCoordinator(hass, fetch_hour, fetch_minute)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "button"])
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "button"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


class OKTEDataUpdateCoordinator(DataUpdateCoordinator):
    """Fetches OKTE prices once daily using official REST API."""

    def __init__(self, hass: HomeAssistant, fetch_hour: int, fetch_minute: int) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.fetch_hour = fetch_hour
        self.fetch_minute = fetch_minute
        self._raw_prices: list[float] = []
        self._prices_date: str = ""

        self._unsub_time = async_track_time_change(
            hass, self._scheduled_update,
            hour=fetch_hour, minute=fetch_minute, second=0,
        )
        self._unsub_15min = async_track_time_change(
            hass, self._update_current_from_cache,
            minute=[0, 15, 30, 45], second=0,
        )

    async def _scheduled_update(self, now=None):
        _LOGGER.info("OKTE: scheduled daily fetch at %02d:%02d", self.fetch_hour, self.fetch_minute)
        await self.async_refresh()

    async def _update_current_from_cache(self, now=None):
        if not self._raw_prices:
            return
        self._inject_current_price()
        self.async_set_updated_data(self.data)

    def _get_price_index(self) -> int:
        """Return the index (0-95) for the current 15-min period."""
        now = datetime.now()
        return (now.hour * 4) + (now.minute // 15)

    def _inject_current_price(self):
        if not self.data or not self._raw_prices:
            return
        idx = self._get_price_index()
        prices = self._raw_prices
        current = prices[idx] if idx < len(prices) else None
        nxt = prices[idx + 1] if (idx + 1) < len(prices) else None
        upcoming_5 = prices[idx:idx + 5]
        self.data["current_price"] = current
        self.data["next_price"] = nxt
        self.data["negative_now"] = "Yes" if (current is not None and current < 0) else "No"
        self.data["negative_next"] = "Yes" if any(p < 0 for p in upcoming_5) else "No"
        self.data["current_index"] = idx

    async def _async_update_data(self):
        """Fetch all 96 prices from OKTE official REST API.

        API: GET https://isot.okte.sk/api/v1/dam/results/detail?deliveryDay=YYYY-MM-DD
        Returns a JSON array of period objects, each with a 'price' field (float, EUR/MWh).
        Periods are 1-indexed (1=00:00-00:15 ... 96=23:45-00:00) for 15-min MTU.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"{OKTE_API_URL}?deliveryDay={today}"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; HomeAssistant/OKTE-integration)",
            "Accept": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 404:
                        raise UpdateFailed(f"OKTE: no data published yet for {today} (HTTP 404)")
                    if resp.status != 200:
                        raise UpdateFailed(f"OKTE API HTTP error: {resp.status} for {url}")
                    data = await resp.json(content_type=None)

            if not isinstance(data, list) or len(data) == 0:
                raise UpdateFailed(f"OKTE: empty or invalid API response for {today}")

            # Sort by period number to guarantee correct order
            data_sorted = sorted(data, key=lambda x: x.get("period", 0))

            prices = []
            for period in data_sorted:
                price = period.get("price")
                if price is None:
                    _LOGGER.warning("OKTE: period %s missing 'price' field", period.get("period"))
                    continue
                prices.append(float(price))

            if not prices:
                raise UpdateFailed(f"OKTE: no valid prices found in API response for {today}")

            self._raw_prices = prices[:96]
            self._prices_date = today

            idx = self._get_price_index()
            current = self._raw_prices[idx] if idx < len(self._raw_prices) else None
            nxt = self._raw_prices[idx + 1] if (idx + 1) < len(self._raw_prices) else None
            upcoming_5 = self._raw_prices[idx:idx + 5]

            _LOGGER.info(
                "OKTE API %s: %d periods fetched, idx=%d, current=%.2f \u20ac/MWh",
                today, len(prices), idx, current or 0
            )

            return {
                "date": today,
                "prices": self._raw_prices,
                "current_price": current,
                "next_price": nxt,
                "min_price": min(prices),
                "max_price": max(prices),
                "avg_price": round(sum(prices) / len(prices), 2),
                "price_count": len(prices),
                "current_index": idx,
                "negative_now": "Yes" if (current is not None and current < 0) else "No",
                "negative_next": "Yes" if any(p < 0 for p in upcoming_5) else "No",
            }

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"OKTE unexpected error: {err}") from err
