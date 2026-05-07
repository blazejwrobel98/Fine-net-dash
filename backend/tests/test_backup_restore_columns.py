"""Przywracanie portfela: różna liczba kolumn między main a kopią (np. starszy backup)."""

import sqlite3
import tempfile
from pathlib import Path

from app.services import backups as backups_mod


def test_copy_table_uses_column_intersection_not_star():
    with tempfile.TemporaryDirectory() as td:
        main_path = Path(td) / "main.db"
        src_path = Path(td) / "src.db"
        # main: 3 kolumny
        c1 = sqlite3.connect(str(main_path))
        c1.execute(
            "CREATE TABLE price_cache (id INTEGER PRIMARY KEY, ticker TEXT, price REAL, extra_col REAL DEFAULT 0)"
        )
        c1.execute("INSERT INTO price_cache (ticker, price, extra_col) VALUES ('AAA', 1.0, 99)")
        c1.commit()
        c1.close()
        # src: 2 kolumny (brak extra_col — jak stary backup)
        c2 = sqlite3.connect(str(src_path))
        c2.execute("CREATE TABLE price_cache (id INTEGER PRIMARY KEY, ticker TEXT, price REAL)")
        c2.execute("INSERT INTO price_cache (ticker, price) VALUES ('AAA', 2.5)")
        c2.commit()
        c2.close()

        conn = sqlite3.connect(str(main_path))
        conn.execute("ATTACH DATABASE ? AS srcdb", (str(src_path),))
        n = backups_mod._copy_table_from_attached(conn, "price_cache")
        conn.commit()
        row = conn.execute(
            "SELECT ticker, price, extra_col FROM price_cache WHERE ticker='AAA'"
        ).fetchone()
        conn.close()

        assert n == 1
        assert row is not None
        assert row[0] == "AAA"
        assert row[1] == 2.5
        # Kolumny tylko w main — brak w SELECT z kopii; SQLite może wstawić NULL albo DEFAULT kolumny.
        assert row[2] in (None, 0, 0.0)
