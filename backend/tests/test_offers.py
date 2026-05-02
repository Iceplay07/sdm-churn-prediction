"""Юнит-тесты движка офферов — без поднятия FastAPI."""
from backend.offers import OFFER_TEMPLATES, list_templates, pick_offer


def test_templates_well_formed():
    for tid, t in OFFER_TEMPLATES.items():
        assert t["id"] == tid
        for k in ("title", "reason_template", "estimated_lift", "cta"):
            assert k in t


def test_support_tickets_triggers_manager_call():
    o = pick_offer(
        {"support_tickets_30d": 2, "balance_rub": 12000, "n_products": 1},
        [{"feature": "support_tickets_30d", "value": 2, "impact": 1.5, "direction": "+"}],
    )
    assert o["id"] == "manager_call"
    assert "обращений" in o["reason"]


def test_unsubscribe_triggers_comm_resettings():
    o = pick_offer(
        {"unsubscribe_count_90d": 1, "n_products": 2, "balance_rub": 50000},
        [{"feature": "unsubscribe_count_90d", "value": 1, "impact": 0.8, "direction": "+"}],
    )
    assert o["id"] == "comm_resettings"


def test_inflow_drop_triggers_salary_bonus():
    o = pick_offer(
        {"inflow_drop_pct": 1.0, "inflow_60d_prev": 95000},
        [{"feature": "inflow_drop_pct", "value": 1.0, "impact": 0.7, "direction": "+"}],
    )
    assert o["id"] == "salary_bonus"


def test_inactive_login_triggers_app_reactivation():
    o = pick_offer(
        {"days_since_last_login": 25, "n_products": 1, "balance_rub": 30000},
        [{"feature": "days_since_last_login", "value": 25, "impact": 0.9, "direction": "+"}],
    )
    assert o["id"] == "app_reactivation_gift"
    assert "25" in o["reason"]


def test_negative_direction_factors_skipped_to_fallback():
    """Если все top_factors снижают риск (direction='-'), оффер — fallback."""
    o = pick_offer(
        {"n_products": 1, "balance_rub": 10000},
        [{"feature": "n_products", "value": 3, "impact": -0.5, "direction": "-"}],
    )
    assert o["id"] == "default_retention_call"


def test_premium_with_one_product_gets_cross_sell_when_no_rule_matches():
    """Если ни одно правило не сработало, но клиент премиум с 1 продуктом — кросс-продажа."""
    o = pick_offer(
        {"n_products": 1, "balance_rub": 800_000},
        [{"feature": "credit_score", "value": 750, "impact": 0.3, "direction": "+"}],
    )
    assert o["id"] == "cross_sell_savings"
    assert "800,000" in o["reason"] or "800000" in o["reason"]


def test_list_templates_count():
    assert len(list_templates()) == len(OFFER_TEMPLATES)
