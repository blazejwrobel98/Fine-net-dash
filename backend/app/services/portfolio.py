from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PurchaseLot
from app.schemas import PositionSummary
from app.services.prices import get_cached_map


def lots_by_ticker(db: Session) -> dict[str, list[PurchaseLot]]:
    lots = db.execute(select(PurchaseLot)).scalars().all()
    by: dict[str, list[PurchaseLot]] = defaultdict(list)
    for lot in lots:
        by[lot.ticker.upper()].append(lot)
    return by


def positions_summary(db: Session) -> list[PositionSummary]:
    by = lots_by_ticker(db)
    tickers = list(by.keys())
    prices = get_cached_map(db, tickers)
    out: list[PositionSummary] = []
    for ticker, lots in sorted(by.items()):
        total_shares = sum(l.quantity for l in lots)
        total_cost = sum(l.quantity * l.price_per_share for l in lots)
        avg = total_cost / total_shares if total_shares else 0.0
        cur = prices.get(ticker)
        current_price = cur[0] if cur else None
        currency = cur[1] if cur else None
        pct = None
        if current_price is not None and avg > 0:
            pct = (current_price / avg - 1.0) * 100.0
        out.append(
            PositionSummary(
                ticker=ticker,
                total_shares=total_shares,
                avg_buy_price=round(avg, 6),
                total_cost=round(total_cost, 2),
                current_price=round(current_price, 6) if current_price is not None else None,
                currency=currency,
                pct_vs_avg=round(pct, 2) if pct is not None else None,
            )
        )
    return out
