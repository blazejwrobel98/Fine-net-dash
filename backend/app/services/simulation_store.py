"""Zapisane symulacje (pliki JSON) — historia lookback / forward bez ponownego liczenia."""

from __future__ import annotations

import json
import logging
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.services.dividend_forecast_cache import holdings_signature

logger = logging.getLogger(__name__)
_STORE_LOCK = Lock()
_STORE_DIR = BASE_DIR / "data" / "simulations"
_MAX_SAVED = 40


def _ensure_dir() -> Path:
    _STORE_DIR.mkdir(parents=True, exist_ok=True)
    return _STORE_DIR


def _label_for(kind: str, params: dict[str, Any]) -> str:
    if kind == "lookback":
        y = params.get("years_back", 1)
        ytxt = f"{int(y)}" if float(y) == int(y) else str(y)
        return f"Lookback {ytxt} lat"
    y = params.get("years_forward", 10)
    r = params.get("annual_return_pct", 7)
    d = params.get("dividend_yield_pct", 3)
    dep = float(params.get("monthly_deposit_pln") or 0)
    base = f"Projekcja {int(y) if float(y) == int(y) else y} lat · {r}% · dyw {d}%"
    if dep > 0:
        return f"{base} · wpł. {dep:.0f}/mies."
    return base


def _rescale_lookback_series(payload: dict[str, Any], ratio: float) -> dict[str, Any]:
    if ratio == 1.0:
        return payload
    out = deepcopy(payload)
    for pt in out.get("series") or []:
        if pt.get("holdings_value_pln") is not None:
            pt["holdings_value_pln"] = round(float(pt["holdings_value_pln"]) * ratio, 2)
    if out.get("virtual_cost_pln") is not None:
        out["virtual_cost_pln"] = round(float(out["virtual_cost_pln"]) * ratio, 2)
    if out.get("current_value_pln") is not None:
        # current equity from wallet — only scale holdings-derived display; keep wallet total
        pass
    return out


def _resync_lookback_payload(payload: dict[str, Any], db: Session, cached_sig: dict[str, float]) -> dict[str, Any]:
    current = holdings_signature(db)
    if not cached_sig or current == cached_sig:
        return {**payload, "shares_resynced": False}
    total_old = sum(cached_sig.values())
    total_new = sum(current.values())
    if total_old <= 0 or set(current.keys()) != set(cached_sig.keys()):
        return {
            **payload,
            "shares_resynced": False,
            "refresh_recommended": True,
            "note": (payload.get("note") or "")
            + (" Zmienił się skład portfela — wykonaj nowy lookback." if payload.get("note") else "Zmienił się skład portfela — wykonaj nowy lookback."),
        }
    ratio = total_new / total_old
    out = _rescale_lookback_series(payload, ratio)
    out["shares_resynced"] = abs(ratio - 1.0) > 1e-9
    return out


def list_saved() -> list[dict[str, Any]]:
    d = _ensure_dir()
    items: list[dict[str, Any]] = []
    for path in d.glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or "id" not in raw:
                continue
            items.append(
                {
                    "id": raw["id"],
                    "kind": raw.get("kind"),
                    "label": raw.get("label") or path.stem,
                    "created_at_utc": raw.get("created_at_utc"),
                }
            )
        except Exception as e:
            logger.warning("simulation store skip %s: %s", path.name, e)
    items.sort(key=lambda x: str(x.get("created_at_utc") or ""), reverse=True)
    return items


def get_saved(entry_id: str, db: Session | None = None) -> dict[str, Any] | None:
    path = _STORE_DIR / f"{entry_id}.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("simulation store read %s: %s", entry_id, e)
        return None
    if not isinstance(raw, dict):
        return None
    payload = raw.get("payload")
    if not isinstance(payload, dict):
        return None
    out = dict(payload)
    out["saved_id"] = raw["id"]
    out["kind"] = raw.get("kind")
    out["from_cache"] = True
    out["created_at_utc"] = raw.get("created_at_utc")
    if db is not None and raw.get("kind") == "lookback":
        from app.services.wallet import wallet_summary_dict

        summ = wallet_summary_dict(db)
        out["current_value_pln"] = round(float(summ["total_equity_pln"]), 2)
        out["actual_invested_pln"] = round(float(summ["invested_pln"]), 2)
        sig = raw.get("holdings_signature") or {}
        if isinstance(sig, dict):
            out = _resync_lookback_payload(out, db, {k: float(v) for k, v in sig.items()})
    return out


def save_simulation(
    db: Session,
    *,
    kind: Literal["lookback", "forward"],
    params: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    entry_id = uuid.uuid4().hex[:12]
    envelope: dict[str, Any] = {
        "id": entry_id,
        "kind": kind,
        "label": _label_for(kind, params),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "params": params,
        "holdings_signature": holdings_signature(db) if kind == "lookback" else None,
        "payload": payload,
    }
    with _STORE_LOCK:
        _ensure_dir()
        (_STORE_DIR / f"{entry_id}.json").write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _trim_old()
    return entry_id


def delete_saved(entry_id: str) -> bool:
    safe = "".join(c for c in entry_id if c.isalnum())
    if safe != entry_id:
        return False
    path = _STORE_DIR / f"{safe}.json"
    with _STORE_LOCK:
        if path.is_file():
            path.unlink()
            return True
    return False


def _trim_old() -> None:
    files = sorted(_STORE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[_MAX_SAVED:]:
        try:
            p.unlink()
        except OSError as e:
            logger.warning("simulation store trim %s: %s", p.name, e)


def latest_saved_id(kind: str) -> str | None:
    for item in list_saved():
        if item.get("kind") == kind:
            return str(item["id"])
    return None
