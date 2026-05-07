import pandas as pd

from app.services.prices import _dividend_yield_from_history, _guess_currency


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
