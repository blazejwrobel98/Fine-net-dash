from datetime import datetime
from zoneinfo import ZoneInfo

import requests

_NBP_BASE = "https://api.nbp.pl/api/exchangerates/rates/A"
_NBP_TZ = ZoneInfo("Europe/Warsaw")


def nbp_scheduler_day_key() -> str:
    """Dzień kalendarzowy w PL — jedna próba auto-pobrania na ten dzień."""
    return datetime.now(_NBP_TZ).date().isoformat()


def _fetch_rate(code: str) -> tuple[float, str]:
    r = requests.get(f"{_NBP_BASE}/{code}/?format=json", timeout=15)
    r.raise_for_status()
    data = r.json()
    rates = data.get("rates") or []
    if not rates:
        raise ValueError(f"NBP rate payload missing rates for {code}")
    row = rates[0]
    mid = float(row["mid"])
    effective_date = str(row["effectiveDate"])
    return mid, effective_date


def fetch_nbp_usd_eur_pln() -> tuple[float, float, str]:
    usd, d1 = _fetch_rate("USD")
    eur, d2 = _fetch_rate("EUR")
    return usd, eur, d1 if d1 == d2 else max(d1, d2)
