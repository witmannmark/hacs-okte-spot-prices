"""OKTE Spot Prices - Slovak electricity day-ahead prices."""
from __future__ import annotations

from datetime import timedelta, datetime
import logging

import aiohttp
from bs4 import BeautifulSoup
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.event import async_track_time_change

from .const import DOMAIN, DEFAULT_FETCH_HOUR, DEFAULT_FETCH_MINUTE

_LOGGER = logging.getLogger(__name__)
OKTE_URL = "https://www.okte.sk/sk/kratkodoby-trh/zverejnenie-udajov-dt/celkove-vysledky-dt/"


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


def _parse_price(text: str) -> float | None:
    """Parse price string like '121,34' or '121.34' or '-15,37 €/MWh' to float."""
    cleaned = (
        text
        .replace("\u20ac/MWh", "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace("\t", "")
        .replace(",", ".")
        .strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


def _find_price_column(header_row) -> int:
    """Auto-detect the Cena (€/MWh) column index from the table header."""
    if header_row is None:
        return 2  # default fallback based on observed OKTE structure
    for i, th in enumerate(header_row.find_all(["th", "td"])):
        text = th.get_text(strip=True).lower()
        if "cena" in text or "price" in text or "eur" in text or "mwh" in text:
            return i
    return 2  # fallback: Perióda(0), Čas(1), Cena(2)


class OKTEDataUpdateCoordinator(DataUpdateCoordinator):
    """Fetches OKTE prices once daily at configured time."""

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
        """Fetch all 96 prices from OKTE."""
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

            # Auto-detect the Cena column from header
            header_row = table.find("tr")
            price_col = _find_price_column(header_row)
            _LOGGER.debug("OKTE: using price column index %d", price_col)

            prices = []
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) <= price_col:
                    continue
                val = _parse_price(cols[price_col].get_text(strip=True))
                if val is not None:
                    prices.append(val)

            if not prices:
                raise UpdateFailed(f"OKTE: no prices parsed (tried column {price_col})")

            self._raw_prices = prices[:96]
            self._prices_date = today

            idx = self._get_price_index()
            current = self._raw_prices[idx] if idx < len(self._raw_prices) else None
            nxt = self._raw_prices[idx + 1] if (idx + 1) < len(self._raw_prices) else None
            upcoming_5 = self._raw_prices[idx:idx + 5]

            _LOGGER.info(
                "OKTE %s: %d prices (col %d), idx=%d current=%.2f \u20ac/MWh",
                today, len(prices), price_col, idx, current or 0
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
