"""
SDM Churn — feature engineering поверх processed/features.csv.

Один источник правды для train.py и predict.py:
  - ENGINEERED_FEATURES — список добавленных колонок
  - add_engineered_features(df) — добавляет их по месту, возвращает df

Идея: базовый features.csv содержит сырые агрегаты, но самые сильные
сигналы оттока — это РАТИО и ФЛАГИ "тихого" клиента, которые модель сама
тяжелее находит на 6776 train-строках.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ENGINEERED_FEATURES: list[str] = [
    "silent_30d",                   # 1 если 0 транзакций и 0 сессий за 30д
    "is_inactive_recent",           # 1 если не заходил >= 14 дней
    "tx_per_session_30d",           # интенсивность: транзакций на сессию
    "cash_buffer_months",           # balance / salary — финансовая подушка в мес.
    "support_per_30d_session",      # тикеты на одну сессию (фрустрация)
    "unsubscribed_flag",            # 1 если хоть раз отписался
    "push_silence",                 # пуши приходили, но клиент их не открывал
    "tx_count_drop_30d_vs_avg",     # tx_30d vs средняя за 90д (нормированная)
    "outflow_per_tx_30d",           # средний чек последних 30 дней
    "no_inflow_30d",                # 1 если зарплата не пришла в последние 30 дней
]


def _safe_div(num: pd.Series, den: pd.Series, fill: float = 0.0) -> pd.Series:
    den_safe = den.replace(0, np.nan)
    return (num / den_safe).fillna(fill)


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет инженерные фичи к базовому features.csv. Идемпотентна."""
    out = df.copy()

    out["silent_30d"] = (
        (out["tx_count_30d"] == 0) & (out["sessions_30d"] == 0)
    ).astype(int)

    out["is_inactive_recent"] = (out["days_since_last_login"] >= 14).astype(int)

    out["tx_per_session_30d"] = _safe_div(out["tx_count_30d"], out["sessions_30d"])

    out["cash_buffer_months"] = _safe_div(
        out["balance_rub"].astype(float), out["salary_monthly_rub"].astype(float)
    ).clip(upper=120.0)  # обрезаем экстремальные хвосты на 10 лет

    out["support_per_30d_session"] = _safe_div(
        out["support_tickets_30d"], out["sessions_30d"]
    )

    out["unsubscribed_flag"] = (out["unsubscribe_count_90d"] > 0).astype(int)

    # пуши приходили, но открываемость почти 0 — клиент "молчит"
    out["push_silence"] = (
        (out["push_received_90d"] >= 3) & (out["push_open_rate_90d"] <= 0.1)
    ).astype(int)

    # tx за 30 дней относительно средней дневной частоты по 90д окну
    avg_30d = out["tx_count_90d"] / 3.0
    out["tx_count_drop_30d_vs_avg"] = _safe_div(
        avg_30d - out["tx_count_30d"], avg_30d.abs()
    ).clip(-1, 1)

    out["outflow_per_tx_30d"] = _safe_div(
        out["turnover_outflow_30d"], out["tx_count_30d"]
    )

    out["no_inflow_30d"] = (out["inflow_30d"] == 0).astype(int)

    return out
