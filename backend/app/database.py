from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_add_column(conn, table: str, column: str, sql_type: str) -> None:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    existing = {r[1] for r in rows}
    if column not in existing:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))


def _migrate_sqlite_schema() -> None:
    if "sqlite" not in settings.database_url:
        return
    insp = inspect(engine)
    with engine.begin() as conn:
        if insp.has_table("universe_stocks"):
            _sqlite_add_column(conn, "universe_stocks", "sector", "VARCHAR(64)")
        if insp.has_table("price_cache"):
            for col, typ in [
                ("dividend_yield_pct", "FLOAT"),
                ("dividend_yield_forward_pct", "FLOAT"),
                ("change_1d_pct", "FLOAT"),
                ("change_1w_pct", "FLOAT"),
                ("change_1m_pct", "FLOAT"),
                ("change_1y_pct", "FLOAT"),
                ("change_5y_pct", "FLOAT"),
                ("avg_price_1d", "FLOAT"),
                ("avg_price_1w", "FLOAT"),
                ("avg_price_1m", "FLOAT"),
                ("avg_price_1y", "FLOAT"),
                ("avg_price_5y", "FLOAT"),
            ]:
                _sqlite_add_column(conn, "price_cache", col, typ)
        if insp.has_table("purchase_lots"):
            _sqlite_add_column(conn, "purchase_lots", "currency", "VARCHAR(8)")
        if insp.has_table("app_settings"):
            _sqlite_add_column(conn, "app_settings", "usd_pln_rate", "FLOAT DEFAULT 4.0")
            _sqlite_add_column(conn, "app_settings", "eur_pln_rate", "FLOAT DEFAULT 4.3")
            _sqlite_add_column(conn, "app_settings", "fx_nbp_auto", "BOOLEAN DEFAULT 0")
            _sqlite_add_column(conn, "app_settings", "fx_nbp_last_run_date", "VARCHAR(16)")
            _sqlite_add_column(conn, "app_settings", "universe_price_interval_minutes", "INTEGER DEFAULT 120")
            conn.execute(
                text("UPDATE app_settings SET usd_pln_rate = 4.0 WHERE usd_pln_rate IS NULL")
            )
            conn.execute(
                text("UPDATE app_settings SET eur_pln_rate = 4.3 WHERE eur_pln_rate IS NULL")
            )
            conn.execute(
                text(
                    "UPDATE app_settings SET universe_price_interval_minutes = 120 "
                    "WHERE universe_price_interval_minutes IS NULL"
                )
            )
        if insp.has_table("universe_stocks"):
            _migrate_yahoo_ticker_corrections(conn)


def _migrate_yahoo_ticker_corrections(conn) -> None:
    """Poprawki symboli Yahoo != skrót GPW (np. mBank MBK.WA, Tauron TPE.WA)."""
    renames = [("MBANK.WA", "MBK.WA"), ("TAU.WA", "TPE.WA")]
    for old, new in renames:
        conn.execute(
            text(
                "DELETE FROM universe_stocks WHERE ticker = :old "
                "AND EXISTS (SELECT 1 FROM universe_stocks u WHERE u.ticker = :new)"
            ),
            {"old": old, "new": new},
        )
        conn.execute(
            text("UPDATE universe_stocks SET ticker = :new WHERE ticker = :old"),
            {"old": old, "new": new},
        )
        conn.execute(text("DELETE FROM price_cache WHERE ticker = :old"), {"old": old})
        conn.execute(
            text(
                "DELETE FROM alert_cooldowns WHERE ticker = :old "
                "AND EXISTS (SELECT 1 FROM alert_cooldowns c WHERE c.ticker = :new)"
            ),
            {"old": old, "new": new},
        )
        conn.execute(
            text("UPDATE alert_cooldowns SET ticker = :new WHERE ticker = :old"),
            {"old": old, "new": new},
        )
        conn.execute(
            text("UPDATE purchase_lots SET ticker = :new WHERE ticker = :old"),
            {"old": old, "new": new},
        )
        conn.execute(
            text("UPDATE dividend_receipts SET ticker = :new WHERE ticker = :old"),
            {"old": old, "new": new},
        )


def init_db():
    db_path = Path(settings.database_url.replace("sqlite:///", ""))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()
