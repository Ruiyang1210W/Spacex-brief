"""Live data tools for Pad Brief. The model must call these instead of guessing."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx

PACIFIC = ZoneInfo("America/Los_Angeles")
HTTP_TIMEOUT = 20.0

DEFAULT_PLACE = os.getenv("DEFAULT_PLACE", "Hawthorne, CA")
DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "33.9207"))
DEFAULT_LON = float(os.getenv("DEFAULT_LON", "-118.3280"))


def _iso_to_local(iso: str | None) -> dict:
    if not iso:
        return {"utc": None, "los_angeles": None}
    utc = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=timezone.utc)
    local = utc.astimezone(PACIFIC)
    return {
        "utc": utc.strftime("%Y-%m-%d %H:%M UTC"),
        "los_angeles": local.strftime("%Y-%m-%d %I:%M %p PT"),
        "unix": int(utc.timestamp()),
    }


def get_next_spacex_launches(limit: int = 3) -> dict:
    """Upcoming SpaceX launches from Launch Library 2 (not model memory)."""
    limit = max(1, min(int(limit), 5))
    url = "https://ll.thespacedevs.com/2.3.0/launches/upcoming/"
    params = {
        "lsp__name": "SpaceX",
        "ordering": "net",
        "limit": limit,
        "mode": "detailed",
    }
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            payload = r.json()
    except Exception as exc:
        return {"ok": False, "error": f"Launch Library request failed: {exc}"}

    launches = []
    for item in payload.get("results", []):
        mission = item.get("mission") or {}
        pad = (item.get("pad") or {})
        location = pad.get("location") or {}
        rocket = ((item.get("rocket") or {}).get("configuration") or {})
        status = item.get("status") or {}
        image = item.get("image") or {}
        launches.append(
            {
                "name": item.get("name"),
                "status": status.get("name"),
                "status_description": status.get("description"),
                "net": _iso_to_local(item.get("net")),
                "window_start": _iso_to_local(item.get("window_start")),
                "window_end": _iso_to_local(item.get("window_end")),
                "rocket": rocket.get("full_name") or rocket.get("name"),
                "mission_type": mission.get("type"),
                "mission_description": (mission.get("description") or "")[:800],
                "orbit": ((mission.get("orbit") or {}).get("name")),
                "pad": pad.get("name"),
                "location": location.get("name"),
                "image_url": image.get("image_url") or image.get("thumbnail_url"),
            }
        )
    return {
        "ok": True,
        "source": "The Space Devs Launch Library 2",
        "count": len(launches),
        "launches": launches,
        "note": "Times converted to Pacific Time for the Hawthorne/LA demo default.",
    }


def get_iss_passes(
    lat: float | None = None,
    lon: float | None = None,
    place: str | None = None,
    n: int = 5,
) -> dict:
    """Upcoming ISS passes that can be seen with the naked eye."""
    lat = DEFAULT_LAT if lat is None else float(lat)
    lon = DEFAULT_LON if lon is None else float(lon)
    place = place or DEFAULT_PLACE
    n = max(1, min(int(n), 8))
    url = "https://iss-api.polluxlabs.io/iss-pass"
    params = {
        "lat": lat,
        "lon": lon,
        "n": n,
        "visible_only": "true",
        "min_elevation": 10,
    }
    now = None
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            payload = r.json()
    except Exception as exc:
        return {"ok": False, "error": f"ISS pass request failed: {exc}"}

    try:
        with httpx.Client(timeout=8.0) as client:
            now_r = client.get("https://api.open-notify.org/iss-now.json")
            if now_r.status_code == 200:
                now = now_r.json()
    except Exception:
        now = None

    def _event(block) -> dict | None:
        if not isinstance(block, dict):
            return None
        timed = _iso_to_local(block.get("time"))
        return {
            **timed,
            "azimuth_deg": block.get("azimuth_deg"),
            "compass": block.get("compass"),
            "elevation_deg": block.get("elevation_deg"),
        }

    passes = []
    for p in payload.get("passes") or []:
        culm = p.get("culmination") or {}
        passes.append(
            {
                "rise": _event(p.get("rise")),
                "max": _event(culm),
                "set": _event(p.get("set")),
                "visible_start": _iso_to_local(p.get("visible_start")),
                "visible_end": _iso_to_local(p.get("visible_end")),
                "max_elevation_deg": culm.get("elevation_deg"),
                "duration_s": p.get("visible_duration_sec") or p.get("duration_sec"),
                "appears_from": (p.get("rise") or {}).get("compass"),
                "disappears_to": (p.get("set") or {}).get("compass"),
                "visible": p.get("visible", True),
            }
        )

    iss_now = None
    if now and now.get("iss_position"):
        iss_now = {
            "latitude": now["iss_position"].get("latitude"),
            "longitude": now["iss_position"].get("longitude"),
            "timestamp_utc": datetime.fromtimestamp(
                int(now.get("timestamp", 0)), tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M UTC"),
        }

    return {
        "ok": True,
        "source": "ISS Pass API + Open Notify",
        "place": place,
        "lat": lat,
        "lon": lon,
        "iss_now": iss_now,
        "visible_passes": passes,
        "tip": "Naked-eye ISS passes need a dark sky, ISS in sunlight, and roughly 10°+ elevation.",
    }


def get_apod(date: str | None = None) -> dict:
    """NASA Astronomy Picture of the Day."""
    api_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
    params = {"api_key": api_key}
    if date:
        params["date"] = date
    urls = [
        "https://api.nasa.gov/planetary/apod",
        "https://science.nasa.gov/wp-json/wp/v2/apod-basic/",
    ]
    last_error = None
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        for url in urls:
            try:
                r = client.get(url, params=params)
                r.raise_for_status()
                data = r.json()
                if isinstance(data, list) and data:
                    data = data[0]
                return {
                    "ok": True,
                    "source": "NASA APOD",
                    "title": data.get("title") or data.get("name"),
                    "date": data.get("date"),
                    "explanation": (data.get("explanation") or data.get("description") or "")[:1200],
                    "url": data.get("url") or data.get("hdurl") or data.get("image"),
                    "hdurl": data.get("hdurl"),
                    "media_type": data.get("media_type", "image"),
                    "copyright": data.get("copyright"),
                }
            except Exception as exc:
                last_error = exc
    return {"ok": False, "error": f"APOD request failed: {last_error}"}
