"""Prognoza dywidend z historii Yahoo (bez gwarancji — spółki zmieniają politykę)."""

from __future__ import annotations

import time
from datetime import date, timedelta
from random import uniform
from statistics import median
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.services.portfolio import lots_by_ticker
from app.services.prices import _guess_currency, get_cached_map, yahoo_dividend_events
from app.services.wallet import get_fx_rates, price_to_pln_per_share

DISCLAIMER_PL = (
    "Szacunek z historii Yahoo (ostatnie wypłaty). Rzeczywiste kwoty i daty mogą się różnić "
    "(podatki, waluta wypłaty, zmiana polityki dywidendowej). Nie jest to porada inwestycyjna."
)


def _trailing_per_share(events: list[tuple[date, float]], days: int = 365) -> float:
    if not events:
        return 0.0
    cutoff = date.today() - timedelta(days=days)
    return sum(amt for d, amt in events if d >= cutoff)


def _median_payment_gap_days(events: list[tuple[date, float]]) -> int | None:
    if len(events) < 2:
        return None
    gaps: list[int] = []
    for i in range(1, len(events)):
        g = (events[i][0] - events[i - 1][0]).days
        if g > 0:
            gaps.append(g)
    if not gaps:
        return None
    return int(median(gaps))


def _avg_last_payment_amount(events: list[tuple[date, float]], n: int = 4) -> float | None:
    if not events:
        return None
    tail = [amt for _, amt in events[-n:]]
    if not tail:
        return None
    return sum(tail) / len(tail)


def _project_payment_dates(
    events: list[tuple[date, float]],
    gap_days: int,
    max_payments: int,
    horizon_end: date,
) -> list[date]:
    if not events or gap_days <= 0:
        return []
    today = date.today()
    last_d = events[-1][0]
    out: list[date] = []
    d = last_d
    safety = 0
    while safety < max_payments * 8 + 24:
        safety += 1
        d = d + timedelta(days=gap_days)
        if d > horizon_end:
            break
        if d >= today:
            out.append(d)
        if len(out) >= max_payments:
            break
    return out


def dividend_forecast_payload(db: Session, *, horizon_days: int = 365) -> dict[str, Any]:
    usd, eur = get_fx_rates(db)
    by = lots_by_ticker(db)
    tickers = sorted(by.keys())
    prices = get_cached_map(db, tickers)
    delay = max(0.0, float(settings.yahoo_request_delay_seconds))

    holdings_out: list[dict[str, Any]] = []
    total_trailing = 0.0
    total_upcoming_horizon = 0.0
    horizon_end = date.today() + timedelta(days=horizon_days)

    for i, ticker in enumerate(tickers):
        if i > 0 and delay > 0:
            time.sleep(delay + uniform(0, 0.15))
        shares = sum(l.quantity for l in by[ticker])
        if shares <= 0:
            continue

        ccy = _guess_currency(ticker)
        pc = prices.get(ticker)
        if pc and pc[1]:
            ccy = pc[1]

        events = yahoo_dividend_events(ticker, "2y")
        trailing_ps = _trailing_per_share(events, 365)
        trailing_pln = price_to_pln_per_share(trailing_ps, ccy, usd, eur) * shares
        total_trailing += trailing_pln

        gap = _median_payment_gap_days(events)
        avg_pay = _avg_last_payment_amount(events, 4)
        upcoming: list[dict[str, Any]] = []
        note: str | None = None

        if not events:
            note = "Brak historii dywidend w Yahoo."
        elif trailing_ps <= 0:
            note = "Brak wypłat w ostatnich 12 mies. (wg Yahoo)."
        elif gap is None or gap < 14:
            note = "Za mało wypłat do szacowania terminów — tylko suma roczna."
        elif avg_pay is None or avg_pay <= 0:
            note = None
        else:
            for pay_d in _project_payment_dates(events, gap, max_payments=8, horizon_end=horizon_end):
                amt_pln = round(price_to_pln_per_share(avg_pay, ccy, usd, eur) * shares, 2)
                upcoming.append({"estimated_date": pay_d.isoformat(), "amount_pln_estimate": amt_pln})
                total_upcoming_horizon += amt_pln

        holdings_out.append(
            {
                "ticker": ticker,
                "shares": round(shares, 6),
                "currency": ccy,
                "trailing_12m_per_share": round(trailing_ps, 6),
                "trailing_12m_pln_estimate": round(trailing_pln, 2),
                "median_days_between_payments": gap,
                "avg_recent_payment_per_share": round(avg_pay, 6) if avg_pay is not None else None,
                "upcoming": upcoming,
                "note": note,
            }
        )

    return {
        "holdings": holdings_out,
        "total_trailing_12m_pln_estimate": round(total_trailing, 2),
        "total_upcoming_horizon_pln_estimate": round(total_upcoming_horizon, 2),
        "horizon_days": horizon_days,
        "disclaimer": DISCLAIMER_PL,
    }
