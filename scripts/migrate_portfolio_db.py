"""
Copy portfolio.db into an install layout when the target is missing or empty (no lots).
Used by install-windows.ps1 so dev data is not left behind in repo/backend/data.
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def count_lots(db_path: Path) -> int:
    if not db_path.is_file():
        return 0
    try:
        con = sqlite3.connect(str(db_path))
        try:
            cur = con.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='purchase_lots'"
            )
            if cur.fetchone()[0] == 0:
                return 0
            row = con.execute("SELECT COUNT(*) FROM purchase_lots").fetchone()
            return int(row[0]) if row else 0
        finally:
            con.close()
    except sqlite3.Error:
        return -1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--install-root", type=Path, required=True, help="Folder instalacji (np. .../DividendPortfolio)")
    p.add_argument(
        "--prefer-src",
        type=Path,
        required=True,
        help="Kandydat na zrodlo (np. repo/backend/data/portfolio.db)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Nadpisz cel plikiem zrodlowym (kopie zapasowa .bak robimy zawsze gdy cel istnieje)",
    )
    args = p.parse_args()

    install_root: Path = args.install_root.resolve()
    src: Path = args.prefer_src.resolve()
    target = (install_root / "backend" / "data" / "portfolio.db").resolve()

    if src == target:
        print("migrate: zrodlo i cel to ten sam plik — pomijam.")
        return 0

    if not src.is_file():
        print(f"migrate: brak pliku zrodlowego {src}")
        return 0

    src_lots = count_lots(src)
    if src_lots < 0:
        print(f"migrate: nieczytelna baza zrodlowa {src}")
        return 1
    if src_lots == 0:
        print("migrate: zrodlo nie ma zadnych lotow — pomijam.")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    dst_lots = count_lots(target)
    if dst_lots < 0:
        print(f"migrate: cel {target} jest nieczytelny (SQLite) — nie ruszam bez --force.")
        return 1

    if target.is_file() and dst_lots > 0 and not args.force:
        print(f"migrate: cel {target} juz ma {dst_lots} lotow — nie ruszam (uzyj --force aby nadpisac).")
        return 0

    if target.is_file():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = target.with_suffix(f".db.bak-{ts}")
        shutil.copy2(target, bak)
        print(f"migrate: kopia zapasowa celu: {bak}")

    shutil.copy2(src, target)
    print(f"migrate: skopiowano {src} -> {target} (lotow w zrodle: {src_lots})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
