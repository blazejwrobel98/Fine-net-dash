from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AppSettings, CashDeposit, DividendReceipt, PortfolioSnapshot, PurchaseLot, SaleTransaction
from app.services.portfolio import lots_by_ticker
from app.services.prices import _guess_currency, get_cached_map


def price_to_pln_per_share(price: float, currency: str | None, usd_pln: float, eur_pln: float) -> float:
    if currency is None:
        return price
    u = currency.upper()
    if u in ("PLN", "PL"):
        return price
    if u == "USD":
        return price * usd_pln
    if u == "EUR":
        return price * eur_pln
    if u in ("GBP",):
        return price * usd_pln * 1.27
    if u in ("GBX", "GBp"):
        return (price / 100.0) * usd_pln * 1.27
    if u == "CHF":
        return price * eur_pln * 1.05
    if u == "DKK":
        return price * eur_pln * 0.134
    if u == "SEK":
        return price * eur_pln * 0.092
    return price * usd_pln


def get_fx_rates(db: Session) -> tuple[float, float]:
    s = db.execute(select(AppSettings).where(AppSettings.id == 1)).scalar_one()
    usd = float(s.usd_pln_rate) if s.usd_pln_rate is not None else 4.0
    eur = float(s.eur_pln_rate) if s.eur_pln_rate is not None else 4.3
    return usd, eur


def sum_deposits_pln(db: Session) -> float:
    v = db.execute(select(func.coalesce(func.sum(CashDeposit.amount_pln), 0.0))).scalar_one()
    return float(v)


def sum_dividends_pln(db: Session) -> float:
    v = db.execute(select(func.coalesce(func.sum(DividendReceipt.amount_pln), 0.0))).scalar_one()
    return float(v)


def sum_sales_proceeds_pln(db: Session) -> float:
    v = db.execute(select(func.coalesce(func.sum(SaleTransaction.proceeds_pln), 0.0))).scalar_one()
    return float(v)


def sum_realized_pnl_pln(db: Session) -> float:
    v = db.execute(select(func.coalesce(func.sum(SaleTransaction.realized_pln), 0.0))).scalar_one()
    return float(v)


def sum_invested_pln(db: Session) -> float:
    """
    Suma kosztów zakupów przeliczona na PLN.
    price_per_share jest w walucie instrumentu (lot.currency); kursy z Ustawień.
    """
    lots = db.execute(select(PurchaseLot)).scalars().all()
    usd, eur = get_fx_rates(db)
    total = 0.0
    for l in lots:
        ccy = getattr(l, "currency", None) or _guess_currency(l.ticker) or "PLN"
        total += price_to_pln_per_share(float(l.price_per_share), ccy, usd, eur) * float(l.quantity)
    return float(round(total, 2))


def holdings_market_value_pln(db: Session) -> float:
    usd, eur = get_fx_rates(db)
    by = lots_by_ticker(db)
    tickers = list(by.keys())
    prices = get_cached_map(db, tickers)
    total = 0.0
    for t, ls in by.items():
        cur = prices.get(t)
        if not cur:
            continue
        pr, ccy = cur
        shares = sum(l.quantity for l in ls)
        total += price_to_pln_per_share(pr, ccy, usd, eur) * shares
    return round(total, 2)


def wallet_summary_dict(db: Session) -> dict[str, Any]:
    deposits = sum_deposits_pln(db)
    dividends = sum_dividends_pln(db)
    sales = sum_sales_proceeds_pln(db)
    realized = sum_realized_pnl_pln(db)
    invested = sum_invested_pln(db)
    cash = deposits + dividends + sales - invested
    holdings = holdings_market_value_pln(db)
    equity = holdings + cash
    return {
        "deposits_total_pln": round(deposits, 2),
        "dividends_total_pln": round(dividends, 2),
        "sales_proceeds_total_pln": round(sales, 2),
        "realized_pnl_total_pln": round(realized, 2),
        "invested_pln": round(invested, 2),
        "cash_available_pln": round(cash, 2),
        "holdings_market_pln": round(holdings, 2),
        "total_equity_pln": round(equity, 2),
    }


def upsert_today_snapshot(db: Session) -> None:
    summ = wallet_summary_dict(db)
    # Data „dziś” w UTC — spójnie z zapisem snapshotów (timezone-aware).
    now = datetime.now(timezone.utc)
    today = now.date()
    start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end = datetime.combine(today, time.max, tzinfo=timezone.utc)
    row = db.execute(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.recorded_at >= start,
            PortfolioSnapshot.recorded_at <= end,
        )
    ).scalar_one_or_none()
    if row:
        row.holdings_value_pln = summ["holdings_market_pln"]
        row.cash_pln = summ["cash_available_pln"]
        row.total_equity_pln = summ["total_equity_pln"]
        row.recorded_at = now
    else:
        db.add(
            PortfolioSnapshot(
                recorded_at=now,
                holdings_value_pln=summ["holdings_market_pln"],
                cash_pln=summ["cash_available_pln"],
                total_equity_pln=summ["total_equity_pln"],
            )
        )
    db.commit()
