"""SDM Churn — predict-функция для бэкенда.

Публичный API:
    from model.predict import predict, predict_batch, MODEL_INFO

    predict(client_features) -> {
        "client_id": int | None,
        "churn_score": float,            # 0..1
        "churn_probability_pct": int,    # 0..100
        "is_at_risk": bool,              # score >= threshold (mode по умолчанию)
        "risk_level": "low" | "medium" | "high",
        "top_factors": [{"feature": str, "value": float, "impact": float, "direction": "+"|"-"}, ...],
        "threshold_mode": "balanced" | "high_precision" | "high_recall",
    }

    predict_batch(rows: list[dict]) -> list[dict]   # пакетный режим, переиспользует SHAP-explainer

Режим порога переключается параметром mode="balanced"|"high_precision"|"high_recall".
По умолчанию — "balanced".
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap

from model.features import add_engineered_features

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "model"

DEFAULT_MODE = "balanced"
RISK_LEVEL_CUTS = (0.30, 0.65)  # < 0.30 low, 0.30..0.65 medium, >=0.65 high


@lru_cache(maxsize=1)
def _load():
    model = joblib.load(MODEL_DIR / "model.pkl")
    feature_meta = json.loads((MODEL_DIR / "feature_list.json").read_text())
    threshold_meta = json.loads((MODEL_DIR / "threshold.json").read_text())
    explainer = shap.TreeExplainer(model)
    return model, feature_meta, threshold_meta, explainer


def _get_threshold(mode: str) -> float:
    _, _, thr_meta, _ = _load()
    bucket = thr_meta.get(mode)
    if bucket is None:
        # fallback на default
        bucket = thr_meta[thr_meta.get("default", "balanced")]
    return float(bucket["threshold"])


def _risk_level(score: float) -> str:
    low, high = RISK_LEVEL_CUTS
    if score < low:
        return "low"
    if score < high:
        return "medium"
    return "high"



RAW_FEATURE_DEFAULTS = {
    "age": 0, "gender": "M", "geography": "Регион",
    "tenure_years": 0, "credit_score": 600,
    "salary_monthly_rub": 0, "balance_rub": 0,
    "n_products": 1, "has_credit_card": 0, "is_active_member": 0,
    "tx_count_90d": 0, "turnover_outflow_90d": 0,
    "tx_count_30d": 0, "turnover_outflow_30d": 0, "turnover_outflow_60d_prev": 0,
    "days_since_last_tx": 999,
    "inflow_30d": 0, "inflow_60d_prev": 0,
    "sessions_30d": 0, "sessions_60d_prev": 0,
    "days_since_last_login": 999,
    "unsubscribe_count_90d": 0, "support_tickets_30d": 0,
    "push_received_90d": 0, "push_opened_90d": 0,
    "turnover_drop_30d_vs_60d_pct": 0.0,
    "sessions_drop_30d_vs_60d_pct": 0.0,
    "push_open_rate_90d": 0.0, "inflow_drop_pct": 0.0,
}


def _ensure_raw_columns(df):
    """Заполняет недостающие raw-фичи безопасными дефолтами, чтобы add_engineered_features не падал."""
    for col, default in RAW_FEATURE_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default
    return df


def _row_to_frame(client_features: dict) -> tuple[pd.DataFrame, Any]:
    """Принимает dict с базовыми фичами клиента, возвращает 1-row DataFrame
    в порядке feature_list (с инженерными фичами)."""
    _, feature_meta, _, _ = _load()
    feature_list = feature_meta["feature_list"]
    cat_features = feature_meta["cat_features"]
    client_id = client_features.get("client_id")

    df = pd.DataFrame([client_features])
    df = _ensure_raw_columns(df)
    df = add_engineered_features(df)

    # Заполняем недостающие фичи нулями (на случай если фронт прислал не всё)
    for col in feature_list:
        if col not in df.columns:
            df[col] = 0
    df = df[feature_list]

    # Категориальные — в строки
    for col in cat_features:
        df[col] = df[col].astype(str)

    return df, client_id


def _explain(X_row: pd.DataFrame, top_k: int = 3) -> list[dict]:
    _, _, _, explainer = _load()
    shap_values = explainer.shap_values(X_row)
    if isinstance(shap_values, list):  # multiclass
        shap_values = shap_values[1]
    contribs = shap_values[0]
    feats = X_row.columns.tolist()
    values = X_row.iloc[0].tolist()
    triples = sorted(
        zip(feats, values, contribs),
        key=lambda t: -abs(float(t[2])),
    )[:top_k]
    return [
        {
            "feature": f,
            "value": (float(v) if isinstance(v, (int, float, np.floating, np.integer)) else str(v)),
            "impact": float(c),
            "direction": "+" if c > 0 else "-",
        }
        for f, v, c in triples
    ]


def predict(client_features: dict, mode: str = DEFAULT_MODE) -> dict:
    """Предсказание для одного клиента."""
    model, _, _, _ = _load()
    X, client_id = _row_to_frame(client_features)

    score = float(model.predict_proba(X)[0, 1])
    threshold = _get_threshold(mode)

    return {
        "client_id": int(client_id) if client_id is not None else None,
        "churn_score": round(score, 4),
        "churn_probability_pct": int(round(score * 100)),
        "is_at_risk": bool(score >= threshold),
        "risk_level": _risk_level(score),
        "top_factors": _explain(X, top_k=3),
        "threshold_mode": mode,
        "threshold_value": round(threshold, 4),
    }


def predict_batch(rows: list[dict], mode: str = DEFAULT_MODE) -> list[dict]:
    """Пакетное предсказание — эффективнее одиночного для списков клиентов."""
    if not rows:
        return []
    model, feature_meta, _, explainer = _load()
    feature_list = feature_meta["feature_list"]
    cat_features = feature_meta["cat_features"]
    threshold = _get_threshold(mode)

    df = pd.DataFrame(rows)
    client_ids = df.get("client_id", pd.Series([None] * len(df))).tolist()
    df = _ensure_raw_columns(df)
    df = add_engineered_features(df)
    for col in feature_list:
        if col not in df.columns:
            df[col] = 0
    df = df[feature_list]
    for col in cat_features:
        df[col] = df[col].astype(str)

    proba = model.predict_proba(df)[:, 1]
    sv = explainer.shap_values(df)
    if isinstance(sv, list):
        sv = sv[1]

    out = []
    for i in range(len(df)):
        contribs = sv[i]
        triples = sorted(
            zip(feature_list, df.iloc[i].tolist(), contribs),
            key=lambda t: -abs(float(t[2])),
        )[:3]
        out.append({
            "client_id": int(client_ids[i]) if client_ids[i] is not None else None,
            "churn_score": round(float(proba[i]), 4),
            "churn_probability_pct": int(round(float(proba[i]) * 100)),
            "is_at_risk": bool(proba[i] >= threshold),
            "risk_level": _risk_level(float(proba[i])),
            "top_factors": [
                {
                    "feature": f,
                    "value": (float(v) if isinstance(v, (int, float, np.floating, np.integer)) else str(v)),
                    "impact": float(c),
                    "direction": "+" if c > 0 else "-",
                }
                for f, v, c in triples
            ],
            "threshold_mode": mode,
            "threshold_value": round(threshold, 4),
        })
    return out


def MODEL_INFO() -> dict:
    """Метаданные модели для эндпоинта /info."""
    _, feature_meta, thr_meta, _ = _load()
    return {
        "model_version": feature_meta.get("version"),
        "trained_at": feature_meta.get("trained_at"),
        "n_features": feature_meta.get("n_features"),
        "thresholds": {
            k: thr_meta.get(k) for k in ("balanced", "high_precision", "high_recall")
        },
        "default_mode": thr_meta.get("default", "balanced"),
    }


# ----------------------------------------------------------------------
# Smoke-тест
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import time

    sample_at_risk = {
        "client_id": 4242,
        "age": 34, "gender": "M", "geography": "Москва",
        "tenure_years": 2, "credit_score": 580,
        "salary_monthly_rub": 95000, "balance_rub": 12000,
        "n_products": 1, "has_credit_card": 1, "is_active_member": 0,
        "tx_count_90d": 35, "turnover_outflow_90d": 120000,
        "tx_count_30d": 4, "turnover_outflow_30d": 8000,
        "turnover_outflow_60d_prev": 90000,
        "days_since_last_tx": 18,
        "inflow_30d": 0, "inflow_60d_prev": 95000,
        "sessions_30d": 1, "sessions_60d_prev": 22,
        "days_since_last_login": 21,
        "unsubscribe_count_90d": 1, "support_tickets_30d": 2,
        "push_received_90d": 12, "push_opened_90d": 1,
        "turnover_drop_30d_vs_60d_pct": 0.91,
        "sessions_drop_30d_vs_60d_pct": 0.95,
        "push_open_rate_90d": 0.083,
        "inflow_drop_pct": 1.0,
    }

    sample_loyal = {
        "client_id": 1001,
        "age": 45, "gender": "F", "geography": "Санкт-Петербург",
        "tenure_years": 8, "credit_score": 780,
        "salary_monthly_rub": 180000, "balance_rub": 540000,
        "n_products": 3, "has_credit_card": 1, "is_active_member": 1,
        "tx_count_90d": 210, "turnover_outflow_90d": 450000,
        "tx_count_30d": 72, "turnover_outflow_30d": 155000,
        "turnover_outflow_60d_prev": 295000,
        "days_since_last_tx": 1,
        "inflow_30d": 180000, "inflow_60d_prev": 360000,
        "sessions_30d": 28, "sessions_60d_prev": 55,
        "days_since_last_login": 0,
        "unsubscribe_count_90d": 0, "support_tickets_30d": 0,
        "push_received_90d": 9, "push_opened_90d": 7,
        "turnover_drop_30d_vs_60d_pct": -0.05,
        "sessions_drop_30d_vs_60d_pct": -0.02,
        "push_open_rate_90d": 0.78,
        "inflow_drop_pct": 0.0,
    }

    print("=" * 70)
    print("predict.py smoke-test")
    print("=" * 70)

    t0 = time.perf_counter()
    r1 = predict(sample_at_risk)
    t1 = (time.perf_counter() - t0) * 1000
    print(f"\n[at-risk client] inference: {t1:.1f} ms")
    print(json.dumps(r1, indent=2, ensure_ascii=False))

    t0 = time.perf_counter()
    r2 = predict(sample_loyal)
    t2 = (time.perf_counter() - t0) * 1000
    print(f"\n[loyal client] inference: {t2:.1f} ms")
    print(json.dumps(r2, indent=2, ensure_ascii=False))

    print("\n[batch x 100] timing:")
    rows = [sample_at_risk] * 50 + [sample_loyal] * 50
    t0 = time.perf_counter()
    batch = predict_batch(rows)
    tb = (time.perf_counter() - t0) * 1000
    print(f"  total: {tb:.1f} ms  ({tb/len(rows):.2f} ms/client)")

    print("\n[MODEL_INFO]")
    print(json.dumps(MODEL_INFO(), indent=2, ensure_ascii=False))
