from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PurchaseLot, SaleTransaction
from app.services.prices import _guess_currency, get_price_rows
from app.services.wallet import get_fx_rates, price_to_pln_per_share


def detect_trade_currency(db: Session, ticker: str) -> str | None:
    pc = get_price_rows(db, [ticker]).get(ticker)
    if pc and pc.currency:
        return pc.currency
    return _guess_currency(ticker)


def execute_sell_fifo(
    db: Session,
    ticker: str,
    quantity: float,
    sell_price_per_share: float,
    sold_at: datetime,
) -> SaleTransaction:
    lots = db.execute(
        select(PurchaseLot).where(PurchaseLot.ticker == ticker).order_by(PurchaseLot.purchased_at, PurchaseLot.id)
    ).scalars().all()
    total_shares = sum(float(l.quantity) for l in lots)
    if total_shares + 1e-9 < quantity:
        raise HTTPException(400, f"Za mało akcji {ticker} do sprzedaży. Dostępne: {round(total_shares, 6)}")

    ccy = detect_trade_currency(db, ticker) or "PLN"
    usd, eur = get_fx_rates(db)
    to_sell = quantity
    cost_basis_pln = 0.0

    for l in lots:
        if to_sell <= 1e-12:
            break
        take = min(float(l.quantity), to_sell)
        lot_ccy = l.currency or ccy
        cost_basis_pln += price_to_pln_per_share(float(l.price_per_share), lot_ccy, usd, eur) * take
        l.quantity = float(l.quantity) - take
        to_sell -= take
        if l.quantity <= 1e-12:
            db.delete(l)

    proceeds_pln = price_to_pln_per_share(sell_price_per_share, ccy, usd, eur) * quantity
    realized = proceeds_pln - cost_basis_pln
    sale = SaleTransaction(
        ticker=ticker,
        quantity=quantity,
        price_per_share=sell_price_per_share,
        currency=ccy,
        proceeds_pln=round(proceeds_pln, 2),
        cost_basis_pln=round(cost_basis_pln, 2),
        realized_pln=round(realized, 2),
        sold_at=sold_at,
    )
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale
