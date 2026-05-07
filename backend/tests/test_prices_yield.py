import pandas as pd
import pytest

from app.services import prices
from app.services.prices import (
    _dividend_yield_from_history,
    _fetch_forward_dividend_rate_from_html,
    _fetch_forward_dividend_rate_map,
    _guess_currency,
)


def test_dividend_yield_uses_latest_calendar_year_not_rolling_12m():
    idx = pd.to_datetime(
        [
            "2025-05-08",
            "2026-04-17",
            "2026-05-01",
        ]
    )
    h = pd.DataFrame(
        {
            "Close": [50.0, 48.2, 48.19],
            "Dividends": [4.3, 3.5, 0.0],
        },
        index=idx,
    )

    # Roczny yield powinien użyć tylko 2026 (3.5), nie 4.3+3.5 z rolling 12M.
    y = _dividend_yield_from_history(h, 48.19)
    assert y == round((3.5 / 48.19) * 100.0, 3)


def test_guess_currency_for_sweden_tickers():
    assert _guess_currency("SWED-A.ST") == "SEK"


def test_guess_currency_for_germany_tickers():
    assert _guess_currency("MBG.DE") == "EUR"


def test_forward_dividend_rate_map_parses_quote_payload(monkeypatch: pytest.MonkeyPatch):
    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "quoteResponse": {
                    "result": [
                        {"symbol": "SWED-A.ST", "dividendRate": 20.45},
                        {"symbol": "MBG.DE", "dividendRate": 3.5},
                        {"symbol": "XXX", "dividendRate": None},
                    ]
                }
            }

    def fake_get(url: str, timeout: int = 20):  # noqa: ARG001
        return FakeResp()

    monkeypatch.setattr(prices._YF_SESSION, "get", fake_get)
    out = _fetch_forward_dividend_rate_map(["SWED-A.ST", "MBG.DE"])
    assert out["SWED-A.ST"] == pytest.approx(20.45)
    assert out["MBG.DE"] == pytest.approx(3.5)


def test_forward_dividend_rate_from_html_parses_raw_value(monkeypatch: pytest.MonkeyPatch):
    class FakeResp:
        status_code = 200
        text = '<html>..."dividendRate":{"raw":20.45,"fmt":"20.45"}...</html>'

        def raise_for_status(self):
            return None

    def fake_get(url: str, timeout: int = 25):  # noqa: ARG001
        return FakeResp()

    monkeypatch.setattr(prices._YF_SESSION, "get", fake_get)
    assert _fetch_forward_dividend_rate_from_html("SWED-A.ST") == pytest.approx(20.45)


def test_forward_dividend_rate_from_html_falls_back_to_trailing(monkeypatch: pytest.MonkeyPatch):
    class FakeResp:
        status_code = 200
        text = '<html>..."trailingAnnualDividendRate":{"raw":7.25,"fmt":"7.25"}...</html>'

        def raise_for_status(self):
            return None

    def fake_get(url: str, timeout: int = 25):  # noqa: ARG001
        return FakeResp()

    monkeypatch.setattr(prices._YF_SESSION, "get", fake_get)
    assert _fetch_forward_dividend_rate_from_html("KO") == pytest.approx(7.25)
