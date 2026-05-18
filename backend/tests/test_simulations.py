from datetime import date, timedelta

import pandas as pd

from app.services.simulations import forward_simulation_payload, lookback_simulation_payload


def test_forward_simulation_grows_with_positive_return(client):
    from app.database import SessionLocal
    from app.models import PurchaseLot
    from datetime import datetime, timezone

    db = SessionLocal()
    try:
        db.add(
            PurchaseLot(
                ticker="SIMTEST.WA",
                quantity=1,
                price_per_share=100,
                purchased_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        out = forward_simulation_payload(
            db,
            years_forward=1.0,
            annual_return_pct=12.0,
            dividend_yield_pct=0,
            monthly_deposit_pln=500.0,
        )
        assert out["end_equity_pln"] > out["start_equity_pln"] + 5000
        assert len(out["series"]) >= 12
    finally:
        db.close()


def test_lookback_with_mock_history(client, monkeypatch):
    from app.database import SessionLocal
    from app.models import PurchaseLot
    from datetime import datetime, timezone

    today = date.today()
    idx = pd.date_range(end=today, periods=400, freq="D")
    closes = [100.0 + i * 0.1 for i in range(len(idx))]
    df = pd.DataFrame({"Close": closes}, index=idx)

    monkeypatch.setattr("app.services.simulations._load_history", lambda _t, _p, actions=False: df)

    db = SessionLocal()
    try:
        db.add(
            PurchaseLot(
                ticker="LBTEST.WA",
                quantity=10,
                price_per_share=50,
                purchased_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        out = lookback_simulation_payload(db, years_back=1.0)
        assert out["series"]
        assert out["virtual_cost_pln"] > 0
        assert out["series"][-1]["holdings_value_pln"] > out["virtual_cost_pln"]
    finally:
        db.close()
