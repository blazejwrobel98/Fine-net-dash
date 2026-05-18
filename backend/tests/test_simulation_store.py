import json

from app.services.simulation_store import delete_saved, get_saved, list_saved, save_simulation


def test_save_list_delete_simulation(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        payload = {
            "years_forward": 5,
            "annual_return_pct": 7,
            "dividend_yield_pct": 3,
            "monthly_deposit_pln": 0,
            "start_equity_pln": 1000,
            "end_equity_pln": 1500,
            "series": [{"date": "2026-01-01", "total_equity_pln": 1000}],
            "disclaimer": "test",
        }
        sid = save_simulation(
            db,
            kind="forward",
            params={"years_forward": 5, "annual_return_pct": 7, "dividend_yield_pct": 3},
            payload=payload,
        )
        items = list_saved()
        assert any(x["id"] == sid for x in items)
        got = get_saved(sid, db)
        assert got and got.get("end_equity_pln") == 1500
        assert delete_saved(sid)
        assert get_saved(sid, db) is None
    finally:
        db.close()

    r = client.get("/api/simulations/saved")
    assert r.status_code == 200
