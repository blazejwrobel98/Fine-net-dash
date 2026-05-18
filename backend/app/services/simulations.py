"""Symulacje portfela: lookback (gdyby kupił wcześniej) i projekcja w przód."""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from random import uniform
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.services.portfolio import lots_by_ticker
from app.services.prices import _guess_currency, _load_history, get_cached_map
from app.services.wallet import get_fx_rates, price_to_pln_per_share, wallet_summary_dict

DISCLAIMER = (
    "Modele uproszczone: historyczne ceny Yahoo (lookback), stałe stopy i miesięczna kapitalizacja (projekcja). "
    "Nie uwzględniają podatków, opłat, zmian składu portfela ani scenariuszy makro. Nie jest to porada inwestycyjna."
)


def _period_for_years(years: float) -> str:
    if years <= 1.5:
        return "2y"
    if years <= 3.5:
        return "5y"
    return "10y"


def _monthly_closes(df: pd.DataFrame) -> list[tuple[date, float]]:
    if df is None or df.empty:
        return []
    s = df["Close"].astype(float).resample("ME").last().dropna()
    return [(ts.date(), float(v)) for ts, v in s.items()]


def _price_on_or_before(series: list[tuple[date, float]], on: date) -> float | None:
    val: float | None = None
    for d, p in series:
        if d <= on:
            val = p
        else:
            break
    return val


def _holdings_shares(db: Session) -> dict[str, float]:
    by = lots_by_ticker(db)
    return {
        t: round(sum(float(l.quantity) for l in ls), 6)
        for t, ls in by.items()
        if sum(float(l.quantity) for l in ls) > 0
    }


def lookback_simulation_payload(db: Session, *, years_back: float = 1.0) -> dict[str, Any]:
    """
    Wartość bieżących pozycji w PLN w czasie, jak gdyby trzymał je od (dziś − years_back).
    Koszt „zakupu wtedy” = suma akcji × cena na początku okna.
    """
    years_back = max(0.25, min(float(years_back), 10.0))
    shares_by = _holdings_shares(db)
    if not shares_by:
        return {
            "years_back": years_back,
            "start_date": None,
            "end_date": date.today().isoformat(),
            "virtual_cost_pln": 0.0,
            "current_value_pln": 0.0,
            "actual_invested_pln": 0.0,
            "series": [],
            "disclaimer": DISCLAIMER,
            "note": "Brak pozycji w portfelu.",
        }

    usd, eur = get_fx_rates(db)
    prices = get_cached_map(db, list(shares_by.keys()))
    today = date.today()
    start = today - timedelta(days=int(365.25 * years_back))
    period = _period_for_years(years_back)
    delay = max(0.0, float(settings.yahoo_request_delay_seconds))

    monthly_by_ticker: dict[str, list[tuple[date, float]]] = {}
    failed: list[str] = []

    for i, ticker in enumerate(sorted(shares_by.keys())):
        if i > 0 and delay > 0:
            time.sleep(delay + uniform(0, 0.12))
        ccy = _guess_currency(ticker)
        pc = prices.get(ticker)
        if pc and pc[1]:
            ccy = pc[1]
        df = _load_history(ticker, period, actions=False)
        raw = _monthly_closes(df)
        if not raw:
            failed.append(ticker)
            continue
        monthly_by_ticker[ticker] = [
            (d, price_to_pln_per_share(p, ccy, usd, eur)) for d, p in raw if p > 0
        ]

    all_dates: set[date] = set()
    for series in monthly_by_ticker.values():
        for d, _ in series:
            if start <= d <= today:
                all_dates.add(d)
    if today not in all_dates:
        all_dates.add(today)

    series_out: list[dict[str, Any]] = []
    for d in sorted(all_dates):
        total = 0.0
        for ticker, qty in shares_by.items():
            m = monthly_by_ticker.get(ticker)
            if not m:
                continue
            px = _price_on_or_before(m, d)
            if px is not None:
                total += qty * px
        if total > 0:
            series_out.append({"date": d.isoformat(), "holdings_value_pln": round(total, 2)})

    virtual_cost = 0.0
    for ticker, qty in shares_by.items():
        m = monthly_by_ticker.get(ticker)
        if not m:
            continue
        px = _price_on_or_before(m, start) or (m[0][1] if m else None)
        if px is not None:
            virtual_cost += qty * px

    summ = wallet_summary_dict(db)
    current = float(summ["total_equity_pln"])
    note = None
    if failed:
        note = f"Brak historii Yahoo dla: {', '.join(failed[:8])}{'…' if len(failed) > 8 else ''}."

    return {
        "years_back": years_back,
        "start_date": start.isoformat(),
        "end_date": today.isoformat(),
        "virtual_cost_pln": round(virtual_cost, 2),
        "current_value_pln": round(current, 2),
        "actual_invested_pln": round(float(summ["invested_pln"]), 2),
        "series": series_out,
        "disclaimer": DISCLAIMER,
        "note": note,
    }


def forward_simulation_payload(
    db: Session,
    *,
    years_forward: float = 10.0,
    annual_return_pct: float = 7.0,
    dividend_yield_pct: float = 3.0,
    monthly_deposit_pln: float = 0.0,
) -> dict[str, Any]:
    """Projekcja miesięczna: kapitalizacja zwrotu + dywidenda (reinwest.) + opcjonalne wpłaty."""
    years_forward = max(0.5, min(float(years_forward), 40.0))
    annual_return_pct = max(-50.0, min(float(annual_return_pct), 50.0))
    dividend_yield_pct = max(0.0, min(float(dividend_yield_pct), 30.0))
    monthly_deposit_pln = max(0.0, float(monthly_deposit_pln))

    summ = wallet_summary_dict(db)
    v0 = max(0.0, float(summ["total_equity_pln"]))
    r_m = annual_return_pct / 100.0 / 12.0
    d_m = dividend_yield_pct / 100.0 / 12.0
    months = max(1, int(round(years_forward * 12)))
    today = date.today()

    series: list[dict[str, Any]] = []
    v = v0
    total_deposits = 0.0
    for m in range(months + 1):
        d = today + timedelta(days=int(30.44 * m))
        series.append(
            {
                "date": d.isoformat(),
                "total_equity_pln": round(v, 2),
                "cumulative_deposits_pln": round(total_deposits, 2),
            }
        )
        if m >= months:
            break
        v = v * (1.0 + r_m) + v * d_m + monthly_deposit_pln
        total_deposits += monthly_deposit_pln

    return {
        "years_forward": years_forward,
        "annual_return_pct": annual_return_pct,
        "dividend_yield_pct": dividend_yield_pct,
        "monthly_deposit_pln": round(monthly_deposit_pln, 2),
        "start_equity_pln": round(v0, 2),
        "end_equity_pln": round(v, 2),
        "series": series,
        "disclaimer": DISCLAIMER,
    }
