"""OKTE Spot Prices - Slovak electricity day-ahead prices."""
from __future__ import annotations

from datetime import timedelta, datetime
import logging

import aiohttp
from bs4 import BeautifulSoup
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

OKTE_URL = "https://www.okte.sk/sk/kratkodoby-trh/zverejnenie-udajov-dt/celkove-vysledky-dt/"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    scan_interval = entry.options.get(
        "scan_interval", entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    )
    coordinator = OKTEDataUpdateCoordinator(hass, scan_interval)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


class OKTEDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, scan_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_interval),
        )

    async def _async_update_data(self):
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"{OKTE_URL}#date={today}&page=1"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"OKTE HTTP error: {resp.status}")
                    text = await resp.text()

            soup = BeautifulSoup(text, "html.parser")
            table = soup.find("table")
            if table is None:
                raise UpdateFailed("OKTE: table not found in page")

            prices = []
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue
                raw = (
                    cols[3].get_text(strip=True)
                    .replace("\u20ac/MWh", "")
                    .replace("\xa0", "")
                    .replace(" ", "")
                    .replace(",", ".")
                )
                try:
                    prices.append(float(raw))
                except ValueError:
                    continue

            if not prices:
                raise UpdateFailed("OKTE: no prices parsed")

            current_price = prices[0]
            next_5 = prices[:5]

            return {
                "date": today,
                "prices": prices[:96],
                "current_price": current_price,
                "next_price": prices[1] if len(prices) > 1 else None,
                "min_price": min(prices),
                "max_price": max(prices),
                "avg_price": round(sum(prices) / len(prices), 2),
                "price_count": len(prices),
                "negative_now": "Yes" if current_price < 0 else "No",
                "negative_next": "Yes" if any(p < 0 for p in next_5) else "No",
            }

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"OKTE unexpected error: {err}") from err
