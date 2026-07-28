# ASL3-SkywarnPlus-NG-Bridge

Relays active weather alerts from a locally running [SkywarnPlus-NG](https://github.com/hardenedpenguin/SkywarnPlus-NG) into the legacy Allmon3 iframe panel and classic (AUTOSKY) Supermon warning display — integrations NG doesn't provide natively.

Optionally merges in a current-conditions weather snapshot (written by something else, e.g. [asl3-herald](https://github.com/N6LKA/ASL3-Herald)) for the Allmon3 panel. This script does not fetch weather itself — see [Weather snapshot contract](#weather-snapshot-contract) below.

## Why this exists

SkywarnPlus-NG ships its own web dashboard and handles alert announcements on the repeater directly, but has no concept of Allmon3's iframe panel or classic Supermon's AUTOSKY warning file — those were features of the original SkywarnPlus fork this replaces. This bridge polls NG's local API and reproduces that same output.

## Requirements

- [SkywarnPlus-NG](https://github.com/hardenedpenguin/SkywarnPlus-NG) installed and running locally (`systemctl status skywarnplus-ng`)
- Python 3 with `requests` and `ruamel.yaml`
- Root (writes into Allmon3's web root and/or Supermon's AUTOSKY paths, which aren't writable by SkywarnPlus-NG's own service user)
- Allmon3 and/or classic (AUTOSKY-based) Supermon installed, for whichever integration you enable

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/N6LKA/ASL3-SkywarnPlus-NG-Bridge/main/install.sh | sudo bash
```

This installs the script to `/usr/local/sbin/asl3-swp-ng-bridge.py`, writes a default config to `/etc/asl3-swp-ng-bridge/config.yaml` (only if one doesn't already exist), and adds a cron job that runs it every minute.

**After installing**, edit `/etc/asl3-swp-ng-bridge/config.yaml`:
- Set `Allmon3.Enable: true` and/or `Supermon.Enable: true` for whichever you use
- Adjust `Allmon3.WebRoot` / `Supermon.Paths` if they differ from the defaults
- Set `Weather.Enable: true` and `Weather.JsonPath` if you have something writing a weather snapshot (see below)

Test a run manually before waiting on cron:

```sh
sudo /usr/local/sbin/asl3-swp-ng-bridge.py
```

## Uninstall

```sh
curl -fsSL https://raw.githubusercontent.com/N6LKA/ASL3-SkywarnPlus-NG-Bridge/main/uninstall.sh | sudo bash
```

Add `--purge` to also remove the config directory. Output files already written into Allmon3/Supermon are left alone either way.

## Allmon3 setup

This script only writes `swp-data.json` and `swp-alerts.html` into your Allmon3 web root — it does not touch `allmon3.ini`. Point Allmon3's `menu.ini`/iframe config at `swp-alerts.html` yourself, the same way you would for any other custom panel page.

## Supermon setup

Writes `warnings.txt` to `/tmp/AUTOSKY` and `/var/www/html/AUTOSKY` (both, if writable) in the same format classic Supermon already expects — no Supermon-side configuration needed.

## Weather snapshot contract

If `Weather.Enable: true`, the script reads a JSON file (default `/tmp/asl3-herald/weather.json`) and merges it into the Allmon3 panel only (Supermon's AUTOSKY display stays alerts-only). It's ignored if missing or older than `Weather.MaxAgeMin`. Expected shape:

```json
{
  "weather": {
    "temp_f": "82",
    "temp_c": "27.8",
    "humidity": "55",
    "wind_mph": "8",
    "wind_dir": "SW",
    "wind_gust_mph": "14",
    "condition": "Partly Cloudy"
  },
  "weather_label": "My Station"
}
```

`wind_gust_mph` and `condition` may be omitted/null. Anything writing this file just needs to produce this shape.

## File locations

| Item | Path |
|---|---|
| Script | `/usr/local/sbin/asl3-swp-ng-bridge.py` |
| Config | `/etc/asl3-swp-ng-bridge/config.yaml` |
| Cron | `/etc/cron.d/asl3-swp-ng-bridge` |
| Log | `/var/log/asl3-swp-ng-bridge.log` |
| Allmon3 output | `<WebRoot>/swp-data.json`, `<WebRoot>/swp-alerts.html` |
| Supermon output | `<path>/warnings.txt` for each configured path |

## License

GPLv3. See [LICENSE](LICENSE).
