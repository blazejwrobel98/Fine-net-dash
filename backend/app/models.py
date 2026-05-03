from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UniverseStock(Base):
    __tablename__ = "universe_stocks"
    __table_args__ = (UniqueConstraint("ticker", name="uq_universe_ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    region: Mapped[str] = mapped_column(String(8), nullable=False)  # pl | eu | us
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PurchaseLot(Base):
    __tablename__ = "purchase_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_share: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)


class SaleTransaction(Base):
    __tablename__ = "sale_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_share: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    proceeds_pln: Mapped[float] = mapped_column(Float, nullable=False)
    cost_basis_pln: Mapped[float] = mapped_column(Float, nullable=False)
    realized_pln: Mapped[float] = mapped_column(Float, nullable=False)
    sold_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_threshold_percent: Mapped[float] = mapped_column(Float, default=2.0)
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ntfy_topic: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ntfy_server_url: Mapped[str] = mapped_column(String(512), default="https://ntfy.sh")
    price_check_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    universe_price_interval_minutes: Mapped[int] = mapped_column(Integer, default=120)
    usd_pln_rate: Mapped[float] = mapped_column(Float, default=4.0)
    eur_pln_rate: Mapped[float] = mapped_column(Float, default=4.3)
    fx_nbp_auto: Mapped[bool] = mapped_column(Boolean, default=False)
    fx_nbp_last_run_date: Mapped[str | None] = mapped_column(String(16), nullable=True)


class PriceCache(Base):
    __tablename__ = "price_cache"
    __table_args__ = (UniqueConstraint("ticker", name="uq_price_ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)
    dividend_yield_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_1d_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_1w_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_1m_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_1y_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_5y_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_price_1d: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_price_1w: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_price_1m: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_price_1y: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_price_5y: Mapped[float | None] = mapped_column(Float, nullable=True)


class AlertCooldown(Base):
    __tablename__ = "alert_cooldowns"
    __table_args__ = (UniqueConstraint("ticker", name="uq_cooldown_ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reference_avg_price: Mapped[float] = mapped_column(Float, nullable=False)


class CashDeposit(Base):
    __tablename__ = "cash_deposits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    amount_pln: Mapped[float] = mapped_column(Float, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class DividendReceipt(Base):
    __tablename__ = "dividend_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount_pln: Mapped[float] = mapped_column(Float, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, index=True)
    holdings_value_pln: Mapped[float] = mapped_column(Float, nullable=False)
    cash_pln: Mapped[float] = mapped_column(Float, nullable=False)
    total_equity_pln: Mapped[float] = mapped_column(Float, nullable=False)
