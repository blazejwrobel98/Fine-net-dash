import logging
import re
import time
from datetime import date, datetime, timezone
from random import uniform
from urllib.parse import quote

import pandas as pd
import requests
import yfinance as yf
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import PriceCache

logger = logging.getLogger(__name__)

# Ciszej w konsoli — yfinance loguje każdy chybiony ticker na INFO
for _log_name in ("yfinance", "yfinance.base", "yfinance.scrapers", "peewee"):
    logging.getLogger(_log_name).setLevel(logging.ERROR)


def _yf_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return s


_YF_SESSION = _yf_session()
_DIVIDEND_RATE_RE = re.compile(
    r'(?:\\"|")dividendRate(?:\\"|")\s*:\s*(?:\\"|")?\{(?:\\"|")raw(?:\\"|")\s*:\s*([0-9]+(?:\.[0-9]+)?)'
)
_TRAILING_DIVIDEND_RATE_RE = re.compile(
    r'(?:\\"|")trailingAnnualDividendRate(?:\\"|")\s*:\s*(?:\\"|")?\{(?:\\"|")raw(?:\\"|")\s*:\s*([0-9]+(?:\.[0-9]+)?)'
)


def _yahoo_chart_range(period: str) -> str:
    """Mapowanie okresu history() na parametr range wykresu Yahoo (v8)."""
    p = (period or "1y").lower().strip()
    if p in ("1d", "5d", "7d"):
        return "5d"
    if p in ("1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"):
        return p
    return "1y"


def _load_history_yahoo_chart(ticker: str, period: str, *, actions: bool) -> pd.DataFrame:
    """
    Bezpośrednie Yahoo chart v8 — stabilniejsze niż scraper yfinance (często pusty JSON / 429).
    """
    rng = _yahoo_chart_range(period)
    sym = quote(ticker, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval=1d"
    if actions:
        url += "&events=div"
    try:
        r = _YF_SESSION.get(url, timeout=35)
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        logger.debug("yahoo chart %s %s: %s", ticker, rng, e)
        return pd.DataFrame()

    chart = payload.get("chart") or {}
    if chart.get("error"):
        logger.debug("yahoo chart error %s: %s", ticker, chart.get("error"))
        return pd.DataFrame()
    results = chart.get("result") or []
    if not results:
        return pd.DataFrame()
    res = results[0]
    timestamps = res.get("timestamp") or []
    if not timestamps:
        return pd.DataFrame()
    quotes = (res.get("indicators") or {}).get("quote") or [{}]
    closes = (quotes[0] or {}).get("close") or []
    if len(closes) != len(timestamps):
        return pd.DataFrame()

    idx = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None)
    df = pd.DataFrame({"Close": closes}, index=idx)
    df = df[df["Close"].notna()].copy()
    if df.empty:
        return df

    if actions:
        divs: dict[str, float] = {}
        events = res.get("events") or {}
        raw_div = events.get("dividends") or {}
        for unix, info in raw_div.items():
            try:
                amt = float((info or {}).get("amount", 0) or 0)
            except (TypeError, ValueError):
                amt = 0.0
            if amt <= 0:
                continue
            d = pd.to_datetime(int(unix), unit="s", utc=True).tz_convert(None).date()
            divs[str(d)] = divs.get(str(d), 0.0) + amt
        df["Dividends"] = [divs.get(str(ts.date()), 0.0) for ts in df.index]
    return df


def _fetch_forward_dividend_rate_map(tickers: list[str]) -> dict[str, float]:
    """
    Forward annual dividend amount per share z Yahoo quote (batch),
    np. 20.45 dla SWED-A.ST.
    """
    out: dict[str, float] = {}
    if not tickers:
        return out
    unique = sorted(set(t.upper() for t in tickers if t))
    chunk_size = 40
    for i in range(0, len(unique), chunk_size):
        chunk = unique[i : i + chunk_size]
        sym = ",".join(quote(t, safe="") for t in chunk)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={sym}"
        payload = None
        for attempt in range(2):
            try:
                r = _YF_SESSION.get(url, timeout=20)
                if r.status_code == 429:
                    raise requests.HTTPError("429")
                r.raise_for_status()
                payload = r.json()
                break
            except Exception as e:
                logger.debug("yahoo quote forward div batch %s attempt %s: %s", i // chunk_size, attempt, e)
                if attempt == 0:
                    time.sleep(1.2 + uniform(0.1, 0.6))
        if not payload:
            continue
        rows = (payload.get("quoteResponse") or {}).get("result") or []
        for row in rows:
            t = str(row.get("symbol") or "").upper().strip()
            if not t:
                continue
            try:
                rate = float(row.get("dividendRate"))
            except (TypeError, ValueError):
                rate = 0.0
            if rate <= 0:
                try:
                    rate = float(row.get("trailingAnnualDividendRate"))
                except (TypeError, ValueError):
                    rate = 0.0
            if rate > 0:
                out[t] = rate
    return out


def _fetch_forward_dividend_rate_from_html(ticker: str) -> float | None:
    """
    Fallback, gdy Yahoo quote API zwróci pusto/429:
    parsujemy `dividendRate.raw` ze strony quote HTML.
    """
    sym = quote((ticker or "").upper().strip(), safe="")
    if not sym:
        return None
    url = f"https://finance.yahoo.com/quote/{sym}"
    try:
        r = _YF_SESSION.get(url, timeout=25)
        r.raise_for_status()
        text = r.text or ""
        m = _DIVIDEND_RATE_RE.search(text)
        if not m:
            m = _TRAILING_DIVIDEND_RATE_RE.search(text)
        if not m:
            return None
        val = float(m.group(1))
        return val if val > 0 else None
    except Exception as e:
        logger.debug("yahoo html forward div %s: %s", ticker, e)
        return None


def yahoo_dividend_events(ticker: str, range_key: str = "2y") -> list[tuple[date, float]]:
    """
    Zdarzenia dywidend z Yahoo chart (events=div), posortowane rosnąco po dacie.
    Kwoty w walucie wypłaty (typowo jak notowanie).
    """
    rng = _yahoo_chart_range(range_key)
    sym = quote(ticker, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval=1d&events=div"
    try:
        r = _YF_SESSION.get(url, timeout=35)
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        logger.debug("yahoo div events %s: %s", ticker, e)
        return []

    chart = payload.get("chart") or {}
    if chart.get("error"):
        return []
    results = chart.get("result") or []
    if not results:
        return []
    res = results[0]
    events = res.get("events") or {}
    raw_div = events.get("dividends") or {}
    by_day: dict[date, float] = {}
    for unix, info in raw_div.items():
        try:
            amt = float((info or {}).get("amount", 0) or 0)
        except (TypeError, ValueError):
            amt = 0.0
        if amt <= 0:
            continue
        d = pd.to_datetime(int(unix), unit="s", utc=True).tz_convert(None).date()
        by_day[d] = by_day.get(d, 0.0) + amt
    return sorted(by_day.items(), key=lambda x: x[0])


def _guess_currency(ticker: str) -> str | None:
    u = ticker.upper()
    if u.endswith(".WA") or u.endswith(".WAR"):
        return "PLN"
    if u.endswith(".ST"):
        return "SEK"
    if u.endswith(".DE") or u.endswith(".F"):
        return "EUR"
    if u.endswith(".PA") or u.endswith(".AS") or u.endswith(".MI") or u.endswith(".MC"):
        return "EUR"
    if u.endswith(".SW"):
        return "CHF"
    if u.endswith(".L") or u.endswith(".IL"):
        return "GBp"
    if u.endswith(".LS") or u.endswith(".LIS"):
        return "EUR"
    if u.endswith(".CO"):
        return "DKK"
    if "." in u:
        return "EUR"
    return "USD"

def _load_history(ticker: str, period: str, *, actions: bool) -> pd.DataFrame:
    """Najpierw oficjalne API wykresu Yahoo; potem yfinance jako zapas."""
    for attempt in range(3):
        h = _load_history_yahoo_chart(ticker, period, actions=actions)
        if h is not None and not h.empty and "Close" in h.columns:
            return h
        try:
            h2 = yf.Ticker(ticker, session=_YF_SESSION).history(
                period=period,
                interval="1d",
                auto_adjust=True,
                actions=actions,
            )
            if h2 is not None and not h2.empty and "Close" in h2.columns:
                return h2
        except Exception as e:
            logger.debug("yfinance history %s (%s) attempt %s: %s", ticker, period, attempt, e)
        if attempt < 2:
            time.sleep(2.0 * (attempt + 1) + uniform(0.3, 1.2))
    return pd.DataFrame()


def fetch_price(ticker: str) -> tuple[float | None, str | None]:
    h = _load_history(ticker, "7d", actions=False)
    if h.empty:
        return None, None
    try:
        last = float(h["Close"].iloc[-1])
        return last, _guess_currency(ticker)
    except Exception:
        return None, None


def _dividend_yield_from_history(h: pd.DataFrame, price: float) -> float | None:
    if price <= 0 or h is None or h.empty:
        return None
    if "Dividends" not in h.columns:
        return None
    div = h["Dividends"].fillna(0)
    if div.empty:
        return None
    positive = div[div > 0]
    if positive.empty:
        return None
    # Roczna (kalendarzowa), nie trailing 12M:
    # suma wypłat z ostatniego roku, w którym wystąpiła dywidenda.
    latest_year = int(positive.index.max().year)
    total_year = float(positive[positive.index.year == latest_year].sum())
    if total_year <= 0:
        return None
    return round((total_year / price) * 100.0, 3)


def _avg_close(closes: pd.Series, window: int) -> float | None:
    if closes is None or closes.empty:
        return None
    if len(closes) < window:
        return None
    return round(float(closes.tail(window).mean()), 4)


def fetch_extended_metrics(ticker: str) -> dict:
    """
    Jedno pobranie history(1y) na ticker (z ewentualnymi ponowieniami).
    Bez t.info — mniej limitów Yahoo.
    """
    out: dict = {
        "price": None,
        "currency": None,
        "dividend_yield_pct": None,
        "dividend_yield_forward_pct": None,
        "change_1d_pct": None,
        "change_1w_pct": None,
        "change_1m_pct": None,
        "change_1y_pct": None,
        "change_5y_pct": None,
        "avg_price_1d": None,
        "avg_price_1w": None,
        "avg_price_1m": None,
        "avg_price_1y": None,
        "avg_price_5y": None,
    }
    h = _load_history(ticker, "5y", actions=True)
    if h.empty or "Close" not in h.columns:
        return out
    try:
        cl = h["Close"].dropna()
        if len(cl) < 1:
            return out
        price = float(cl.iloc[-1])
        out["price"] = price
        out["currency"] = _guess_currency(ticker)
        out["dividend_yield_pct"] = _dividend_yield_from_history(h, price)

        if len(cl) >= 2:
            out["change_1d_pct"] = round((float(cl.iloc[-1]) / float(cl.iloc[-2]) - 1.0) * 100.0, 2)
        if len(cl) >= 6:
            out["change_1w_pct"] = round((float(cl.iloc[-1]) / float(cl.iloc[-6]) - 1.0) * 100.0, 2)
        if len(cl) >= 22:
            out["change_1m_pct"] = round((float(cl.iloc[-1]) / float(cl.iloc[-22]) - 1.0) * 100.0, 2)
        if len(cl) >= 252:
            out["change_1y_pct"] = round((float(cl.iloc[-1]) / float(cl.iloc[-252]) - 1.0) * 100.0, 2)
        if len(cl) >= 1260:
            out["change_5y_pct"] = round((float(cl.iloc[-1]) / float(cl.iloc[-1260]) - 1.0) * 100.0, 2)

        out["avg_price_1d"] = _avg_close(cl, 2)
        out["avg_price_1w"] = _avg_close(cl, 6)
        out["avg_price_1m"] = _avg_close(cl, 22)
        out["avg_price_1y"] = _avg_close(cl, 252)
        out["avg_price_5y"] = _avg_close(cl, 1260)
    except Exception as e:
        logger.debug("fetch_extended_metrics %s: %s", ticker, e)
    return out


def refresh_tickers(db: Session, tickers: list[str]) -> tuple[int, list[str]]:
    failed: list[str] = []
    updated = 0
    delay = max(0.0, float(settings.yahoo_request_delay_seconds))
    forward_div_rate = _fetch_forward_dividend_rate_map(tickers)
    for i, ticker in enumerate(tickers):
        if i > 0 and delay > 0:
            time.sleep(delay + uniform(0, 0.2))
        m = fetch_extended_metrics(ticker)
        if m["price"] is None:
            failed.append(ticker)
            continue
        fd = forward_div_rate.get(ticker.upper())
        if not fd:
            fd = _fetch_forward_dividend_rate_from_html(ticker)
        if fd and m["price"] and m["price"] > 0:
            m["dividend_yield_forward_pct"] = round((float(fd) / float(m["price"])) * 100.0, 3)
        else:
            m["dividend_yield_forward_pct"] = None
        row = db.execute(select(PriceCache).where(PriceCache.ticker == ticker)).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if row:
            row.price = m["price"]
            row.currency = m["currency"]
            row.updated_at = now
            row.dividend_yield_pct = m["dividend_yield_pct"]
            row.dividend_yield_forward_pct = m["dividend_yield_forward_pct"]
            row.change_1d_pct = m["change_1d_pct"]
            row.change_1w_pct = m["change_1w_pct"]
            row.change_1m_pct = m["change_1m_pct"]
            row.change_1y_pct = m["change_1y_pct"]
            row.change_5y_pct = m["change_5y_pct"]
            row.avg_price_1d = m["avg_price_1d"]
            row.avg_price_1w = m["avg_price_1w"]
            row.avg_price_1m = m["avg_price_1m"]
            row.avg_price_1y = m["avg_price_1y"]
            row.avg_price_5y = m["avg_price_5y"]
        else:
            db.add(
                PriceCache(
                    ticker=ticker,
                    price=m["price"],
                    currency=m["currency"],
                    updated_at=now,
                    dividend_yield_pct=m["dividend_yield_pct"],
                    dividend_yield_forward_pct=m["dividend_yield_forward_pct"],
                    change_1d_pct=m["change_1d_pct"],
                    change_1w_pct=m["change_1w_pct"],
                    change_1m_pct=m["change_1m_pct"],
                    change_1y_pct=m["change_1y_pct"],
                    change_5y_pct=m["change_5y_pct"],
                    avg_price_1d=m["avg_price_1d"],
                    avg_price_1w=m["avg_price_1w"],
                    avg_price_1m=m["avg_price_1m"],
                    avg_price_1y=m["avg_price_1y"],
                    avg_price_5y=m["avg_price_5y"],
                )
            )
        updated += 1
    db.commit()
    return updated, failed


def get_cached_map(db: Session, tickers: list[str]) -> dict[str, tuple[float, str | None]]:
    if not tickers:
        return {}
    rows = db.execute(select(PriceCache).where(PriceCache.ticker.in_(tickers))).scalars().all()
    return {r.ticker: (r.price, r.currency) for r in rows}


def last_prices_update_global(db: Session) -> datetime | None:
    r = db.execute(select(func.max(PriceCache.updated_at))).scalar_one_or_none()
    return r


def get_price_rows(db: Session, tickers: list[str]) -> dict[str, PriceCache]:
    if not tickers:
        return {}
    rows = db.execute(select(PriceCache).where(PriceCache.ticker.in_(tickers))).scalars().all()
    return {r.ticker: r for r in rows}
