#!/usr/bin/python3

"""
swp-ng-bridge.py
===============================================================================
Relays active weather alerts from a locally running SkywarnPlus-NG instance
(https://github.com/hardenedpenguin/SkywarnPlus-NG) into the legacy Allmon3
iframe panel and classic (AUTOSKY) Supermon warning display, since NG itself
has no built-in integration for either.

Optionally merges in a separately-maintained current-conditions weather
snapshot (e.g. written by Herald, formerly asl3-herald) for the Allmon3
panel — this script does not fetch weather itself.

Run as root via cron (SkywarnPlus-NG's alert data is fetched over its local
HTTP API, but Allmon3's web root and Supermon's AUTOSKY paths are not
writable by an unprivileged user).

This file is part of ASL3-SkywarnPlus-NG-Bridge.
ASL3-SkywarnPlus-NG-Bridge is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at your
option) any later version. ASL3-SkywarnPlus-NG-Bridge is distributed in the
hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
the GNU General Public License for more details. You should have received a
copy of the GNU General Public License along with this program. If not, see
<https://www.gnu.org/licenses/>.
"""

import os
import sys
import json
import logging
import datetime

try:
    import requests
except ImportError:
    requests = None

try:
    from ruamel.yaml import YAML
except ImportError:
    YAML = None

CONFIG_FILE = os.environ.get(
    "SWP_NG_BRIDGE_CONFIG", "/etc/asl3-swp-ng-bridge/config.yaml"
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Static HTML written to the Allmon3 web root on each run. Identical panel
# behavior to the original SkywarnPlus Allmon3 integration: fetches
# swp-data.json every 60s and re-renders without a full page reload.
ALERTS_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link rel="stylesheet" href="css/bootstrap.min.css">
  <style>
    html,body{margin:0;padding:0;height:auto!important;min-height:0!important;background:transparent;font-size:1rem}
    body{padding:4px 8px}
    .swp-wx{padding:4px 8px;margin-bottom:3px;border-radius:3px;background:rgba(255,255,255,.08);text-align:center}
    .swp-wx-title{font-weight:600;margin-bottom:2px}
    .swp-alert{padding:3px 8px;margin-bottom:3px;border-radius:3px;font-weight:500;text-align:center}
    .swp-extreme{background:#7a0000;color:#fff}
    .swp-severe{background:#b83200;color:#fff}
    .swp-moderate{background:#9a5a00;color:#fff}
    .swp-minor{background:#7a6000;color:#fff}
    .swp-unknown{background:#444;color:#fff}
  </style>
</head>
<body>
  <div id="swp"></div>
  <script>
    var SEV={extreme:'swp-extreme',severe:'swp-severe',moderate:'swp-moderate',minor:'swp-minor'};
    function titleCase(s){
      return s.replace(/\\w\\S*/g, function(t){return t.charAt(0).toUpperCase()+t.substr(1).toLowerCase();});
    }
    function resizeParent(){
      try{
        var h=document.body.scrollHeight,fr=window.parent.document.querySelectorAll('iframe');
        for(var i=0;i<fr.length;i++){
          try{if(fr[i].contentWindow===window){fr[i].style.height=h+'px';break;}}catch(e){}
        }
      }catch(e){}
    }
    function render(d){
      var h='';
      if(d.weather){
        var w=d.weather;
        var title='Weather conditions'+(d.weather_label?': '+d.weather_label:'');
        var tempC=Math.round((w.temp_f-32)*5/9);
        var details='Temperature: '+w.temp_f+'&deg;F, '+tempC+'&deg;C';
        if(w.feels_like_f!=null && w.feels_like_f!=w.temp_f) details+=' (feels like '+w.feels_like_f+'&deg;F)';
        if(w.humidity!=null) details+=' &nbsp;|&nbsp; Humidity: '+w.humidity+'%';
        if(w.wind_mph!=null){
          var wind=(w.wind_dir?w.wind_dir+' ':'')+w.wind_mph+' mph';
          if(w.wind_gust_mph) wind+=' (gust '+w.wind_gust_mph+' mph)';
          details+=' &nbsp;|&nbsp; Wind: '+wind;
        }
        if(w.condition) details+=' &nbsp;|&nbsp; '+titleCase(w.condition);
        h+='<div class="swp-wx">'+
           '<div class="swp-wx-title">'+title+'</div>'+
           '<div>'+details+'</div>'+
           '</div>';
      }
      (d.alerts||[]).forEach(function(a){
        var c=SEV[(a.severity||'').toLowerCase()]||'swp-unknown';
        h+='<div class="swp-alert '+c+'"><strong>'+a.title+'</strong> ['+a.counties.join(', ')+']</div>';
      });
      document.getElementById('swp').innerHTML=h;
      resizeParent();
    }
    function poll(){
      fetch('swp-data.json?_='+Date.now())
        .then(function(r){return r.json();})
        .then(render)
        .catch(function(){});
    }
    poll();
    setInterval(poll,60000);
  </script>
</body>
</html>
"""


def load_config():
    if YAML is None:
        logging.error("ruamel.yaml not installed")
        return None
    if not os.path.isfile(CONFIG_FILE):
        logging.error("Config file not found: %s", CONFIG_FILE)
        return None
    yaml = YAML()
    with open(CONFIG_FILE, "r") as f:
        return yaml.load(f) or {}


def write_json_file(path, payload):
    """Write payload as a real, regular JSON file at path. Removes a
    pre-existing symlink first — writing through one would silently write to
    its target instead of replacing it, and Apache won't serve a symlinked
    static file unless FollowSymLinks is enabled in the vhost."""
    if os.path.islink(path):
        os.remove(path)
    with open(path, "w") as f:
        json.dump(payload, f)


def fetch_ng_alerts(api_base, timeout=10):
    """Fetch the active alert list from a local SkywarnPlus-NG instance.
    Returns None on any failure so the caller can leave existing output
    files untouched rather than clobbering good data with an empty result."""
    url = api_base.rstrip("/") + "/api/alerts"
    try:
        resp = requests.get(url, timeout=timeout)
    except Exception as exc:
        logging.warning("Could not reach SkywarnPlus-NG API at %s: %s", url, exc)
        return None
    if resp.status_code != 200:
        logging.warning("SkywarnPlus-NG API returned HTTP %s from %s", resp.status_code, url)
        return None
    try:
        return resp.json().get("alerts", [])
    except Exception as exc:
        logging.warning("Could not parse SkywarnPlus-NG API response: %s", exc)
        return None


def load_weather_snapshot(path, max_age_min):
    """Read the current-conditions JSON another program (e.g. Herald)
    is expected to maintain. Expected shape:
        {"weather": {"temp_f": ..., "condition": ..., "feels_like_f": ...,
                     "humidity": ..., "wind_mph": ..., "wind_dir": ...,
                     "wind_gust_mph": ...},
         "weather_label": "..."}
    Matches Herald's own weather-provider normalization (Tempest,
    Open-Meteo, METAR). Returns None if missing, unreadable, or older than
    max_age_min."""
    if not path or not os.path.isfile(path):
        return None
    try:
        age_min = (datetime.datetime.now().timestamp() - os.path.getmtime(path)) / 60.0
        if age_min > max_age_min:
            logging.debug("Weather snapshot %s is stale (%.1f min old), skipping", path, age_min)
            return None
        with open(path, "r") as f:
            return json.load(f)
    except Exception as exc:
        logging.warning("Could not read weather snapshot %s: %s", path, exc)
        return None


def build_display_alerts(ng_alerts):
    """Reshape NG's alert objects into the display format the Allmon3 panel
    HTML/JS expects. NG already de-duplicates and consolidates alerts, so
    each entry here is one alert with one area_desc and one expiry."""
    display = []
    for alert in ng_alerts:
        area_desc = alert.get("area_desc") or ""
        counties = [c.strip() for c in area_desc.split(";") if c.strip()] or [area_desc]
        display.append(
            {
                "title": alert.get("event", "Weather Alert"),
                "severity": alert.get("severity", "Unknown"),
                "counties": counties,
                "end_time": alert.get("expires", ""),
            }
        )
    return display


def build_supermon_lines(ng_alerts):
    lines = []
    for alert in ng_alerts:
        event = alert.get("event", "Weather Alert")
        area_desc = alert.get("area_desc") or ""
        lines.append("{} [{}]".format(event, area_desc) if area_desc else event)
    return lines


def write_supermon(cfg, ng_alerts):
    paths = cfg.get("Supermon", {}).get("Paths", ["/tmp/AUTOSKY", "/var/www/html/AUTOSKY"])
    content = "<br>".join(build_supermon_lines(ng_alerts))
    for path in paths:
        try:
            os.makedirs(path, exist_ok=True)
            if os.access(path, os.W_OK):
                with open(os.path.join(path, "warnings.txt"), "w") as f:
                    f.write(content)
            else:
                logging.error("No write permission for %s", path)
        except Exception as exc:
            logging.error("An error occurred while writing to %s: %s", path, exc)


def write_allmon3(cfg, ng_alerts, weather):
    web_root = cfg.get("Allmon3", {}).get("WebRoot", "/usr/share/allmon3")
    os.makedirs(web_root, exist_ok=True)

    payload = {
        "alerts": build_display_alerts(ng_alerts),
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if weather:
        payload["weather"] = weather.get("weather")
        payload["weather_label"] = weather.get("weather_label", "")

    write_json_file(os.path.join(web_root, "swp-data.json"), payload)
    with open(os.path.join(web_root, "swp-alerts.html"), "w") as f:
        f.write(ALERTS_HTML)


def main():
    if os.geteuid() != 0:
        logging.error("Must run as root (writes into Allmon3/Supermon web roots)")
        sys.exit(1)

    if requests is None:
        logging.error("python3-requests not installed")
        sys.exit(1)

    cfg = load_config()
    if cfg is None:
        sys.exit(1)

    ng_cfg = cfg.get("SkywarnPlusNG", {})
    api_base = ng_cfg.get("ApiBase", "http://127.0.0.1:8100")

    allmon3_enabled = cfg.get("Allmon3", {}).get("Enable", False)
    supermon_enabled = cfg.get("Supermon", {}).get("Enable", False)

    if not allmon3_enabled and not supermon_enabled:
        logging.info("Both Allmon3 and Supermon integration disabled in config, nothing to do")
        return

    ng_alerts = fetch_ng_alerts(api_base)
    if ng_alerts is None:
        logging.warning("Skipping this run - could not fetch alerts from SkywarnPlus-NG")
        return

    weather = None
    weather_cfg = cfg.get("Weather", {})
    if weather_cfg.get("Enable", False):
        weather = load_weather_snapshot(
            weather_cfg.get("JsonPath", "/etc/asterisk/scripts/herald/weather.json"),
            weather_cfg.get("MaxAgeMin", 30),
        )

    if allmon3_enabled:
        write_allmon3(cfg, ng_alerts, weather)
        logging.info("Wrote Allmon3 panel (%d alert(s))", len(ng_alerts))

    if supermon_enabled:
        write_supermon(cfg, ng_alerts)
        logging.info("Wrote Supermon AUTOSKY files (%d alert(s))", len(ng_alerts))


if __name__ == "__main__":
    main()
