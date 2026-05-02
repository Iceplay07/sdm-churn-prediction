"""Smoke-тесты эндпоинтов SDM Churn API."""

AT_RISK_SAMPLE = {
    "client_id": 99001, "age": 34, "gender": "M", "geography": "Москва",
    "tenure_years": 2, "credit_score": 580, "salary_monthly_rub": 95000, "balance_rub": 12000,
    "n_products": 1, "has_credit_card": 1, "is_active_member": 0,
    "tx_count_90d": 35, "turnover_outflow_90d": 120000, "tx_count_30d": 4,
    "turnover_outflow_30d": 8000, "turnover_outflow_60d_prev": 90000, "days_since_last_tx": 18,
    "inflow_30d": 0, "inflow_60d_prev": 95000, "sessions_30d": 1, "sessions_60d_prev": 22,
    "days_since_last_login": 21, "unsubscribe_count_90d": 1, "support_tickets_30d": 2,
    "push_received_90d": 12, "push_opened_90d": 1, "turnover_drop_30d_vs_60d_pct": 0.91,
    "sessions_drop_30d_vs_60d_pct": 0.95, "push_open_rate_90d": 0.083, "inflow_drop_pct": 1.0,
}

LOYAL_SAMPLE = {
    "client_id": 99002, "age": 45, "gender": "F", "geography": "Санкт-Петербург",
    "tenure_years": 8, "credit_score": 780, "salary_monthly_rub": 180000, "balance_rub": 540000,
    "n_products": 3, "has_credit_card": 1, "is_active_member": 1,
    "tx_count_90d": 210, "turnover_outflow_90d": 450000, "tx_count_30d": 72,
    "turnover_outflow_30d": 155000, "turnover_outflow_60d_prev": 295000, "days_since_last_tx": 1,
    "inflow_30d": 180000, "inflow_60d_prev": 360000, "sessions_30d": 28, "sessions_60d_prev": 55,
    "days_since_last_login": 0, "unsubscribe_count_90d": 0, "support_tickets_30d": 0,
    "push_received_90d": 9, "push_opened_90d": 7, "turnover_drop_30d_vs_60d_pct": -0.05,
    "sessions_drop_30d_vs_60d_pct": -0.02, "push_open_rate_90d": 0.78, "inflow_drop_pct": 0.0,
}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["clients_loaded"] > 0


def test_info_has_three_thresholds(client):
    r = client.get("/info")
    assert r.status_code == 200
    info = r.json()
    assert info["default_mode"] in ("balanced", "high_precision", "high_recall")
    for mode in ("balanced", "high_precision", "high_recall"):
        assert mode in info["thresholds"], f"missing {mode} preset"


def test_predict_at_risk_high_score(client):
    r = client.post("/predict", json=AT_RISK_SAMPLE)
    assert r.status_code == 200
    body = r.json()
    assert body["churn_score"] > 0.7, body
    assert body["is_at_risk"] is True
    assert body["risk_level"] == "high"
    assert len(body["top_factors"]) == 3


def test_predict_loyal_low_score(client):
    r = client.post("/predict", json=LOYAL_SAMPLE)
    assert r.status_code == 200
    body = r.json()
    assert body["churn_score"] < 0.3, body
    assert body["is_at_risk"] is False
    assert body["risk_level"] == "low"


def test_predict_batch_keeps_order(client):
    r = client.post("/predict/batch", json={"rows": [AT_RISK_SAMPLE, LOYAL_SAMPLE, AT_RISK_SAMPLE]})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 3
    assert items[0]["client_id"] == 99001
    assert items[1]["client_id"] == 99002
    assert items[2]["client_id"] == 99001
    # Скоры в правильных пропорциях
    assert items[0]["churn_score"] > items[1]["churn_score"]


def test_predict_mode_changes_threshold(client):
    """В режиме high_recall is_at_risk должен срабатывать чаще (порог ниже)."""
    border_sample = {**AT_RISK_SAMPLE, "support_tickets_30d": 0, "unsubscribe_count_90d": 0,
                     "days_since_last_login": 10}
    r1 = client.post("/predict?mode=balanced", json=border_sample).json()
    r2 = client.post("/predict?mode=high_recall", json=border_sample).json()
    # Скор тот же, порог разный
    assert abs(r1["churn_score"] - r2["churn_score"]) < 1e-6
    assert r1["threshold_value"] >= r2["threshold_value"]


def test_at_risk_default_sorted_desc(client):
    r = client.get("/clients/at-risk?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    scores = [it["churn_score"] for it in body["items"]]
    assert scores == sorted(scores, reverse=True), "items must be sorted by score desc"


def test_at_risk_pagination(client):
    p1 = client.get("/clients/at-risk?limit=5&offset=0").json()
    p2 = client.get("/clients/at-risk?limit=5&offset=5").json()
    ids1 = [it["client_id"] for it in p1["items"]]
    ids2 = [it["client_id"] for it in p2["items"]]
    assert len(ids1) == 5 and len(ids2) == 5
    assert set(ids1).isdisjoint(set(ids2)), "pages must not overlap"


def test_at_risk_geography_filter(client):
    full = client.get("/clients/at-risk?limit=500").json()["total"]
    msk = client.get("/clients/at-risk?geography=Москва&limit=500").json()["total"]
    assert 0 < msk < full


def test_at_risk_min_score_filter(client):
    full = client.get("/clients/at-risk?limit=500").json()["total"]
    high = client.get("/clients/at-risk?min_score=0.95&limit=500").json()["total"]
    assert 0 < high < full


def test_every_at_risk_has_offer(client):
    body = client.get("/clients/at-risk?limit=50").json()
    assert body["returned"] > 0
    for item in body["items"]:
        assert item["offer"] is not None, f"client {item['client_id']} has no offer"
        assert item["offer"]["id"]
        assert item["offer"]["title"]
        assert item["offer"]["cta"]


def test_client_card_from_at_risk_list(client):
    cid = client.get("/clients/at-risk?limit=1").json()["items"][0]["client_id"]
    r = client.get(f"/clients/{cid}")
    assert r.status_code == 200
    body = r.json()
    assert body["client_id"] == cid
    assert body["full_name"]
    assert body["offer"] is not None


def test_client_card_404(client):
    r = client.get("/clients/99999999")
    assert r.status_code == 404


def test_offers_templates_endpoint(client):
    r = client.get("/offers/templates")
    assert r.status_code == 200
    templates = r.json()["templates"]
    assert len(templates) >= 8
    ids = {t["id"] for t in templates}
    assert "manager_call" in ids
    assert "default_retention_call" in ids


def test_batch_size_limit(client):
    """Превышение MAX_BATCH_SIZE должно вернуть 413."""
    huge = {"rows": [LOYAL_SAMPLE] * 1001}
    r = client.post("/predict/batch", json=huge)
    assert r.status_code == 413
