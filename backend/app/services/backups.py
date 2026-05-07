import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import PriceCache

logger = logging.getLogger(__name__)

_PORTFOLIO_TABLES = [
    "app_settings",
    "universe_stocks",
    "price_cache",
    "alert_cooldowns",
    "purchase_lots",
    "sale_transactions",
    "cash_deposits",
    "dividend_receipts",
    "portfolio_snapshots",
]


def _sqlite_db_path() -> Path | None:
    url = (settings.database_url or "").strip()
    if not url.startswith("sqlite:///"):
        return None
    raw = url.replace("sqlite:///", "", 1)
    return Path(raw)


def _backup_root() -> Path | None:
    dbp = _sqlite_db_path()
    if not dbp:
        return None
    return dbp.parent / "backups"


def _portfolio_dir() -> Path | None:
    root = _backup_root()
    return None if root is None else root / "portfolio"


def _prices_dir() -> Path | None:
    root = _backup_root()
    return None if root is None else root / "prices"


def _prices_snapshot_dir() -> Path | None:
    pd = _prices_dir()
    return None if pd is None else pd / "snapshots"


def _safe_reason(v: str) -> str:
    s = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (v or "manual"))
    s = s.strip("_")
    return s or "manual"


def _safe_import_name(v: str) -> str:
    n = Path(v or "").name
    stem = Path(n).stem
    s = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in stem)
    s = s.strip("_")
    return s or "file"


def _rotate_keep_latest(folder: Path, pattern: str, keep: int) -> None:
    if keep < 1:
        keep = 1
    files = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink(missing_ok=True)
        except Exception as e:
            logger.warning("backup rotate unlink %s: %s", old, e)


def _file_meta(path: Path, kind: str) -> dict:
    st = path.stat()
    return {
        "file_name": path.name,
        "size_bytes": int(st.st_size),
        "created_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc),
        "kind": kind,
    }


def list_portfolio_backups() -> list[dict]:
    folder = _portfolio_dir()
    if folder is None or not folder.exists():
        return []
    files = sorted(folder.glob("portfolio-*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [_file_meta(p, "portfolio") for p in files]


def list_prices_backups() -> list[dict]:
    snapshot_dir = _prices_snapshot_dir()
    if snapshot_dir is None or not snapshot_dir.exists():
        return []
    files = sorted(snapshot_dir.glob("prices-snapshot-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [_file_meta(p, "prices_snapshot") for p in files]


def _resolve_backup_file(folder: Path, file_name: str) -> Path:
    path = (folder / file_name).resolve()
    if folder.resolve() not in path.parents or not path.is_file():
        raise FileNotFoundError(file_name)
    return path


def resolve_portfolio_backup_file(file_name: str) -> Path:
    folder = _portfolio_dir()
    if folder is None:
        raise FileNotFoundError(file_name)
    return _resolve_backup_file(folder, file_name)


def resolve_prices_backup_file(file_name: str) -> Path:
    folder = _prices_snapshot_dir()
    if folder is None:
        raise FileNotFoundError(file_name)
    return _resolve_backup_file(folder, file_name)


def import_portfolio_backup_file(file_name: str, content: bytes) -> tuple[bool, str]:
    folder = _portfolio_dir()
    if folder is None:
        return False, "Brak katalogu backupow portfela."
    folder.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = folder / f"portfolio-{ts}-imported-{_safe_import_name(file_name)}.db"
    try:
        out.write_bytes(content)
        con = sqlite3.connect(str(out))
        try:
            row = con.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='purchase_lots'"
            ).fetchone()
        finally:
            con.close()
        if not row or int(row[0] or 0) == 0:
            out.unlink(missing_ok=True)
            return False, "Plik nie wyglada na backup portfela SQLite (brak tabeli purchase_lots)."
        return True, out.name
    except Exception as e:
        try:
            out.unlink(missing_ok=True)
        except Exception:
            pass
        return False, f"Import backupu portfela nie powiodl sie: {e}"


def import_prices_backup_file(file_name: str, content: bytes) -> tuple[bool, str]:
    folder = _prices_snapshot_dir()
    if folder is None:
        return False, "Brak katalogu backupow listy spolek."
    folder.mkdir(parents=True, exist_ok=True)
    try:
        payload = json.loads(content.decode("utf-8"))
    except Exception as e:
        return False, f"Niepoprawny JSON backupu listy spolek: {e}"
    if not isinstance(payload, dict):
        return False, "Niepoprawny format backupu listy spolek (oczekiwany obiekt JSON)."
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = folder / f"prices-snapshot-{ts}-imported-{_safe_import_name(file_name)}.json"
    try:
        out.write_text(json.dumps(payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
        return True, out.name
    except Exception as e:
        try:
            out.unlink(missing_ok=True)
        except Exception:
            pass
        return False, f"Import backupu listy spolek nie powiodl sie: {e}"


def backup_portfolio_now(reason: str = "manual") -> Path | None:
    dbp = _sqlite_db_path()
    folder = _portfolio_dir()
    if not dbp or not dbp.is_file() or folder is None:
        return None
    keep = max(2, int(getattr(settings, "portfolio_backup_versions", 3) or 3))
    folder.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = folder / f"portfolio-{ts}-{_safe_reason(reason)}.db"

    try:
        src = sqlite3.connect(str(dbp))
        dst = sqlite3.connect(str(out))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        _rotate_keep_latest(folder, "portfolio-*.db", keep=keep)
        return out
    except Exception as e:
        logger.warning("portfolio backup failed: %s", e)
        try:
            out.unlink(missing_ok=True)
        except Exception:
            pass
        return None


def _table_exists(conn: sqlite3.Connection, db_alias: str, table: str) -> bool:
    cur = conn.execute(
        f"SELECT name FROM {db_alias}.sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None


def restore_portfolio_from_backup(file_name: str) -> tuple[bool, int, str]:
    dbp = _sqlite_db_path()
    folder = _portfolio_dir()
    if dbp is None or folder is None or not dbp.exists():
        return False, 0, "Brak lokalnej bazy SQLite do przywrocenia."
    try:
        src_path = _resolve_backup_file(folder, file_name)
    except FileNotFoundError:
        return False, 0, "Nie znaleziono wskazanej kopii portfela."

    backup_portfolio_now("before_restore")
    copied_rows = 0
    conn = sqlite3.connect(str(dbp))
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("ATTACH DATABASE ? AS srcdb", (str(src_path),))
        for table in _PORTFOLIO_TABLES:
            if not _table_exists(conn, "main", table) or not _table_exists(conn, "srcdb", table):
                continue
            conn.execute(f"DELETE FROM {table}")
            conn.execute(f"INSERT INTO {table} SELECT * FROM srcdb.{table}")
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            copied_rows += int(row[0] if row else 0)
        conn.execute("DETACH DATABASE srcdb")
        conn.commit()
        return True, copied_rows, f"Przywrocono dane portfela z kopii: {file_name}"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.warning("portfolio restore failed: %s", e)
        err = str(e)
        if "locked" in err.lower():
            return (
                False,
                0,
                "Baza SQLite jest zablokowana (zwykle serwer trzyma plik). "
                "Zatrzymaj zadanie harmonogramu „DividendPortfolio”, poczekaj kilka sekund i sprobuj ponownie — "
                "albo uzyj skryptu scripts/restore-portfolio-db-file.ps1 (przywracanie przy wylaczonym serwerze).",
            )
        return False, 0, f"Blad przy przywracaniu portfela: {e}"
    finally:
        conn.close()


def _price_row_payload(r: PriceCache) -> dict:
    return {
        "ticker": r.ticker,
        "price": r.price,
        "currency": r.currency,
        "dividend_yield_pct": r.dividend_yield_pct,
        "dividend_yield_forward_pct": getattr(r, "dividend_yield_forward_pct", None),
        "change_1d_pct": r.change_1d_pct,
        "change_1w_pct": r.change_1w_pct,
        "change_1m_pct": r.change_1m_pct,
        "change_1y_pct": r.change_1y_pct,
        "change_5y_pct": getattr(r, "change_5y_pct", None),
        "avg_price_1d": getattr(r, "avg_price_1d", None),
        "avg_price_1w": getattr(r, "avg_price_1w", None),
        "avg_price_1m": getattr(r, "avg_price_1m", None),
        "avg_price_1y": getattr(r, "avg_price_1y", None),
        "avg_price_5y": getattr(r, "avg_price_5y", None),
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def _price_snapshot_map(db: Session) -> dict[str, dict]:
    rows = db.execute(select(PriceCache).order_by(PriceCache.ticker)).scalars().all()
    return {r.ticker: _price_row_payload(r) for r in rows}


def backup_price_history_snapshot_now(db: Session, reason: str = "manual") -> Path | None:
    prices_dir = _prices_dir()
    snapshot_dir = _prices_snapshot_dir()
    if prices_dir is None or snapshot_dir is None:
        return None
    prices_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    current = _price_snapshot_map(db)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = snapshot_dir / f"prices-snapshot-{ts}-{_safe_reason(reason)}.json"
    out.write_text(json.dumps(current, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    latest = snapshot_dir / "prices-latest.json"
    latest.write_text(json.dumps(current, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    keep_days = max(30, int(getattr(settings, "price_backup_keep_days", 120) or 120))
    _rotate_keep_latest(snapshot_dir, "prices-snapshot-*.json", keep=keep_days)
    return out


def backup_price_history_incremental_daily(db: Session) -> Path | None:
    prices_dir = _prices_dir()
    snapshot_dir = _prices_snapshot_dir()
    if prices_dir is None or snapshot_dir is None:
        return None
    prices_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    delta_file = prices_dir / f"prices-delta-{day}.json"
    if delta_file.exists():
        return delta_file

    current = _price_snapshot_map(db)
    latest_snapshot = snapshot_dir / "prices-latest.json"
    previous: dict[str, dict] = {}
    if latest_snapshot.exists():
        try:
            previous = json.loads(latest_snapshot.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("price snapshot read failed: %s", e)
            previous = {}

    changed = [payload for t, payload in current.items() if previous.get(t) != payload]
    removed = [t for t in previous.keys() if t not in current]
    delta_payload = {
        "day_utc": day,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_current_tickers": len(current),
        "changed_count": len(changed),
        "removed_count": len(removed),
        "changed": changed,
        "removed": removed,
    }
    delta_file.write_text(json.dumps(delta_payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")

    dated_snapshot = snapshot_dir / f"prices-snapshot-{day}.json"
    dated_snapshot.write_text(json.dumps(current, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    latest_snapshot.write_text(json.dumps(current, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")

    keep_days = max(30, int(getattr(settings, "price_backup_keep_days", 120) or 120))
    _rotate_keep_latest(prices_dir, "prices-delta-*.json", keep=keep_days)
    _rotate_keep_latest(snapshot_dir, "prices-snapshot-*.json", keep=keep_days)
    return delta_file


def _parse_iso_naive_utc(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def restore_prices_from_snapshot(db: Session, file_name: str) -> tuple[bool, int, str]:
    folder = _prices_snapshot_dir()
    if folder is None:
        return False, 0, "Brak katalogu backupow cen."
    try:
        path = _resolve_backup_file(folder, file_name)
    except FileNotFoundError:
        return False, 0, "Nie znaleziono wskazanej kopii listy spolek."

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, 0, f"Nie da sie odczytac pliku backupu: {e}"
    if not isinstance(payload, dict):
        return False, 0, "Nieprawidlowy format backupu cen."

    tickers = [str(k) for k in payload.keys()]
    existing_rows = db.execute(select(PriceCache).where(PriceCache.ticker.in_(tickers))).scalars().all()
    existing = {r.ticker: r for r in existing_rows}
    applied = 0
    for key, row_payload in payload.items():
        if not isinstance(row_payload, dict):
            continue
        ticker = str(row_payload.get("ticker") or key).strip().upper()
        price = row_payload.get("price")
        if price is None:
            continue
        row = existing.get(ticker)
        if row is None:
            row = PriceCache(ticker=ticker, price=float(price))
            db.add(row)
            existing[ticker] = row
        row.price = float(price)
        row.currency = row_payload.get("currency")
        row.dividend_yield_pct = row_payload.get("dividend_yield_pct")
        row.dividend_yield_forward_pct = row_payload.get("dividend_yield_forward_pct")
        row.change_1d_pct = row_payload.get("change_1d_pct")
        row.change_1w_pct = row_payload.get("change_1w_pct")
        row.change_1m_pct = row_payload.get("change_1m_pct")
        row.change_1y_pct = row_payload.get("change_1y_pct")
        row.change_5y_pct = row_payload.get("change_5y_pct")
        row.avg_price_1d = row_payload.get("avg_price_1d")
        row.avg_price_1w = row_payload.get("avg_price_1w")
        row.avg_price_1m = row_payload.get("avg_price_1m")
        row.avg_price_1y = row_payload.get("avg_price_1y")
        row.avg_price_5y = row_payload.get("avg_price_5y")
        parsed_dt = _parse_iso_naive_utc(row_payload.get("updated_at"))
        if parsed_dt is not None:
            row.updated_at = parsed_dt
        applied += 1

    db.commit()
    return True, applied, f"Przywrocono dane listy spolek z kopii: {file_name}"
