from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from typing import Literal


class UniverseStockOut(BaseModel):
    id: int
    ticker: str
    name: str
    region: str
    sector: str | None = None
    notes: str | None

    model_config = {"from_attributes": True}


class UniverseRowOut(BaseModel):
    id: int
    ticker: str
    name: str
    region: str
    sector: str | None
    notes: str | None
    price: float | None
    currency: str | None
    dividend_yield_pct: float | None
    change_1d_pct: float | None
    change_1w_pct: float | None
    change_1m_pct: float | None
    change_1y_pct: float | None
    change_5y_pct: float | None
    avg_price_1d: float | None
    avg_price_1w: float | None
    avg_price_1m: float | None
    avg_price_1y: float | None
    avg_price_5y: float | None
    updated_at: datetime | None


class UniverseListResponse(BaseModel):
    stocks: list[UniverseRowOut]
    last_prices_update: datetime | None


class PurchaseLotCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=32)
    quantity: float = Field(..., gt=0)
    price_per_share: float = Field(..., gt=0)
    side: Literal["buy", "sell"] = "buy"
    purchased_at: datetime | None = None

    @field_validator("ticker", mode="before")
    @classmethod
    def upper_ticker(cls, v: str) -> str:
        return str(v).strip().upper()


class PurchaseLotOut(BaseModel):
    id: int
    ticker: str
    quantity: float
    price_per_share: float
    currency: str | None = None
    purchased_at: datetime

    model_config = {"from_attributes": True}


class TradeResultOut(BaseModel):
    side: Literal["buy", "sell"]
    ticker: str
    quantity: float
    price_per_share: float
    currency: str | None = None
    proceeds_pln: float | None = None
    cost_basis_pln: float | None = None
    realized_pln: float | None = None
    remaining_shares: float | None = None
    sold_at: datetime | None = None


class SaleTransactionOut(BaseModel):
    id: int
    ticker: str
    quantity: float
    price_per_share: float
    currency: str | None
    proceeds_pln: float
    cost_basis_pln: float
    realized_pln: float
    sold_at: datetime

    model_config = {"from_attributes": True}


class PositionSummary(BaseModel):
    ticker: str
    total_shares: float
    avg_buy_price: float
    total_cost: float
    current_price: float | None
    currency: str | None
    pct_vs_avg: float | None


class SettingsOut(BaseModel):
    alert_threshold_percent: float
    alerts_enabled: bool
    ntfy_topic: str | None
    ntfy_server_url: str
    price_check_interval_minutes: int
    universe_price_interval_minutes: int
    usd_pln_rate: float
    eur_pln_rate: float
    fx_nbp_auto: bool
    fx_nbp_last_run_date: str | None = None


class SettingsUpdate(BaseModel):
    alert_threshold_percent: float | None = Field(None, ge=0.1, le=50)
    alerts_enabled: bool | None = None
    ntfy_topic: str | None = None
    ntfy_server_url: str | None = None
    price_check_interval_minutes: int | None = Field(None, ge=5, le=1440)
    universe_price_interval_minutes: int | None = Field(None, ge=15, le=1440)
    usd_pln_rate: float | None = Field(None, gt=0)
    eur_pln_rate: float | None = Field(None, gt=0)
    fx_nbp_auto: bool | None = None


class FxRatesRefreshOut(BaseModel):
    usd_pln_rate: float
    eur_pln_rate: float
    source: str
    effective_date: str
    fx_nbp_auto: bool
    fx_nbp_last_run_date: str | None = None


class RefreshPricesResult(BaseModel):
    updated: int
    failed: list[str]


class BackupFileOut(BaseModel):
    file_name: str
    size_bytes: int
    created_at: datetime
    kind: str


class BackupListOut(BaseModel):
    files: list[BackupFileOut]


class BackupCreateOut(BaseModel):
    created: bool
    file_name: str | None = None
    message: str


class BackupRestoreIn(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=256)


class BackupRestoreOut(BaseModel):
    restored: bool
    message: str
    records: int | None = None


class CheckAlertsResult(BaseModel):
    sent: int
    skipped: list[str]
    notes: list[str] = []


class NtfyTestResult(BaseModel):
    ok: bool
    message: str


class CashDepositCreate(BaseModel):
    amount_pln: float = Field(..., gt=0)
    received_at: datetime | None = None
    note: str | None = None


class CashDepositOut(BaseModel):
    id: int
    amount_pln: float
    received_at: datetime
    note: str | None

    model_config = {"from_attributes": True}


class DividendReceiptCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=32)
    amount_pln: float = Field(..., gt=0)
    received_at: datetime | None = None
    note: str | None = None

    @field_validator("ticker", mode="before")
    @classmethod
    def upper_ticker(cls, v: str) -> str:
        return str(v).strip().upper()


class DividendReceiptOut(BaseModel):
    id: int
    ticker: str
    amount_pln: float
    received_at: datetime
    note: str | None

    model_config = {"from_attributes": True}


class WalletSummaryOut(BaseModel):
    deposits_total_pln: float
    dividends_total_pln: float
    invested_pln: float
    cash_available_pln: float
    holdings_market_pln: float
    total_equity_pln: float
    sales_proceeds_total_pln: float = 0.0
    realized_pnl_total_pln: float = 0.0


class DividendForecastPaymentOut(BaseModel):
    estimated_date: str
    amount_pln_estimate: float


class DividendForecastHoldingOut(BaseModel):
    ticker: str
    shares: float
    currency: str | None
    trailing_12m_per_share: float
    trailing_12m_pln_estimate: float
    median_days_between_payments: int | None
    avg_recent_payment_per_share: float | None
    upcoming: list[DividendForecastPaymentOut]
    note: str | None = None


class DividendForecastResponse(BaseModel):
    holdings: list[DividendForecastHoldingOut]
    total_trailing_12m_pln_estimate: float
    total_upcoming_horizon_pln_estimate: float
    horizon_days: int
    disclaimer: str
