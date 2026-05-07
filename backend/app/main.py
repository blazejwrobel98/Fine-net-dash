import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db, init_db
from app.models import AppSettings, CashDeposit, DividendReceipt, PurchaseLot, SaleTransaction, UniverseStock
from app.schemas import (
    BackupCreateOut,
    BackupListOut,
    BackupRestoreIn,
    BackupRestoreOut,
    CashDepositCreate,
    CashDepositOut,
    CheckAlertsResult,
    DividendForecastResponse,
    DividendReceiptCreate,
    DividendReceiptOut,
    FxRatesRefreshOut,
    NtfyTestResult,
    PositionSummary,
    PurchaseLotCreate,
    PurchaseLotOut,
    RefreshPricesResult,
    SaleTransactionOut,
    SettingsOut,
    SettingsUpdate,
    TradeResultOut,
    UniverseListResponse,
    UniverseRowOut,
    WalletSummaryOut,
)
from app.seed_universe import ensure_default_settings, seed_universe_if_empty, sync_universe_additions
from app.security_middleware import SecurityHeadersMiddleware
from app.services.alerts import check_and_notify_sync, send_ntfy_test_ping
from app.services.backups import (
    backup_portfolio_now,
    backup_price_history_incremental_daily,
    backup_price_history_snapshot_now,
    import_portfolio_backup_file,
    import_prices_backup_file,
    list_portfolio_backups,
    list_prices_backups,
    resolve_portfolio_backup_file,
    resolve_prices_backup_file,
    restore_portfolio_from_backup,
    restore_prices_from_snapshot,
)
from app.services.charts import allocation_payload, timeline_payload
from app.services.dividend_forecast import dividend_forecast_payload
from app.services.fx import fetch_nbp_usd_eur_pln, nbp_scheduler_day_key
from app.services.portfolio import positions_summary
from app.services.prices import get_price_rows, last_prices_update_global, refresh_tickers
from app.services.trades import detect_trade_currency, execute_sell_fifo
from app.services.wallet import upsert_today_snapshot, wallet_summary_dict

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _snapshot_safe(db: Session) -> None:
    try:
        upsert_today_snapshot(db)
    except Exception as e:
        logger.warning("upsert_today_snapshot: %s", e)


def _portfolio_backup_safe(reason: str) -> None:
    try:
        backup_portfolio_now(reason=reason)
    except Exception as e:
        logger.warning("portfolio backup (%s): %s", reason, e)


def _portfolio_change_safe(db: Session, reason: str) -> None:
    _snapshot_safe(db)
    _portfolio_backup_safe(reason)


def _portfolio_prices_job() -> None:
    """Tylko tickery z portfela (loty) + snapshot + NBP + alerty."""
    db = SessionLocal()
    try:
        settings_row = db.execute(select(AppSettings).where(AppSettings.id == 1)).scalar_one_or_none()
        tickers = sorted(set(db.execute(select(PurchaseLot.ticker).distinct()).scalars().all()))
        if tickers:
            refresh_tickers(db, tickers)
        if settings_row:
            _nbp_auto_fetch_if_due(db, settings_row)
        _snapshot_safe(db)
        if settings_row and settings_row.alerts_enabled and (settings_row.ntfy_topic or "").strip():
            sent, skipped, _notes = check_and_notify_sync(db)
            if sent:
                logger.info("Alerts sent: %s, skipped: %s", sent, skipped)
    except Exception as e:
        logger.exception("Portfolio prices job failed: %s", e)
    finally:
        db.close()


def _universe_prices_job() -> None:
    """Lista spółek poza portfelem — rzadziej, wolniej (mniej tickerów na cykl)."""
    db = SessionLocal()
    try:
        lots = set(db.execute(select(PurchaseLot.ticker).distinct()).scalars().all())
        universe = db.execute(select(UniverseStock.ticker)).scalars().all()
        only_universe = sorted(set(universe) - lots)
        if only_universe:
            refresh_tickers(db, only_universe)
    except Exception as e:
        logger.exception("Universe prices job failed: %s", e)
    finally:
        db.close()


def _price_history_backup_job() -> None:
    """Dzienny backup przyrostowy historii cen (delta vs poprzedni dzień)."""
    db = SessionLocal()
    try:
        backup_price_history_incremental_daily(db)
    except Exception as e:
        logger.exception("Price history backup job failed: %s", e)
    finally:
        db.close()


def _reschedule_price_jobs(s: AppSettings) -> None:
    if os.getenv("SKIP_SCHEDULER") == "1":
        return
    p_mins = max(5, int(s.price_check_interval_minutes or 30))
    u_mins = max(15, int(getattr(s, "universe_price_interval_minutes", None) or 120))
    if scheduler.get_job("portfolio_prices"):
        scheduler.reschedule_job(
            "portfolio_prices",
            trigger=IntervalTrigger(minutes=p_mins),
        )
    if scheduler.get_job("universe_prices"):
        scheduler.reschedule_job(
            "universe_prices",
            trigger=IntervalTrigger(minutes=u_mins),
        )


def _nbp_auto_fetch_if_due(db: Session, s: AppSettings) -> None:
    if not s.fx_nbp_auto:
        return
    day = nbp_scheduler_day_key()
    if (s.fx_nbp_last_run_date or "") == day:
        return
    try:
        usd, eur, _eff = fetch_nbp_usd_eur_pln()
    except Exception as e:
        logger.warning("NBP auto FX: %s", e)
        return
    s.usd_pln_rate = usd
    s.eur_pln_rate = eur
    s.fx_nbp_last_run_date = day
    db.commit()
    _snapshot_safe(db)


def _bootstrap_db():
    init_db()
    db = SessionLocal()
    try:
        seed_universe_if_empty(db, UniverseStock)
        sync_universe_additions(db, UniverseStock)
        ensure_default_settings(db, AppSettings)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _bootstrap_db()
    if os.getenv("SKIP_SCHEDULER") != "1":
        db = SessionLocal()
        try:
            s = db.execute(select(AppSettings).where(AppSettings.id == 1)).scalar_one()
            portfolio_mins = max(5, int(s.price_check_interval_minutes or 30))
            universe_mins = max(15, int(getattr(s, "universe_price_interval_minutes", None) or 120))
        finally:
            db.close()
        scheduler.add_job(
            _portfolio_prices_job,
            IntervalTrigger(minutes=portfolio_mins),
            id="portfolio_prices",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )
        scheduler.add_job(
            _universe_prices_job,
            IntervalTrigger(minutes=universe_mins),
            id="universe_prices",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )
        scheduler.add_job(
            _price_history_backup_job,
            CronTrigger(hour=23, minute=55),
            id="prices_daily_backup",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=7200,
        )
        scheduler.start()
    yield
    if os.getenv("SKIP_SCHEDULER") != "1":
        scheduler.shutdown(wait=False)


_openapi = "/docs" if settings.enable_openapi else None
app = FastAPI(
    title="Portfel dywidendowy",
    lifespan=lifespan,
    docs_url=_openapi,
    redoc_url="/redoc" if settings.enable_openapi else None,
    openapi_url="/openapi.json" if settings.enable_openapi else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_th = [h.strip() for h in settings.trusted_hosts.split(",") if h.strip()]
if _th:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_th)

app.add_middleware(SecurityHeadersMiddleware)


def get_settings_row(db: Session) -> AppSettings:
    row = db.execute(select(AppSettings).where(AppSettings.id == 1)).scalar_one_or_none()
    if not row:
        ensure_default_settings(db, AppSettings)
        row = db.execute(select(AppSettings).where(AppSettings.id == 1)).scalar_one()
    return row


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/version")
def api_version():
    """Żeby w UI było widać, który dokładnie build odpowiada (bez zgadywania po plikach)."""
    from app.version_info import app_version, git_sha

    sha = git_sha()
    return {"version": app_version(), "git_sha": sha if sha else None}


@app.get("/api/universe", response_model=UniverseListResponse)
def list_universe(
    region: str | None = None,
    min_dividend_yield_pct: float | None = Query(
        None,
        ge=0,
        le=50,
        description="Pokaż tylko spółki z dywidendą ≥ tego % (wymaga danych w cache po odświeżeniu cen).",
    ),
    require_dividend_yield: bool = Query(
        False,
        description="Gdy true — pomiń spółki bez dividend_yield_pct w cache (null).",
    ),
    db: Session = Depends(get_db),
):
    q = select(UniverseStock).order_by(UniverseStock.region, UniverseStock.sector, UniverseStock.name)
    if region:
        q = q.where(UniverseStock.region == region.lower())
    stocks_db = db.execute(q).scalars().all()
    tickers = [s.ticker for s in stocks_db]
    price_map = get_price_rows(db, tickers)
    last_u = last_prices_update_global(db)
    stocks_out: list[UniverseRowOut] = []
    for s in stocks_db:
        pc = price_map.get(s.ticker)
        stocks_out.append(
            UniverseRowOut(
                id=s.id,
                ticker=s.ticker,
                name=s.name,
                region=s.region,
                sector=s.sector,
                notes=s.notes,
                price=pc.price if pc else None,
                currency=pc.currency if pc else None,
                dividend_yield_pct=pc.dividend_yield_pct if pc else None,
                dividend_yield_forward_pct=pc.dividend_yield_forward_pct if pc else None,
                change_1d_pct=pc.change_1d_pct if pc else None,
                change_1w_pct=pc.change_1w_pct if pc else None,
                change_1m_pct=pc.change_1m_pct if pc else None,
                change_1y_pct=pc.change_1y_pct if pc else None,
                change_5y_pct=pc.change_5y_pct if pc else None,
                avg_price_1d=pc.avg_price_1d if pc else None,
                avg_price_1w=pc.avg_price_1w if pc else None,
                avg_price_1m=pc.avg_price_1m if pc else None,
                avg_price_1y=pc.avg_price_1y if pc else None,
                avg_price_5y=pc.avg_price_5y if pc else None,
                updated_at=pc.updated_at if pc else None,
            )
        )
    if min_dividend_yield_pct is not None:
        stocks_out = [
            r
            for r in stocks_out
            if r.dividend_yield_pct is not None and r.dividend_yield_pct >= min_dividend_yield_pct
        ]
    elif require_dividend_yield:
        stocks_out = [r for r in stocks_out if r.dividend_yield_pct is not None]
    return UniverseListResponse(stocks=stocks_out, last_prices_update=last_u)


@app.get("/api/positions", response_model=list[PositionSummary])
def list_positions(db: Session = Depends(get_db)):
    return positions_summary(db)


@app.post("/api/lots", response_model=TradeResultOut)
def add_lot(body: PurchaseLotCreate, db: Session = Depends(get_db)):
    at = body.purchased_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if body.side == "sell":
        sale = execute_sell_fifo(
            db=db,
            ticker=body.ticker,
            quantity=float(body.quantity),
            sell_price_per_share=float(body.price_per_share),
            sold_at=at,
        )
        remaining = db.execute(
            select(PurchaseLot).where(PurchaseLot.ticker == body.ticker)
        ).scalars().all()
        _portfolio_change_safe(db, "sell")
        return TradeResultOut(
            side="sell",
            ticker=sale.ticker,
            quantity=sale.quantity,
            price_per_share=sale.price_per_share,
            currency=sale.currency,
            proceeds_pln=sale.proceeds_pln,
            cost_basis_pln=sale.cost_basis_pln,
            realized_pln=sale.realized_pln,
            remaining_shares=round(sum(float(l.quantity) for l in remaining), 6),
            sold_at=sale.sold_at,
        )

    cur = detect_trade_currency(db, body.ticker)
    lot = PurchaseLot(
        ticker=body.ticker,
        quantity=body.quantity,
        price_per_share=body.price_per_share,
        currency=cur,
        purchased_at=at,
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    _portfolio_change_safe(db, "buy")
    return TradeResultOut(
        side="buy",
        ticker=lot.ticker,
        quantity=lot.quantity,
        price_per_share=lot.price_per_share,
        currency=lot.currency,
    )


@app.get("/api/lots", response_model=list[PurchaseLotOut])
def list_lots(db: Session = Depends(get_db)):
    return db.execute(select(PurchaseLot).order_by(PurchaseLot.purchased_at.desc())).scalars().all()


@app.get("/api/lots/sales", response_model=list[SaleTransactionOut])
def list_sales(db: Session = Depends(get_db)):
    return db.execute(select(SaleTransaction).order_by(SaleTransaction.sold_at.desc())).scalars().all()


@app.delete("/api/lots/{lot_id}")
def delete_lot(lot_id: int, db: Session = Depends(get_db)):
    lot = db.get(PurchaseLot, lot_id)
    if not lot:
        raise HTTPException(404, "Lot not found")
    db.delete(lot)
    db.commit()
    _portfolio_change_safe(db, "delete_lot")
    return {"deleted": True}


@app.get("/api/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    s = get_settings_row(db)
    return SettingsOut(
        alert_threshold_percent=s.alert_threshold_percent,
        alerts_enabled=s.alerts_enabled,
        ntfy_topic=s.ntfy_topic,
        ntfy_server_url=s.ntfy_server_url,
        price_check_interval_minutes=s.price_check_interval_minutes,
        universe_price_interval_minutes=int(
            getattr(s, "universe_price_interval_minutes", None) or 120
        ),
        usd_pln_rate=float(s.usd_pln_rate) if s.usd_pln_rate is not None else 4.0,
        eur_pln_rate=float(s.eur_pln_rate) if s.eur_pln_rate is not None else 4.3,
        fx_nbp_auto=bool(getattr(s, "fx_nbp_auto", False)),
        fx_nbp_last_run_date=getattr(s, "fx_nbp_last_run_date", None),
    )


@app.post("/api/fx/refresh", response_model=FxRatesRefreshOut)
def refresh_fx_from_nbp(
    db: Session = Depends(get_db),
    enable_auto: bool = Query(True, description="Włącz automatyczne pobieranie 1× dziennie (NBP)"),
):
    s = get_settings_row(db)
    try:
        usd, eur, eff = fetch_nbp_usd_eur_pln()
    except Exception as e:
        raise HTTPException(502, f"NBP error: {e}") from e
    s.usd_pln_rate = usd
    s.eur_pln_rate = eur
    s.fx_nbp_last_run_date = nbp_scheduler_day_key()
    if enable_auto:
        s.fx_nbp_auto = True
    db.commit()
    db.refresh(s)
    _portfolio_change_safe(db, "fx_refresh")
    return FxRatesRefreshOut(
        usd_pln_rate=round(float(s.usd_pln_rate), 4),
        eur_pln_rate=round(float(s.eur_pln_rate), 4),
        source="NBP",
        effective_date=eff,
        fx_nbp_auto=bool(s.fx_nbp_auto),
        fx_nbp_last_run_date=s.fx_nbp_last_run_date,
    )


@app.patch("/api/settings", response_model=SettingsOut)
def patch_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    s = get_settings_row(db)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    if data.get("usd_pln_rate") is not None or data.get("eur_pln_rate") is not None or data.get("fx_nbp_auto") is not None:
        _portfolio_change_safe(db, "settings_fx")
    if os.getenv("SKIP_SCHEDULER") != "1" and (
        "price_check_interval_minutes" in data or "universe_price_interval_minutes" in data
    ):
        _reschedule_price_jobs(s)
    return SettingsOut(
        alert_threshold_percent=s.alert_threshold_percent,
        alerts_enabled=s.alerts_enabled,
        ntfy_topic=s.ntfy_topic,
        ntfy_server_url=s.ntfy_server_url,
        price_check_interval_minutes=s.price_check_interval_minutes,
        universe_price_interval_minutes=int(
            getattr(s, "universe_price_interval_minutes", None) or 120
        ),
        usd_pln_rate=float(s.usd_pln_rate) if s.usd_pln_rate is not None else 4.0,
        eur_pln_rate=float(s.eur_pln_rate) if s.eur_pln_rate is not None else 4.3,
        fx_nbp_auto=bool(getattr(s, "fx_nbp_auto", False)),
        fx_nbp_last_run_date=getattr(s, "fx_nbp_last_run_date", None),
    )


@app.post("/api/prices/refresh", response_model=RefreshPricesResult)
def refresh_prices(db: Session = Depends(get_db)):
    lots = db.execute(select(PurchaseLot.ticker).distinct()).scalars().all()
    universe = db.execute(select(UniverseStock.ticker)).scalars().all()
    tickers = sorted(set(lots) | set(universe))
    if not tickers:
        _snapshot_safe(db)
        return RefreshPricesResult(updated=0, failed=[])
    updated, failed = refresh_tickers(db, tickers)
    _snapshot_safe(db)
    return RefreshPricesResult(updated=updated, failed=failed)


@app.get("/api/backups/portfolio", response_model=BackupListOut)
def backups_portfolio_list():
    return BackupListOut(files=list_portfolio_backups())


@app.post("/api/backups/portfolio/create", response_model=BackupCreateOut)
def backups_portfolio_create():
    out = backup_portfolio_now(reason="manual")
    if out is None:
        return BackupCreateOut(created=False, message="Nie udalo sie utworzyc kopii portfela.")
    return BackupCreateOut(created=True, file_name=out.name, message="Utworzono kopie portfela.")


@app.post("/api/backups/portfolio/restore", response_model=BackupRestoreOut)
def backups_portfolio_restore(body: BackupRestoreIn):
    # Harmonogram trzyma SessionLocal na czas jobów — pauza zwalnia blokady na portfolio.db.
    paused = False
    if os.getenv("SKIP_SCHEDULER") != "1":
        try:
            scheduler.pause()
            paused = True
            time.sleep(1.0)
        except Exception as e:
            logger.warning("scheduler pause before portfolio restore: %s", e)
    try:
        ok, records, msg = restore_portfolio_from_backup(body.file_name)
    finally:
        if paused:
            try:
                scheduler.resume()
            except Exception as e:
                logger.warning("scheduler resume after portfolio restore: %s", e)
    if not ok:
        raise HTTPException(400, msg)
    return BackupRestoreOut(restored=True, message=msg, records=records)


@app.get("/api/backups/portfolio/export/{file_name}")
def backups_portfolio_export(file_name: str):
    try:
        path = resolve_portfolio_backup_file(file_name)
    except FileNotFoundError:
        raise HTTPException(404, "Nie znaleziono wskazanej kopii portfela.")
    return FileResponse(path, media_type="application/octet-stream", filename=path.name)


@app.post("/api/backups/portfolio/import", response_model=BackupCreateOut)
async def backups_portfolio_import(file: UploadFile = File(...)):
    name = file.filename or "portfolio-import.db"
    data = await file.read()
    ok, msg = import_portfolio_backup_file(name, data)
    if not ok:
        raise HTTPException(400, msg)
    return BackupCreateOut(created=True, file_name=msg, message="Zaimportowano kopie portfela.")


@app.get("/api/backups/prices", response_model=BackupListOut)
def backups_prices_list():
    return BackupListOut(files=list_prices_backups())


@app.post("/api/backups/prices/create", response_model=BackupCreateOut)
def backups_prices_create(db: Session = Depends(get_db)):
    out = backup_price_history_snapshot_now(db, reason="manual")
    if out is None:
        return BackupCreateOut(created=False, message="Nie udalo sie utworzyc kopii listy spolek.")
    return BackupCreateOut(created=True, file_name=out.name, message="Utworzono kopie listy spolek.")


@app.post("/api/backups/prices/restore", response_model=BackupRestoreOut)
def backups_prices_restore(body: BackupRestoreIn, db: Session = Depends(get_db)):
    ok, records, msg = restore_prices_from_snapshot(db, body.file_name)
    if not ok:
        raise HTTPException(400, msg)
    return BackupRestoreOut(restored=True, message=msg, records=records)


@app.get("/api/backups/prices/export/{file_name}")
def backups_prices_export(file_name: str):
    try:
        path = resolve_prices_backup_file(file_name)
    except FileNotFoundError:
        raise HTTPException(404, "Nie znaleziono wskazanej kopii listy spolek.")
    return FileResponse(path, media_type="application/json", filename=path.name)


@app.post("/api/backups/prices/import", response_model=BackupCreateOut)
async def backups_prices_import(file: UploadFile = File(...)):
    name = file.filename or "prices-import.json"
    data = await file.read()
    ok, msg = import_prices_backup_file(name, data)
    if not ok:
        raise HTTPException(400, msg)
    return BackupCreateOut(created=True, file_name=msg, message="Zaimportowano kopie listy spolek.")


@app.get("/api/wallet/summary", response_model=WalletSummaryOut)
def wallet_summary(db: Session = Depends(get_db)):
    d = wallet_summary_dict(db)
    return WalletSummaryOut(**d)


@app.post("/api/wallet/deposits", response_model=CashDepositOut)
def add_deposit(body: CashDepositCreate, db: Session = Depends(get_db)):
    row = CashDeposit(
        amount_pln=body.amount_pln,
        received_at=body.received_at or datetime.now(timezone.utc).replace(tzinfo=None),
        note=body.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _portfolio_change_safe(db, "add_deposit")
    return row


@app.get("/api/wallet/deposits", response_model=list[CashDepositOut])
def list_deposits(db: Session = Depends(get_db)):
    return db.execute(select(CashDeposit).order_by(CashDeposit.received_at.desc())).scalars().all()


@app.delete("/api/wallet/deposits/{dep_id}")
def delete_deposit(dep_id: int, db: Session = Depends(get_db)):
    row = db.get(CashDeposit, dep_id)
    if not row:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    _portfolio_change_safe(db, "delete_deposit")
    return {"deleted": True}


@app.post("/api/wallet/dividends", response_model=DividendReceiptOut)
def add_dividend(body: DividendReceiptCreate, db: Session = Depends(get_db)):
    row = DividendReceipt(
        ticker=body.ticker,
        amount_pln=body.amount_pln,
        received_at=body.received_at or datetime.now(timezone.utc).replace(tzinfo=None),
        note=body.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _portfolio_change_safe(db, "add_dividend")
    return row


@app.get("/api/wallet/dividends", response_model=list[DividendReceiptOut])
def list_dividends(db: Session = Depends(get_db)):
    return db.execute(select(DividendReceipt).order_by(DividendReceipt.received_at.desc())).scalars().all()


@app.delete("/api/wallet/dividends/{div_id}")
def delete_dividend(div_id: int, db: Session = Depends(get_db)):
    row = db.get(DividendReceipt, div_id)
    if not row:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    _portfolio_change_safe(db, "delete_dividend")
    return {"deleted": True}


@app.get("/api/dividends/forecast", response_model=DividendForecastResponse)
def dividends_forecast(
    horizon_days: int = Query(365, ge=30, le=800),
    db: Session = Depends(get_db),
):
    raw = dividend_forecast_payload(db, horizon_days=horizon_days)
    return DividendForecastResponse.model_validate(raw)


@app.get("/api/charts/timeline")
def chart_timeline(db: Session = Depends(get_db)):
    return timeline_payload(db)


@app.get("/api/charts/allocation")
def chart_allocation(db: Session = Depends(get_db)):
    return allocation_payload(db)


@app.post("/api/alerts/check", response_model=CheckAlertsResult)
def check_alerts(db: Session = Depends(get_db)):
    sent, skipped, notes = check_and_notify_sync(db)
    return CheckAlertsResult(sent=sent, skipped=skipped, notes=notes)


@app.api_route("/api/alerts/test-ntfy", methods=["GET", "POST"], response_model=NtfyTestResult)
@app.api_route("/api/alerts/test-ntfy/", methods=["GET", "POST"], response_model=NtfyTestResult)
def test_ntfy(db: Session = Depends(get_db)):
    """GET lub POST — wyślij na ntfy „test”. Z i bez ukośnika na końcu (inaczej POST wpada w StaticFiles → 405)."""
    ok, message = send_ntfy_test_ping(db)
    return NtfyTestResult(ok=ok, message=message)


# Opcjonalnie: serwowanie zbudowanego frontu (npm run build -> frontend/dist)
from pathlib import Path

_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")
