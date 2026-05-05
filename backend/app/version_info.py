"""Numer wydania i identyfikator buildu — widoczne w /api/version i w UI."""

import os

# Domyślnie przy lokalnym uruchomieniu bez zmiennych środowiskowych.
_DEFAULT_VERSION = "0.2.2"


def app_version() -> str:
    v = (os.getenv("APP_VERSION") or "").strip()
    return v if v else _DEFAULT_VERSION


def git_sha() -> str:
    return (os.getenv("GIT_SHA") or "").strip()
