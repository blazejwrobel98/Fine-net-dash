from datetime import datetime, timedelta, timezone

from app.models import CashDeposit, PortfolioSnapshot
from app.services.charts import (
    _cumulative_deposits_at,
    _deposit_cumulative_events,
    timeline_payload,
)


def test_deposit_cumulative_excludes_dividends_logic():
    now = datetime.now(timezone.utc)
    deps = [
        CashDeposit(amount_pln=1000.0, received_at=now - timedelta(days=30)),
        CashDeposit(amount_pln=500.0, received_at=now - timedelta(days=5)),
    ]
    events = _deposit_cumulative_events(deps)
    assert events[-1][1] == 1500.0
    assert _cumulative_deposits_at(events, now - timedelta(days=10)) == 1000.0
    assert _cumulative_deposits_at(events, now) == 1500.0


def test_timeline_includes_deposits_cumulative_on_points(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        db.add(CashDeposit(amount_pln=2000.0, received_at=datetime.now(timezone.utc)))
        db.add(
            PortfolioSnapshot(
                recorded_at=datetime.now(timezone.utc),
                holdings_value_pln=5000.0,
                cash_pln=100.0,
                total_equity_pln=5100.0,
            )
        )
        db.commit()
        payload = timeline_payload(db)
        assert payload["equity_series"]
        last = payload["equity_series"][-1]
        assert last["deposits_cumulative_pln"] == 2000.0
        assert "total_equity_pln" in last
    finally:
        db.close()
