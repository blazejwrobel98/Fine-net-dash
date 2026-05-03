from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AlertCooldown, AppSettings, PurchaseLot
from app.services.portfolio import lots_by_ticker
from app.services.prices import fetch_price, get_cached_map

COOLDOWN_HOURS = 6


def _ntfy_title(s: str) -> str:
    """Nagłówki HTTP muszą być Latin-1; httpx na Windows potrafi wymusić ASCII."""
    return s.replace("\u2014", "-").replace("\u2013", "-").encode("ascii", "replace").decode("ascii")


def _avg_buy_for_ticker(db: Session, ticker: str) -> float | None:
    lots = db.execute(select(PurchaseLot).where(PurchaseLot.ticker == ticker)).scalars().all()
    if not lots:
        return None
    total_shares = sum(l.quantity for l in lots)
    if total_shares <= 0:
        return None
    total_cost = sum(l.quantity * l.price_per_share for l in lots)
    return total_cost / total_shares


def check_and_notify_sync(db: Session) -> tuple[int, list[str], list[str]]:
    """Synchroniczna wersja do schedulera (bez async). Zwraca (sent, skipped, notes)."""
    notes: list[str] = []
    settings = db.execute(select(AppSettings).where(AppSettings.id == 1)).scalar_one_or_none()
    if not settings or not settings.alerts_enabled:
        return 0, ["alerts_disabled"], ["Alerty są wyłączone — włącz je w ustawieniach."]
    topic = (settings.ntfy_topic or "").strip()
    if not topic:
        return 0, ["ntfy_topic_not_set"], ["Uzupełnij temat ntfy (Subscriptions → nazwa tematu)."]

    threshold = settings.alert_threshold_percent
    by = lots_by_ticker(db)
    tickers = list(by.keys())
    if not tickers:
        return 0, [], ["Brak zapisanych zakupów — dodaj lot w zakładce „Pozycje i zakupy”. Test „ping” ntfy jest w osobnym przycisku."]

    prices = get_cached_map(db, tickers)
    now = datetime.now(timezone.utc)
    sent = 0
    skipped: list[str] = []

    for ticker in tickers:
        avg = _avg_buy_for_ticker(db, ticker)
        if avg is None or avg <= 0:
            continue
        cached = prices.get(ticker)
        if cached:
            price = cached[0]
        else:
            price, _ = fetch_price(ticker)
            if price is None:
                skipped.append(f"{ticker}:no_price")
                continue

        trigger_price = avg * (1.0 - threshold / 100.0)
        if price > trigger_price:
            continue

        cd = db.execute(select(AlertCooldown).where(AlertCooldown.ticker == ticker)).scalar_one_or_none()
        if cd and now - cd.last_sent_at < timedelta(hours=COOLDOWN_HOURS):
            skipped.append(f"{ticker}:cooldown")
            continue

        title = _ntfy_title(f"Dokup: {ticker}")
        msg = (
            f"Cena {price:.4f} jest o {threshold:.1f}% lub więcej poniżej średniej kupna {avg:.4f}. "
            f"Różnica vs średnia: {(price / avg - 1) * 100:.2f}%."
        )
        ok = httpx.post(
            f"{settings.ntfy_server_url.rstrip('/')}/{topic}",
            content=msg.encode("utf-8"),
            headers={"Title": title, "Priority": "high"},
            timeout=15.0,
        ).is_success
        if not ok:
            skipped.append(f"{ticker}:ntfy_failed")
            continue

        if cd:
            cd.last_sent_at = now
            cd.reference_avg_price = avg
        else:
            db.add(AlertCooldown(ticker=ticker, last_sent_at=now, reference_avg_price=avg))
        sent += 1

    db.commit()
    if sent == 0 and not skipped:
        notes.append(
            f"Żadna pozycja nie spełnia warunku dokupu: cena musi być co najmniej o {threshold:g}% "
            "poniżej Twojej średniej ceny kupna. Odśwież ceny na pozycjach — bez aktualnej ceny alert też nie wyjdzie."
        )
    return sent, skipped, notes


def send_ntfy_test_ping(db: Session) -> tuple[bool, str]:
    """Jednorazowy komunikat testowy — tylko weryfikacja kanału, bez warunków na ceny."""
    settings = db.execute(select(AppSettings).where(AppSettings.id == 1)).scalar_one_or_none()
    if not settings:
        return False, "Brak ustawień w bazie."
    topic = (settings.ntfy_topic or "").strip()
    if not topic:
        return False, "Ustaw temat ntfy i zapisz."
    url = f"{settings.ntfy_server_url.rstrip('/')}/{topic}"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    title = _ntfy_title(f"Test - {ts}")
    body = (
        "To jest powiadomienie testowe z aplikacji Portfel dywidendowy.\n"
        f"Czas wysłania: {ts}"
    )
    try:
        r = httpx.post(
            url,
            content=body.encode("utf-8"),
            headers={"Title": title, "Priority": "default"},
            timeout=15.0,
        )
    except Exception as e:
        return False, f"Błąd sieci: {e}"
    if r.is_success:
        return True, "Wysłano na kanał ntfy — sprawdź telefon."
    return False, f"ntfy odrzucił żądanie (HTTP {r.status_code}). Treść: {r.text[:300]!r}"
