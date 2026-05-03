from app.seed_universe import UNIVERSE


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_universe_matches_seed(client):
    r = client.get("/api/universe")
    assert r.status_code == 200
    data = r.json()
    stocks = data["stocks"]
    assert len(stocks) == len(UNIVERSE)
    assert len(stocks) >= 50
    assert "last_prices_update" in data


def test_settings_and_threshold_slider(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert "alert_threshold_percent" in r.json()
    r2 = client.patch("/api/settings", json={"alert_threshold_percent": 3.5})
    assert r2.status_code == 200
    assert r2.json()["alert_threshold_percent"] == 3.5


def test_lot_and_positions(client):
    client.post("/api/lots", json={"ticker": "KO", "quantity": 1.5, "price_per_share": 50.0})
    r = client.get("/api/positions")
    assert r.status_code == 200
    pos = r.json()
    assert len(pos) == 1
    assert pos[0]["ticker"] == "KO"
    assert pos[0]["total_shares"] == 1.5
    assert abs(pos[0]["avg_buy_price"] - 50.0) < 1e-5


def test_list_lots(client):
    r = client.get("/api/lots")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
