from datetime import datetime, timezone

from app.models import CashDeposit, PurchaseLot
from app.services.dividend_forecast_cache import (
    _apply_shares_to_payload,
    dividend_forecast_for_api,
    refresh_forecast_cache,
    save_forecast_cache,
)


def test_apply_shares_rescales_amounts():
    payload = {
        "holdings": [
            {
                "ticker": "PKO.WA",
                "shares": 10.0,
                "trailing_12m_pln_estimate": 100.0,
                "upcoming": [{"estimated_date": "2026-06-01", "amount_pln_estimate": 25.0}],
            }
        ],
        "total_trailing_12m_pln_estimate": 100.0,
        "total_upcoming_horizon_pln_estimate": 25.0,
    }
    out, resynced, refresh_rec = _apply_shares_to_payload(
        payload,
        current_sig={"PKO.WA": 20.0},
        cached_sig={"PKO.WA": 10.0},
    )
    assert resynced is True
    assert refresh_rec is False
    h = out["holdings"][0]
    assert h["shares"] == 20.0
    assert h["trailing_12m_pln_estimate"] == 200.0
    assert h["upcoming"][0]["amount_pln_estimate"] == 50.0
    assert out["total_trailing_12m_pln_estimate"] == 200.0


def test_forecast_api_uses_cache_without_yahoo(client, monkeypatch):
    called = {"yahoo": 0}

    def boom(*_a, **_k):
        called["yahoo"] += 1
        raise AssertionError("Yahoo should not be called when reading cache")

    monkeypatch.setattr(
        "app.services.dividend_forecast.yahoo_dividend_events",
        boom,
    )

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        db.add(
            PurchaseLot(
                ticker="PKO.WA",
                quantity=5,
                price_per_share=50,
                purchased_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        payload = {
            "holdings": [
                {
                    "ticker": "PKO.WA",
                    "shares": 5.0,
                    "currency": "PLN",
                    "trailing_12m_per_share": 2.0,
                    "trailing_12m_pln_estimate": 10.0,
                    "median_days_between_payments": 90,
                    "avg_recent_payment_per_share": 0.5,
                    "upcoming": [],
                    "note": None,
                }
            ],
            "total_trailing_12m_pln_estimate": 10.0,
            "total_upcoming_horizon_pln_estimate": 0.0,
            "horizon_days": 365,
            "disclaimer": "test",
        }
        save_forecast_cache(db, payload, horizon_days=365)
        got = dividend_forecast_for_api(db, horizon_days=365, refresh=False)
        assert got["from_cache"] is True
        assert got["holdings"][0]["ticker"] == "PKO.WA"
        assert called["yahoo"] == 0
    finally:
        db.close()

    r = client.get("/api/dividends/forecast")
    assert r.status_code == 200
    body = r.json()
    assert body["from_cache"] is True
    assert "generated_at_utc" in body
