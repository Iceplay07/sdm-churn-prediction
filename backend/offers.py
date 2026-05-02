"""SDM Churn — движок подбора офферов удержания.

Подход: rules-based, без LLM. По топ-фактору SHAP и сегменту клиента
выбираем шаблон оффера. Детерминированно, объяснимо, легко тестируется.

API:
    pick_offer(client_row: dict, top_factors: list[dict]) -> dict | None
    list_templates() -> list[dict]
"""
from __future__ import annotations

from typing import Callable

# ---------------------------------------------------------------------------
# Шаблоны офферов
# ---------------------------------------------------------------------------
OFFER_TEMPLATES: dict[str, dict] = {
    "manager_call": {
        "id": "manager_call",
        "title": "Звонок персонального менеджера",
        "reason_template": "У клиента {tickets} обращений в поддержку за 30 дней — фрустрация",
        "estimated_lift": 0.22,
        "cta": "Запланировать звонок на завтра",
    },
    "comm_resettings": {
        "id": "comm_resettings",
        "title": "Настройка коммуникаций по интересам",
        "reason_template": "Клиент отписался от рассылок ({unsubs} раз за 90д) — раздражают уведомления",
        "estimated_lift": 0.12,
        "cta": "Отправить ссылку на настройку push/email",
    },
    "salary_bonus": {
        "id": "salary_bonus",
        "title": "+1% к вкладу за перевод зарплаты",
        "reason_template": "Зарплата перестала поступать (упала на {drop}%)",
        "estimated_lift": 0.28,
        "cta": "Push-предложение перевести зарплату",
    },
    "cashback_grocery_5pct": {
        "id": "cashback_grocery_5pct",
        "title": "Повышенный кешбэк 5% на продукты на 3 месяца",
        "reason_template": "Обороты упали на {drop}%, основная категория трат — продукты",
        "estimated_lift": 0.20,
        "cta": "Активировать кешбэк в приложении",
    },
    "app_reactivation_gift": {
        "id": "app_reactivation_gift",
        "title": "Бонус 500 ₽ за вход в приложение",
        "reason_template": "Не заходил в приложение {days} дней",
        "estimated_lift": 0.15,
        "cta": "Push: подарок на главном экране",
    },
    "engagement_drop_offer": {
        "id": "engagement_drop_offer",
        "title": "Персональная подборка в приложении",
        "reason_template": "Активность в приложении упала на {drop}%",
        "estimated_lift": 0.14,
        "cta": "Push с персональной лентой",
    },
    "cross_sell_savings": {
        "id": "cross_sell_savings",
        "title": "Накопительный счёт под 14% годовых",
        "reason_template": "Один продукт + остаток {balance:,} ₽ — потенциал кросс-продажи",
        "estimated_lift": 0.18,
        "cta": "Открыть в один клик",
    },
    "default_retention_call": {
        "id": "default_retention_call",
        "title": "Передать в отдел удержания",
        "reason_template": "Несколько слабых сигналов оттока — нужен персональный контакт",
        "estimated_lift": 0.10,
        "cta": "Поставить в очередь отдела удержания",
    },
}


# ---------------------------------------------------------------------------
# Правила: какой топ-фактор → какой оффер.
# Каждое правило — (имя_фактора, predicate(value, client_row), offer_id, format_kwargs).
# Проверяются по порядку, первое совпадение выигрывает.
# ---------------------------------------------------------------------------
def _fmt_pct(v) -> str:
    try:
        return f"{float(v) * 100:.0f}"
    except Exception:
        return "?"


RULES: list[tuple[str, Callable[[float, dict], bool], str, Callable[[float, dict], dict]]] = [
    # 1) Обращения в поддержку — самый сильный сигнал по корреляции
    (
        "support_tickets_30d",
        lambda v, c: float(v) >= 1,
        "manager_call",
        lambda v, c: {"tickets": int(v)},
    ),
    (
        "support_per_30d_session",
        lambda v, c: float(v) >= 0.5,
        "manager_call",
        lambda v, c: {"tickets": int(c.get("support_tickets_30d", 1) or 1)},
    ),
    # 2) Отписки от коммуникаций
    (
        "unsubscribe_count_90d",
        lambda v, c: float(v) >= 1,
        "comm_resettings",
        lambda v, c: {"unsubs": int(v)},
    ),
    (
        "unsubscribed_flag",
        lambda v, c: float(v) >= 1,
        "comm_resettings",
        lambda v, c: {"unsubs": int(c.get("unsubscribe_count_90d", 1) or 1)},
    ),
    # 3) Зарплата ушла в другой банк
    (
        "inflow_drop_pct",
        lambda v, c: float(v) >= 0.7,
        "salary_bonus",
        lambda v, c: {"drop": _fmt_pct(v)},
    ),
    (
        "no_inflow_30d",
        lambda v, c: float(v) >= 1 and float(c.get("inflow_60d_prev", 0) or 0) > 0,
        "salary_bonus",
        lambda v, c: {"drop": "100"},
    ),
    # 4) Падение оборотов
    (
        "turnover_drop_30d_vs_60d_pct",
        lambda v, c: float(v) >= 0.5,
        "cashback_grocery_5pct",
        lambda v, c: {"drop": _fmt_pct(v)},
    ),
    (
        "tx_count_drop_30d_vs_avg",
        lambda v, c: float(v) >= 0.5,
        "cashback_grocery_5pct",
        lambda v, c: {"drop": _fmt_pct(v)},
    ),
    # 5) Не заходит в приложение
    (
        "days_since_last_login",
        lambda v, c: int(v) >= 21,
        "app_reactivation_gift",
        lambda v, c: {"days": int(v)},
    ),
    (
        "is_inactive_recent",
        lambda v, c: float(v) >= 1,
        "app_reactivation_gift",
        lambda v, c: {"days": int(c.get("days_since_last_login", 14) or 14)},
    ),
    # 6) Сессии падают
    (
        "sessions_drop_30d_vs_60d_pct",
        lambda v, c: float(v) >= 0.5,
        "engagement_drop_offer",
        lambda v, c: {"drop": _fmt_pct(v)},
    ),
    # 7) "Тихий" клиент
    (
        "silent_30d",
        lambda v, c: float(v) >= 1,
        "engagement_drop_offer",
        lambda v, c: {"drop": "100"},
    ),
]


def _cross_sell_applicable(client_row: dict) -> bool:
    """Кросс-продажа имеет смысл только когда есть деньги и один продукт."""
    return (
        int(client_row.get("n_products", 0) or 0) <= 1
        and int(client_row.get("balance_rub", 0) or 0) >= 200_000
    )


def pick_offer(client_row: dict, top_factors: list[dict]) -> dict | None:
    """
    Выбирает оффер на основе ТОП-факторов риска и профиля клиента.

    client_row: dict со всеми полями клиента (raw + engineered).
    top_factors: вывод predict()['top_factors'] — список из 3 dict с
                 ключами feature, value, impact, direction.
    """
    if not top_factors:
        return None

    # Идём по top_factors сверху вниз, для каждого ищем правило
    for factor in top_factors:
        feat = factor.get("feature")
        impact = float(factor.get("impact", 0))
        direction = factor.get("direction", "+")
        # Интересуют только факторы, повышающие риск (direction == "+")
        if direction != "+" or impact <= 0:
            continue
        for rule_feat, predicate, offer_id, fmt_kwargs in RULES:
            if rule_feat != feat:
                continue
            try:
                val = factor.get("value")
                if val is None:
                    val = client_row.get(feat, 0)
                if predicate(val, client_row):
                    template = OFFER_TEMPLATES[offer_id]
                    kwargs = fmt_kwargs(val, client_row)
                    return {
                        "id": template["id"],
                        "title": template["title"],
                        "reason": template["reason_template"].format(**kwargs),
                        "estimated_lift": template["estimated_lift"],
                        "cta": template["cta"],
                    }
            except Exception:
                continue

    # Фоллбэк: кросс-продажа сбережений если профиль подходит
    if _cross_sell_applicable(client_row):
        t = OFFER_TEMPLATES["cross_sell_savings"]
        return {
            "id": t["id"],
            "title": t["title"],
            "reason": t["reason_template"].format(balance=int(client_row.get("balance_rub", 0) or 0)),
            "estimated_lift": t["estimated_lift"],
            "cta": t["cta"],
        }

    # Иначе — звонок отдела удержания
    t = OFFER_TEMPLATES["default_retention_call"]
    return {
        "id": t["id"],
        "title": t["title"],
        "reason": t["reason_template"],
        "estimated_lift": t["estimated_lift"],
        "cta": t["cta"],
    }


def list_templates() -> list[dict]:
    return list(OFFER_TEMPLATES.values())
