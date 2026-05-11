"""Numer wydania i identyfikator buildu — widoczne w /api/version i w UI."""

import os
import re
from datetime import datetime, timedelta, timezone
from threading import Lock

import httpx

# Domyślnie przy lokalnym uruchomieniu bez zmiennych środowiskowych.
_DEFAULT_VERSION = "0.3.4"
_RELEASES_URL = "https://api.github.com/repos/blazejwrobel98/Fine-net-dash/releases/latest"
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
_CHECK_TTL = timedelta(minutes=30)
_CHECK_LOCK = Lock()
_CHECK_CACHE: dict[str, object] = {"at": None, "data": None}


def app_version() -> str:
    v = (os.getenv("APP_VERSION") or "").strip()
    return v if v else _DEFAULT_VERSION


def git_sha() -> str:
    return (os.getenv("GIT_SHA") or "").strip()


def _parse_version(raw: str | None) -> tuple[int, int, int] | None:
    v = (raw or "").strip()
    m = _VERSION_RE.match(v)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def check_update_available(current: str | None = None) -> dict[str, object]:
    """
    Sprawdza latest release na GitHub i porównuje do wersji backendu.
    Zwraca bezpieczny payload także przy błędach sieciowych.
    """
    now = datetime.now(timezone.utc)
    with _CHECK_LOCK:
        cached_at = _CHECK_CACHE.get("at")
        cached_data = _CHECK_CACHE.get("data")
        if isinstance(cached_at, datetime) and now - cached_at < _CHECK_TTL and isinstance(cached_data, dict):
            return dict(cached_data)

    cur = (current or app_version()).strip()
    cur_tuple = _parse_version(cur)
    out: dict[str, object] = {
        "current_version": cur,
        "latest_version": None,
        "update_available": False,
        "release_url": None,
        "checked_at_utc": now.isoformat(),
        "error": None,
    }

    try:
        with httpx.Client(timeout=4.0, follow_redirects=True) as client:
            r = client.get(_RELEASES_URL, headers={"Accept": "application/vnd.github+json"})
            r.raise_for_status()
            data = r.json()
        latest_raw = str(data.get("tag_name") or "").strip()
        latest = latest_raw[1:] if latest_raw.startswith("v") else latest_raw
        latest_tuple = _parse_version(latest)
        out["latest_version"] = latest or None
        out["release_url"] = str(data.get("html_url") or "") or None
        out["update_available"] = bool(cur_tuple and latest_tuple and latest_tuple > cur_tuple)
    except Exception as e:
        out["error"] = str(e)

    with _CHECK_LOCK:
        _CHECK_CACHE["at"] = now
        _CHECK_CACHE["data"] = dict(out)
    return out
