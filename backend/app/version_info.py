"""Numer wydania i identyfikator buildu — widoczne w /api/version i w UI."""

import os
import re
from datetime import datetime, timedelta, timezone
from threading import Lock

import httpx

# Domyślnie przy lokalnym uruchomieniu bez zmiennych środowiskowych.
_DEFAULT_VERSION = "0.3.6"
_RELEASES_URL = "https://api.github.com/repos/blazejwrobel98/Fine-net-dash/releases/latest"
# Tag z GitHub bywa `v0.3.4`; APP_VERSION z CI też — akceptujemy `v` / `V` na początku.
_VERSION_RE = re.compile(r"^[vV]?(\d+)\.(\d+)\.(\d+)$")
# Cache tylko odpowiedzi GitHub (tag + URL). update_available liczymy przy każdym żądaniu —
# inaczej po wydaniu nowego tagu przez ~30 min zwracalibyśmy stare „brak aktualizacji”.
_GITHUB_TTL = timedelta(minutes=5)
_GITHUB_ERR_TTL = timedelta(seconds=90)
_CHECK_LOCK = Lock()
_GITHUB_RELEASE_CACHE: dict[str, object | None] = {
    "at": None,
    "tag_name": None,
    "html_url": None,
    "error": None,
}


def app_version() -> str:
    v = (os.getenv("APP_VERSION") or "").strip()
    return v if v else _DEFAULT_VERSION


def git_sha() -> str:
    return (os.getenv("GIT_SHA") or "").strip()


def clear_github_release_cache() -> None:
    """Wyzeruj cache odpowiedzi GitHub (np. ?refresh=1 na /api/version/update)."""
    with _CHECK_LOCK:
        _GITHUB_RELEASE_CACHE["at"] = None
        _GITHUB_RELEASE_CACHE["tag_name"] = None
        _GITHUB_RELEASE_CACHE["html_url"] = None
        _GITHUB_RELEASE_CACHE["error"] = None


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

    tag_raw: str | None = None
    html_url: str | None = None

    with _CHECK_LOCK:
        gh_at = _GITHUB_RELEASE_CACHE.get("at")
        gh_err = _GITHUB_RELEASE_CACHE.get("error")
        if isinstance(gh_at, datetime):
            age = now - gh_at
            ttl = _GITHUB_ERR_TTL if gh_err else _GITHUB_TTL
            if age < ttl:
                if gh_err:
                    out["error"] = str(gh_err)
                    return dict(out)
                tr = _GITHUB_RELEASE_CACHE.get("tag_name")
                if isinstance(tr, str) and tr.strip():
                    tag_raw = tr.strip()
                    hu = _GITHUB_RELEASE_CACHE.get("html_url")
                    html_url = (str(hu).strip() if hu else None) or None

        if tag_raw is None:
            try:
                with httpx.Client(timeout=4.0, follow_redirects=True) as client:
                    r = client.get(_RELEASES_URL, headers={"Accept": "application/vnd.github+json"})
                    r.raise_for_status()
                    data = r.json()
                tr = str(data.get("tag_name") or "").strip() or None
                hu = str(data.get("html_url") or "").strip() or None
                _GITHUB_RELEASE_CACHE["at"] = now
                _GITHUB_RELEASE_CACHE["tag_name"] = tr
                _GITHUB_RELEASE_CACHE["html_url"] = hu if hu else None
                _GITHUB_RELEASE_CACHE["error"] = None
                tag_raw = tr
                html_url = hu if hu else None
            except Exception as e:
                _GITHUB_RELEASE_CACHE["at"] = now
                _GITHUB_RELEASE_CACHE["tag_name"] = None
                _GITHUB_RELEASE_CACHE["html_url"] = None
                _GITHUB_RELEASE_CACHE["error"] = str(e)
                out["error"] = str(e)
                return dict(out)

    if not tag_raw:
        out["error"] = "GitHub: brak tag_name w odpowiedzi."
        return dict(out)

    latest_tuple = _parse_version(tag_raw)
    latest = (
        tag_raw[1:].strip()
        if len(tag_raw) > 1 and tag_raw[0] in "vV" and tag_raw[1].isdigit()
        else tag_raw
    )
    out["latest_version"] = latest or None
    out["release_url"] = html_url or None
    out["update_available"] = bool(cur_tuple and latest_tuple and latest_tuple > cur_tuple)
    return dict(out)
