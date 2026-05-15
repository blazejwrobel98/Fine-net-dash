from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CashDeposit, DividendReceipt, PortfolioSnapshot
from app.services.portfolio import lots_by_ticker
from app.services.prices import get_cached_map
from app.services.wallet import get_fx_rates, price_to_pln_per_share, wallet_summary_dict


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _deposit_cumulative_events(deposits: list[CashDeposit]) -> list[tuple[datetime, float]]:
    """Skumulowane wpłaty (CashDeposit) — dywidendy nie wchodzą."""
    events: list[tuple[datetime, float]] = []
    cum = 0.0
    for d in sorted(deposits, key=lambda x: _as_utc(x.received_at)):
        cum += float(d.amount_pln)
        events.append((_as_utc(d.received_at), round(cum, 2)))
    return events


def _cumulative_deposits_at(events: list[tuple[datetime, float]], at: datetime) -> float:
    at_utc = _as_utc(at)
    val = 0.0
    for dt, cum in events:
        if dt <= at_utc:
            val = cum
        else:
            break
    return val


def _equity_point_from_summary(
    summ: dict, at: datetime, *, deposits_cumulative_pln: float
) -> dict:
    return {
        "date": at.isoformat(),
        "total_equity_pln": round(summ["total_equity_pln"], 2),
        "holdings_pln": round(summ["holdings_market_pln"], 2),
        "cash_pln": round(summ["cash_available_pln"], 2),
        "deposits_cumulative_pln": round(deposits_cumulative_pln, 2),
    }


def timeline_payload(db: Session) -> dict:
    snaps = db.execute(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.recorded_at)
    ).scalars().all()
    divs = db.execute(
        select(DividendReceipt).order_by(DividendReceipt.received_at)
    ).scalars().all()
    deposits = db.execute(select(CashDeposit).order_by(CashDeposit.received_at)).scalars().all()
    deposit_events = _deposit_cumulative_events(deposits)

    equity_series: list[dict] = [
        _equity_point_from_summary(
            {
                "total_equity_pln": s.total_equity_pln,
                "holdings_market_pln": s.holdings_value_pln,
                "cash_available_pln": s.cash_pln,
            },
            s.recorded_at,
            deposits_cumulative_pln=_cumulative_deposits_at(deposit_events, s.recorded_at),
        )
        for s in snaps
    ]
    live = wallet_summary_dict(db)
    now = datetime.now(timezone.utc)
    live_deposits = _cumulative_deposits_at(deposit_events, now)
    if not equity_series:
        equity_series.append(_equity_point_from_summary(live, now, deposits_cumulative_pln=live_deposits))
    else:
        last_snap = snaps[-1]
        last_day = last_snap.recorded_at.date()
        if last_day == now.date():
            equity_series[-1] = _equity_point_from_summary(
                live, now, deposits_cumulative_pln=live_deposits
            )
        else:
            equity_series.append(
                _equity_point_from_summary(live, now, deposits_cumulative_pln=live_deposits)
            )

    return {
        "equity_series": equity_series,
        "dividends": [
            {
                "date": d.received_at.isoformat(),
                "amount_pln": round(d.amount_pln, 2),
                "ticker": d.ticker,
                "note": d.note,
            }
            for d in divs
        ],
    }


def allocation_payload(db: Session) -> dict:
    usd, eur = get_fx_rates(db)
    by = lots_by_ticker(db)
    tickers = list(by.keys())
    prices = get_cached_map(db, tickers)
    pos_slices: list[dict] = []
    for t, ls in sorted(by.items()):
        cur = prices.get(t)
        if not cur:
            continue
        pr, ccy = cur
        shares = sum(l.quantity for l in ls)
        v = price_to_pln_per_share(pr, ccy, usd, eur) * shares
        if v <= 0:
            continue
        pos_slices.append({"ticker": t, "value_pln": round(v, 2)})

    summ = wallet_summary_dict(db)
    cash = max(0.0, float(summ["cash_available_pln"]))
    total_pos = sum(x["value_pln"] for x in pos_slices)
    grand = total_pos + cash
    out: list[dict] = []
    if grand > 0:
        for x in pos_slices:
            out.append(
                {
                    "ticker": x["ticker"],
                    "label": x["ticker"],
                    "value_pln": x["value_pln"],
                    "pct": round(100.0 * x["value_pln"] / grand, 2),
                }
            )
        if cash > 0.01:
            out.append(
                {
                    "ticker": "CASH",
                    "label": "Gotówka",
                    "value_pln": round(cash, 2),
                    "pct": round(100.0 * cash / grand, 2),
                }
            )
    return {"slices": out, "total_pln": round(grand, 2)}
