import pytest

from app.version_info import _DEFAULT_VERSION, app_version, git_sha


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
