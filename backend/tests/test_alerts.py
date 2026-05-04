"""Regresja: cooldown alertów vs naive datetime z SQLite."""

from datetime import datetime, timedelta, timezone

from app.services import alerts


def test_as_utc_aware_naive_subtracts_against_utc_now():
    naive = datetime(2026, 1, 1, 10, 0, 0)
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert now - alerts._as_utc_aware(naive) == timedelta(hours=2)


def test_as_utc_aware_preserves_utc_zones():
    aware = datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    assert alerts._as_utc_aware(aware) == aware
