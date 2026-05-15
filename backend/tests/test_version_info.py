from datetime import datetime, timezone

import pytest

from app.version_info import (
    _DEFAULT_VERSION,
    _parse_version,
    app_version,
    check_update_available,
    clear_github_release_cache,
    git_sha,
)


def test_app_version_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    assert app_version() == _DEFAULT_VERSION
    assert len(_DEFAULT_VERSION) > 0


def test_app_version_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_VERSION", "9.9.9-test")
    assert app_version() == "9.9.9-test"


def test_git_sha_empty_when_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GIT_SHA", raising=False)
    assert git_sha() == ""


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0.3.4", (0, 3, 4)),
        ("v0.3.4", (0, 3, 4)),
        ("V0.3.4", (0, 3, 4)),
        ("v12.0.1", (12, 0, 1)),
        ("bad", None),
    ],
)
def test_parse_version(raw: str, expected: tuple[int, int, int] | None):
    assert _parse_version(raw) == expected


def test_update_available_recomputed_for_each_current_with_cached_github():
    """Cachujemy tag z GitHuba, ale update_available zależy od przekazanej wersji bieżącej."""
    import app.version_info as vi

    now = datetime.now(timezone.utc)
    vi._GITHUB_RELEASE_CACHE.clear()
    vi._GITHUB_RELEASE_CACHE.update(
        {"at": now, "tag_name": "v0.3.4", "html_url": "https://example.com/release", "error": None},
    )

    older = check_update_available("0.3.3")
    assert older["update_available"] is True
    assert older["latest_version"] == "0.3.4"
    assert older["current_version"] == "0.3.3"

    same = check_update_available("0.3.4")
    assert same["update_available"] is False
    assert same["current_version"] == "0.3.4"


def test_clear_github_release_cache_clears_tag():
    import app.version_info as vi

    now = datetime.now(timezone.utc)
    vi._GITHUB_RELEASE_CACHE.clear()
    vi._GITHUB_RELEASE_CACHE.update(
        {"at": now, "tag_name": "v0.1.0", "html_url": "https://x", "error": None},
    )
    clear_github_release_cache()
    assert vi._GITHUB_RELEASE_CACHE.get("tag_name") is None
    assert vi._GITHUB_RELEASE_CACHE.get("at") is None
