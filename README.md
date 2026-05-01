# OKTE Spot Prices for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

HACS custom integration for **Slovak OKTE day-ahead electricity spot prices** (96x 15-minute intervals per day).

## Features
- **Current price** (€/MWh) - actual 15-minute period
- **Next price** - next 15-minute period
- **Today Min / Max / Average**
- **Negative Price** (`Yes`/`No`) - if current price is negative
- **Negative Price Next 5** (`Yes`/`No`) - if any of the next 5 periods is negative
- Full 96-point price list as sensor attribute

## Installation via HACS
1. HACS → Integrations → 3 dots → **Custom repositories**
2. URL: `https://github.com/witmannmark/hacs-okte-spot-prices` | Category: `Integration` → Add
3. HACS → Integrations → **OKTE Spot Prices** → Download
4. Restart Home Assistant
5. Settings → Devices & Services → Add Integration → **OKTE Spot Prices**

## Manual Installation
1. Copy `custom_components/okte_spot_prices/` into your HA `config/custom_components/`
2. Restart Home Assistant
3. Settings → Devices & Services → Add Integration → **OKTE Spot Prices**

## Entities
| Entity | Description |
|---|---|
| `sensor.okte_spot_prices_current_price` | Aktuális ár (€/MWh) |
| `sensor.okte_spot_prices_next_price` | Következő 15 perc ára |
| `sensor.okte_spot_prices_today_min` | Mai minimum ár |
| `sensor.okte_spot_prices_today_max` | Mai maximum ár |
| `sensor.okte_spot_prices_today_average` | Mai átlagár |
| `sensor.okte_spot_prices_negative_price` | Negatív ár most? (Yes/No) |
| `sensor.okte_spot_prices_negative_price_next_5` | Negatív ár jön? (Yes/No) |

## Automation example
```yaml
automation:
  - alias: "Negatív OKTE ár értesítés"
    trigger:
      - platform: state
        entity_id: sensor.okte_spot_prices_negative_price
        to: "Yes"
    action:
      - service: notify.mobile_app
        data:
          title: "⚡ Negatív áram ár!"
          message: "Az aktuális OKTE ár negatív - most ingyen jön az áram!"
```

## Data source
[OKTE, a.s.](https://www.okte.sk) - Slovak short-term electricity market operator
