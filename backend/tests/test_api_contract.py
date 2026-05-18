"""
Kontrakt API — stabilne bez sieci (mocki NBP / Yahoo / ntfy).
Uruchamiane na każdym CI; unikalne tickery, żeby nie kolidować z innymi testami.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

TICK = "CNTRKTST"
TICK2 = "CNTRKTU2"


@pytest.fixture
def mock_fx(monkeypatch: pytest.MonkeyPatch) -> None:
    """NBP — bez HTTP w teście."""

    def fake_nbp():
        return 4.05, 4.35, "2099-01-01"

    monkeypatch.setattr("app.main.fetch_nbp_usd_eur_pln", fake_nbp)


@pytest.fixture
def mock_prices_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    """Odświeżanie cen — bez Yahoo."""

    def fake_refresh(db, tickers):  # noqa: ARG001
        return len(tickers), []

    monkeypatch.setattr("app.main.refresh_tickers", fake_refresh)


@pytest.fixture
def mock_ntfy_post(monkeypatch: pytest.MonkeyPatch) -> None:
    resp = MagicMock()
    resp.is_success = True

    def fake_post(*args, **kwargs):  # noqa: ARG001
        return resp

    monkeypatch.setattr("app.services.alerts.httpx.post", fake_post)


def test_universe_region_filter(client: TestClient):
    r = client.get("/api/universe", params={"region": "us"})
    assert r.status_code == 200
    data = r.json()
    assert "stocks" in data
    for row in data["stocks"]:
        assert row["region"] == "us"


def test_universe_query_validation_min_yield_too_high(client: TestClient):
    r = client.get("/api/universe", params={"min_dividend_yield_pct": 51})
    assert r.status_code == 422


def test_settings_patch_validation_threshold_too_low(client: TestClient):
    r = client.patch("/api/settings", json={"alert_threshold_percent": 0.05})
    assert r.status_code == 422


def test_fx_refresh_contract(client: TestClient, mock_fx: None):
    r = client.post("/api/fx/refresh", params={"enable_auto": "false"})
    assert r.status_code == 200
    j = r.json()
    assert j["source"] == "NBP"
    assert j["usd_pln_rate"] == pytest.approx(4.05)
    assert j["eur_pln_rate"] == pytest.approx(4.35)


def test_prices_refresh_contract(client: TestClient, mock_prices_refresh: None):
    client.post(
        "/api/lots",
        json={"ticker": TICK, "quantity": 1.0, "price_per_share": 10.0, "side": "buy"},
    )
    r = client.post("/api/prices/refresh")
    assert r.status_code == 200
    j = r.json()
    assert "updated" in j and "failed" in j
    assert isinstance(j["failed"], list)


def test_wallet_deposits_crud(client: TestClient):
    r = client.post("/api/wallet/deposits", json={"amount_pln": 100.0, "note": "ci"})
    assert r.status_code == 200
    dep_id = r.json()["id"]
    lst = client.get("/api/wallet/deposits")
    assert lst.status_code == 200
    assert any(d["id"] == dep_id for d in lst.json())
    d = client.delete(f"/api/wallet/deposits/{dep_id}")
    assert d.status_code == 200
    assert client.delete(f"/api/wallet/deposits/{dep_id}").status_code == 404


def test_wallet_dividends_crud(client: TestClient):
    r = client.post(
        "/api/wallet/dividends",
        json={"ticker": TICK, "amount_pln": 12.34, "note": "ci-div"},
    )
    assert r.status_code == 200
    div_id = r.json()["id"]
    lst = client.get("/api/wallet/dividends")
    assert lst.status_code == 200
    assert any(x["id"] == div_id for x in lst.json())
    assert client.delete(f"/api/wallet/dividends/{div_id}").status_code == 200
    assert client.delete(f"/api/wallet/dividends/{div_id}").status_code == 404


def test_wallet_summary_shape(client: TestClient):
    r = client.get("/api/wallet/summary")
    assert r.status_code == 200
    j = r.json()
    for key in (
        "deposits_total_pln",
        "dividends_total_pln",
        "invested_pln",
        "cash_available_pln",
        "holdings_market_pln",
        "total_equity_pln",
        "sales_proceeds_total_pln",
        "realized_pnl_total_pln",
    ):
        assert key in j


def test_dividends_forecast_horizons(client: TestClient):
    r30 = client.get("/api/dividends/forecast", params={"horizon_days": 30})
    assert r30.status_code == 200
    r800 = client.get("/api/dividends/forecast", params={"horizon_days": 800})
    assert r800.status_code == 200
    bad = client.get("/api/dividends/forecast", params={"horizon_days": 20})
    assert bad.status_code == 422


def test_charts_endpoints(client: TestClient):
    t = client.get("/api/charts/timeline")
    assert t.status_code == 200
    a = client.get("/api/charts/allocation")
    assert a.status_code == 200


def test_simulations_endpoints(client: TestClient):
    lb = client.get("/api/simulations/lookback", params={"years_back": 1})
    assert lb.status_code == 200
    assert "series" in lb.json()
    fwd = client.get(
        "/api/simulations/forward",
        params={
            "years_forward": 5,
            "annual_return_pct": 7,
            "dividend_yield_pct": 3,
        },
    )
    assert fwd.status_code == 200
    assert fwd.json()["series"]


def test_backup_portfolio_list_and_create(client: TestClient):
    r = client.get("/api/backups/portfolio")
    assert r.status_code == 200
    assert "files" in r.json()
    c = client.post("/api/backups/portfolio/create")
    assert c.status_code == 200
    body = c.json()
    assert body.get("created") is True
    assert body.get("file_name")


def test_backup_portfolio_restore_unknown_file(client: TestClient):
    r = client.post(
        "/api/backups/portfolio/restore",
        json={"file_name": "portfolio-nonexistent-zzzzz.db"},
    )
    assert r.status_code == 400


def test_backup_prices_list_and_create(client: TestClient):
    r = client.get("/api/backups/prices")
    assert r.status_code == 200
    c = client.post("/api/backups/prices/create")
    assert c.status_code == 200
    assert "created" in c.json()


def test_alerts_check_when_disabled(client: TestClient):
    client.patch("/api/settings", json={"alerts_enabled": False})
    r = client.post("/api/alerts/check")
    assert r.status_code == 200
    j = r.json()
    assert j["sent"] == 0
    assert "alerts_disabled" in j["skipped"]


def test_alerts_check_with_ntfy_mocked(
    client: TestClient, mock_ntfy_post: None, monkeypatch: pytest.MonkeyPatch
):
    """Cena z mocka jest znacznie poniżej średniej kupna — warunek dokupu + wysyłka ntfy (httpx zmockowane)."""

    def fake_fetch_price(ticker: str):  # noqa: ARG001
        return 1.0, "PLN"

    monkeypatch.setattr("app.services.alerts.fetch_price", fake_fetch_price)

    client.patch(
        "/api/settings",
        json={
            "alerts_enabled": True,
            "ntfy_topic": "ci-test-topic-unique",
            "alert_threshold_percent": 50.0,
        },
    )
    client.post(
        "/api/lots",
        json={"ticker": TICK2, "quantity": 2.0, "price_per_share": 100.0, "side": "buy"},
    )
    r = client.post("/api/alerts/check")
    assert r.status_code == 200
    j = r.json()
    assert "sent" in j and "skipped" in j and "notes" in j
    assert j["sent"] >= 1


def test_ntfy_test_ping_mocked(client: TestClient, mock_ntfy_post: None):
    client.patch("/api/settings", json={"ntfy_topic": "ci-ping-topic"})
    r = client.post("/api/alerts/test-ntfy")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_fifo_sell_remaining(client: TestClient):
    t = "FIFOTEST"
    client.post("/api/lots", json={"ticker": t, "quantity": 10.0, "price_per_share": 5.0, "side": "buy"})
    r = client.post(
        "/api/lots",
        json={"ticker": t, "quantity": 3.0, "price_per_share": 6.0, "side": "sell"},
    )
    assert r.status_code == 200
    j = r.json()
    assert j["side"] == "sell"
    assert j["remaining_shares"] == pytest.approx(7.0)


def test_delete_lot_404(client: TestClient):
    assert client.delete("/api/lots/999999999").status_code == 404


def test_portfolio_backup_list_lot_counts_and_restore_roundtrip(client: TestClient):
    """Kopie zwracają purchase_lots_count; przywrócenie odtwarza pełną zawartość pliku kopii (sqlite backup)."""
    a, b = "BKRPLCNT", "BKRPLCN2"
    client.post("/api/lots", json={"ticker": a, "quantity": 1.0, "price_per_share": 10.0, "side": "buy"})
    client.post("/api/lots", json={"ticker": b, "quantity": 2.0, "price_per_share": 5.0, "side": "buy"})
    lots_before = client.get("/api/lots").json()
    n_before = len(lots_before)
    cr = client.post("/api/backups/portfolio/create")
    assert cr.status_code == 200
    fname = cr.json()["file_name"]
    assert fname

    lst = client.get("/api/backups/portfolio")
    assert lst.status_code == 200
    meta = next(f for f in lst.json()["files"] if f["file_name"] == fname)
    assert meta.get("purchase_lots_count") == n_before

    lid = lots_before[0]["id"]
    assert client.delete(f"/api/lots/{lid}").status_code == 200
    assert len(client.get("/api/lots").json()) == n_before - 1

    rr = client.post("/api/backups/portfolio/restore", json={"file_name": fname})
    assert rr.status_code == 200
    restored = client.get("/api/lots").json()
    assert len(restored) == n_before
    tickers = {x["ticker"] for x in restored}
    assert a in tickers and b in tickers


def test_static_index_when_dist_present(client: TestClient):
    """Gdy w repo jest frontend/dist, '/' serwuje SPA; w CI sam backend — opcjonalnie 404."""
    r = client.get("/")
    assert r.status_code in (200, 404)
