"""SDM Churn — пред-расчёт скоров и офферов на старте бэкенда.

Идея: один раз при startup вызываем predict_batch на всех 8 471 активных клиентов
для каждого из 3 пресетов порога. Результат — DataFrame в памяти, который
обслуживает /clients/at-risk и /clients/{id} за миллисекунды.

SHAP в горячем пути НЕ запускается — top_factors уже посчитаны и хранятся как
JSON-сериализуемые dict.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

from backend import settings
from backend.offers import pick_offer
from model.features import add_engineered_features
from model.predict import predict_batch


def _load_raw_clients() -> pd.DataFrame:
    """Активные клиенты (не churned к snapshot) с полным профилем."""
    feats = pd.read_csv(settings.FEATURES_CSV)
    profiles = pd.read_csv(settings.CLIENTS_CSV)

    # Из clients.csv берём только профильные поля (без служебных лейблов)
    profile_cols = [
        "client_id", "first_name", "last_name", "gender", "age",
        "geography", "tenure_years", "credit_score",
    ]
    profiles = profiles[[c for c in profile_cols if c in profiles.columns]]

    df = feats.merge(profiles, on="client_id", how="left", suffixes=("", "_p"))
    # Если в features есть свои age/gender/geography — оставляем их (актуальнее)
    # Если в profile есть first_name/last_name — добавляем
    df = df[df["already_churned_at_snapshot"] == 0].reset_index(drop=True)

    df["full_name"] = (
        df.get("first_name", pd.Series([""] * len(df))).fillna("").astype(str)
        + " "
        + df.get("last_name", pd.Series([""] * len(df))).fillna("").astype(str)
    ).str.strip()
    df.loc[df["full_name"] == "", "full_name"] = "Клиент №" + df["client_id"].astype(str)

    return df


def _segment(row: pd.Series) -> str:
    bal = int(row.get("balance_rub", 0) or 0)
    n = int(row.get("n_products", 0) or 0)
    if bal >= 500_000 or n >= 3:
        return "premium"
    if bal >= 100_000 or n == 2:
        return "standard"
    return "basic"


def precompute_scores(mode: str = "balanced") -> pd.DataFrame:
    """
    Считает churn_score, top_factors, offer для всех активных клиентов.

    Возвращает DataFrame с колонками для in-memory обслуживания запросов:
        client_id, full_name, age, gender, geography, tenure_years,
        n_products, balance_rub, salary_monthly_rub, is_active_member, segment,
        churn_score, churn_probability_pct, risk_level, is_at_risk,
        top_factors (list[dict]), offer (dict|None), threshold_value
    """
    t0 = time.perf_counter()
    raw = _load_raw_clients()
    print(f"[data_loader] loaded {len(raw)} active clients in {(time.perf_counter()-t0)*1000:.0f} ms")

    # predict_batch ожидает list[dict]; даём ему ВСЕ raw-фичи (engineered посчитаются внутри)
    feature_cols = [
        c for c in raw.columns
        if c not in ("client_id", "churned_in_next_28d", "already_churned_at_snapshot",
                     "first_name", "last_name", "full_name")
    ]
    rows = raw[["client_id"] + feature_cols].to_dict(orient="records")

    t1 = time.perf_counter()
    preds = predict_batch(rows, mode=mode)
    print(f"[data_loader] predict_batch on {len(rows)} clients in {(time.perf_counter()-t1):.2f} s")

    # Собираем итоговую таблицу
    pred_df = pd.DataFrame(preds)
    raw_eng = add_engineered_features(raw)  # для движка офферов нужны engineered тоже

    cols_keep = [
        "client_id", "full_name", "age", "gender", "geography", "tenure_years",
        "n_products", "balance_rub", "salary_monthly_rub", "is_active_member",
    ]
    base = raw_eng[cols_keep].copy()
    out = base.merge(pred_df, on="client_id", how="left")

    out["segment"] = out.apply(_segment, axis=1)

    # Офферы — векторно через apply (на 8к строк ~ доли секунды)
    raw_eng_indexed = raw_eng.set_index("client_id")

    def _attach_offer(row):
        cid = row["client_id"]
        client_dict = raw_eng_indexed.loc[cid].to_dict()
        return pick_offer(client_dict, row.get("top_factors") or [])

    t2 = time.perf_counter()
    out["offer"] = out.apply(_attach_offer, axis=1)
    print(f"[data_loader] offers attached in {(time.perf_counter()-t2)*1000:.0f} ms")

    # Чистим NaN -> python None для сериализации
    out = out.where(pd.notnull(out), None)

    return out


def load_transactions(client_id: int, n_days: int = 90) -> list[dict]:
    """Лениво читаем transactions.csv и фильтруем для одного клиента (для карточки)."""
    if not settings.TRANSACTIONS_CSV.exists():
        return []
    # transactions.csv ~70 МБ — читаем колонки и фильтруем
    tx = pd.read_csv(
        settings.TRANSACTIONS_CSV,
        usecols=["client_id", "date", "amount_rub", "category"],
        dtype={"client_id": np.int64, "amount_rub": np.float64, "category": "string"},
    )
    tx = tx[tx["client_id"] == client_id]
    if tx.empty:
        return []
    tx["date"] = pd.to_datetime(tx["date"], errors="coerce")
    cutoff = tx["date"].max() - pd.Timedelta(days=n_days)
    tx = tx[tx["date"] >= cutoff].sort_values("date", ascending=False)
    return [
        {
            "date": d.strftime("%Y-%m-%d"),
            "amount_rub": float(a),
            "category": str(c),
        }
        for d, a, c in zip(tx["date"], tx["amount_rub"], tx["category"])
    ]
