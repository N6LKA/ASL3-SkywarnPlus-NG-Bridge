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

This script writes the two files Allmon3's iframe actually loads — `swp-data.json` and `swp-alerts.html` — into your Allmon3 web root. It never touches `allmon3.ini` or any other Allmon3 config; you point Allmon3 at the page yourself, once:

1. Make sure `Allmon3.Enable: true` and `Allmon3.WebRoot` are set correctly in this script's own config (`/etc/asl3-swp-ng-bridge/config.yaml`, default `WebRoot: /usr/share/allmon3`), and that it's run at least once (manually or via cron) so `swp-alerts.html` actually exists there.
2. Edit `/etc/allmon3/allmon3.ini`:
   ```sh
   sudo nano /etc/allmon3/allmon3.ini
   ```
3. Find the stanza for the node where you want the panel to appear, and add `iframepre` (shows the panel above the transmit status line — recommended, since alerts are high-priority) or `iframepost` (shows it below the connection table instead):
   ```ini
   [501260]
   host = 127.0.0.1
   user = admin
   pass = password
   iframepre = swp-alerts.html
   ```
   Only add this to the stanza(s) for the node(s) actually covered by this alerting setup — not to a stanza for an unrelated node/location. The panel auto-collapses to zero height when there's nothing active, so it costs nothing to leave enabled.
4. Reload the Allmon3 page in your browser — no Allmon3 service restart needed.

## Supermon setup

Writes `warnings.txt` to `/tmp/AUTOSKY` and `/var/www/html/AUTOSKY` (both, if writable) in the same format classic Supermon already expects — no Supermon-side configuration needed.

## Weather snapshot contract

If `Weather.Enable: true`, the script reads a JSON file (default `/tmp/asl3-herald/weather.json`) and merges it into the Allmon3 panel only (Supermon's AUTOSKY display stays alerts-only). It's ignored if missing or older than `Weather.MaxAgeMin`. Expected shape:

```json
{
  "weather": {
    "temp_f": 82,
    "condition": "Partly Cloudy",
    "feels_like_f": 85,
    "humidity": 55
  },
  "weather_label": "My Station"
}
```

Deliberately just these four fields — matches what asl3-herald's own weather providers (Tempest, Open-Meteo, METAR) normalize down to internally for its own announcements, so it can write this snapshot straight from data it's already fetching, no wind/pressure/etc. tracked separately. `feels_like_f`/`condition` may be `null`. Anything writing this file just needs to produce this shape.

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
