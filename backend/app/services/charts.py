from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DividendReceipt, PortfolioSnapshot
from app.services.portfolio import lots_by_ticker
from app.services.prices import get_cached_map
from app.services.wallet import get_fx_rates, price_to_pln_per_share, wallet_summary_dict


def _equity_point_from_summary(summ: dict, at: datetime) -> dict:
    return {
        "date": at.isoformat(),
        "total_equity_pln": round(summ["total_equity_pln"], 2),
        "holdings_pln": round(summ["holdings_market_pln"], 2),
        "cash_pln": round(summ["cash_available_pln"], 2),
    }


def timeline_payload(db: Session) -> dict:
    snaps = db.execute(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.recorded_at)
    ).scalars().all()
    divs = db.execute(
        select(DividendReceipt).order_by(DividendReceipt.received_at)
    ).scalars().all()

    equity_series: list[dict] = [
        {
            "date": s.recorded_at.isoformat(),
            "total_equity_pln": round(s.total_equity_pln, 2),
            "holdings_pln": round(s.holdings_value_pln, 2),
            "cash_pln": round(s.cash_pln, 2),
        }
        for s in snaps
    ]
    live = wallet_summary_dict(db)
    now = datetime.utcnow()
    if not equity_series:
        equity_series.append(_equity_point_from_summary(live, now))
    else:
        last_snap = snaps[-1]
        last_day = last_snap.recorded_at.date()
        if last_day == now.date():
            equity_series[-1] = _equity_point_from_summary(live, now)
        else:
            equity_series.append(_equity_point_from_summary(live, now))

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
