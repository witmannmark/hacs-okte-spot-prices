# OKTE Spot Prices for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](https://github.com/witmannmark/hacs-okte-spot-prices/releases)

HACS custom integration for **Slovak OKTE day-ahead electricity spot prices** (96x 15-minute intervals per day).

## How it works
- **Once daily** (default: 00:10) fetches all 96 prices from OKTE
- Every **:00/:15/:30/:45** the `current_price` and `next_price` sensors automatically update from the local cache — no repeated HTTP requests
- A **manual refresh button** is available in the HA UI at any time

## Entities
| Entity | Description |
|---|---|
| `sensor.okte_spot_prices_current_price` | Aktu\u00e1lis 15 perces \u00e1r (\u20ac/MWh) |
| `sensor.okte_spot_prices_next_price` | K\u00f6vetkez\u0151 15 perc \u00e1ra |
| `sensor.okte_spot_prices_today_min` | Mai minimum \u00e1r |
| `sensor.okte_spot_prices_today_max` | Mai maximum \u00e1r |
| `sensor.okte_spot_prices_today_average` | Mai \u00e1tlag\u00e1r |
| `sensor.okte_spot_prices_negative_price` | Negat\u00edv \u00e1r most? (Yes/No) |
| `sensor.okte_spot_prices_negative_price_next_5` | Negat\u00edv \u00e1r j\u00f6n? (Yes/No) |
| `button.okte_spot_prices_refresh_prices` | Manu\u00e1lis friss\u00edt\u00e9s gomb |

## Installation via HACS
1. HACS \u2192 Integrations \u2192 3 dots \u2192 **Custom repositories**
2. URL: `https://github.com/witmannmark/hacs-okte-spot-prices` | Category: `Integration` \u2192 Add
3. HACS \u2192 Integrations \u2192 **OKTE Spot Prices** \u2192 Download
4. Restart Home Assistant
5. Settings \u2192 Devices & Services \u2192 Add Integration \u2192 **OKTE Spot Prices**

## Config options
| Option | Default | Description |
|---|---|---|
| `fetch_hour` | `0` | Hour for daily OKTE fetch |
| `fetch_minute` | `10` | Minute for daily OKTE fetch |

## Automation example
```yaml
automation:
  - alias: "Negat\u00edv OKTE \u00e1r \u00e9rtes\u00edt\u00e9s"
    trigger:
      - platform: state
        entity_id: sensor.okte_spot_prices_negative_price
        to: "Yes"
    action:
      - service: notify.mobile_app
        data:
          title: "\u26a1 Negat\u00edv \u00e1ram \u00e1r!"
          message: "Az aktu\u00e1lis OKTE \u00e1r negat\u00edv - most ingyen j\u00f6n az \u00e1ram!"
```

## Data source
[OKTE, a.s.](https://www.okte.sk) - Slovak short-term electricity market operator
