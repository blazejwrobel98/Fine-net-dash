"""Cache prognozy dywidend (plik JSON) — bez ponownego odpytywania Yahoo przy każdym wejściu w UI."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.services.dividend_forecast import DISCLAIMER_PL, dividend_forecast_payload
from app.services.portfolio import lots_by_ticker

logger = logging.getLogger(__name__)
_CACHE_LOCK = Lock()
_CACHE_FILE = BASE_DIR / "data" / "dividend-forecast-cache.json"
_FORECAST_TTL = timedelta(hours=24)


def holdings_signature(db: Session) -> dict[str, float]:
    by = lots_by_ticker(db)
    out: dict[str, float] = {}
    for t, ls in by.items():
        q = sum(float(l.quantity) for l in ls)
        if q > 0:
            out[t] = round(q, 6)
    return out


def _read_cache_file() -> dict[str, Any] | None:
    if not _CACHE_FILE.is_file():
        return None
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.warning("dividend forecast cache read failed: %s", e)
        return None


def _write_cache_file(data: dict[str, Any]) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_forecast_cache(db: Session, payload: dict[str, Any], *, horizon_days: int) -> None:
    envelope = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "horizon_days": horizon_days,
        "holdings_signature": holdings_signature(db),
        "payload": payload,
    }
    with _CACHE_LOCK:
        _write_cache_file(envelope)


def refresh_forecast_cache(db: Session, *, horizon_days: int = 365) -> dict[str, Any]:
    payload = dividend_forecast_payload(db, horizon_days=horizon_days)
    save_forecast_cache(db, payload, horizon_days=horizon_days)
    return payload


def _rescale_holding(h: dict[str, Any], new_shares: float) -> dict[str, Any]:
    out = deepcopy(h)
    old = float(out.get("shares") or 0)
    out["shares"] = new_shares
    if old <= 0:
        return out
    ratio = new_shares / old
    out["trailing_12m_pln_estimate"] = round(float(out["trailing_12m_pln_estimate"]) * ratio, 2)
    for u in out.get("upcoming") or []:
        u["amount_pln_estimate"] = round(float(u["amount_pln_estimate"]) * ratio, 2)
    return out


def _apply_shares_to_payload(
    payload: dict[str, Any],
    *,
    current_sig: dict[str, float],
    cached_sig: dict[str, float],
) -> tuple[dict[str, Any], bool, bool]:
    cached_by = {h["ticker"]: h for h in payload.get("holdings") or []}
    current_tickers = set(current_sig.keys())
    cached_tickers = set(cached_sig.keys())
    refresh_recommended = current_tickers != cached_tickers

    holdings_out: list[dict[str, Any]] = []
    shares_resynced = False
    total_trailing = 0.0
    total_upcoming = 0.0

    for ticker in sorted(current_tickers):
        new_shares = current_sig[ticker]
        if ticker not in cached_by:
            refresh_recommended = True
            continue
        old_shares = float(cached_sig.get(ticker) or 0)
        if abs(new_shares - old_shares) > 1e-9:
            shares_resynced = True
        h = _rescale_holding(cached_by[ticker], new_shares)
        holdings_out.append(h)
        total_trailing += float(h["trailing_12m_pln_estimate"])
        for u in h.get("upcoming") or []:
            total_upcoming += float(u["amount_pln_estimate"])

    out = deepcopy(payload)
    out["holdings"] = holdings_out
    out["total_trailing_12m_pln_estimate"] = round(total_trailing, 2)
    out["total_upcoming_horizon_pln_estimate"] = round(total_upcoming, 2)
    return out, shares_resynced, refresh_recommended


def _cache_age_ok(generated_at: str | None) -> bool:
    if not generated_at:
        return False
    try:
        at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - at < _FORECAST_TTL
    except ValueError:
        return False


def dividend_forecast_for_api(
    db: Session,
    *,
    horizon_days: int = 365,
    refresh: bool = False,
) -> dict[str, Any]:
    empty_meta = {
        "from_cache": False,
        "generated_at_utc": None,
        "shares_resynced": False,
        "refresh_recommended": True,
    }

    if refresh:
        payload = refresh_forecast_cache(db, horizon_days=horizon_days)
        return {
            **payload,
            **empty_meta,
            "from_cache": False,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "refresh_recommended": False,
        }

    with _CACHE_LOCK:
        envelope = _read_cache_file()

    if not envelope or "payload" not in envelope:
        return {
            "holdings": [],
            "total_trailing_12m_pln_estimate": 0.0,
            "total_upcoming_horizon_pln_estimate": 0.0,
            "horizon_days": horizon_days,
            "disclaimer": DISCLAIMER_PL,
            **empty_meta,
        }

    cached_horizon = int(envelope.get("horizon_days") or horizon_days)
    payload = deepcopy(envelope["payload"])
    payload["horizon_days"] = cached_horizon
    generated_at = str(envelope.get("generated_at_utc") or "")

    current_sig = holdings_signature(db)
    cached_sig = envelope.get("holdings_signature") or {}
    if not isinstance(cached_sig, dict):
        cached_sig = {}

    payload, shares_resynced, sig_mismatch = _apply_shares_to_payload(
        payload,
        current_sig=current_sig,
        cached_sig={k: float(v) for k, v in cached_sig.items()},
    )

    age_ok = _cache_age_ok(generated_at)
    return {
        **payload,
        "from_cache": True,
        "generated_at_utc": generated_at or None,
        "shares_resynced": shares_resynced,
        "refresh_recommended": sig_mismatch or not age_ok,
    }


def cache_needs_daily_refresh() -> bool:
    envelope = _read_cache_file()
    if not envelope:
        return True
    return not _cache_age_ok(str(envelope.get("generated_at_utc") or ""))
