"""
SDM Churn — обучение модели предсказания оттока (Этап 2 хакатона)

Запуск: python -m train

Артефакты в model/artifacts/:
  - model.pkl, feature_list.json, threshold.json, metrics.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.metrics import average_precision_score, classification_report, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from .src.config import (
    ARTIFACTS_DIR, CAT_FEATURES, CV_SPLITS, DROP_COLS,
    MODEL_PARAMS, RANDOM_STATE, TARGET, TARGET_PRECISION, TARGET_RECALL,
)
from .src.data import load_training_data, split_data
from .src.features import ENGINEERED_FEATURES
from .src.metrics import calculate_metrics, print_metrics
from .src.model_factory import create_model
from .src.thresholds import pick_thresholds


def cross_validate(X, y) -> dict:
    skf = StratifiedKFold(n_splits=CV_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    roc_scores, pr_scores = [], []

    print(f"\n[cv] {CV_SPLITS}-fold stratified cross-validation...")
    for fold, (tr, va) in enumerate(skf.split(X, y), 1):
        model, _ = create_model(y.iloc[tr])
        model.fit(X.iloc[tr], y.iloc[tr], eval_set=(X.iloc[va], y.iloc[va]))
        proba = model.predict_proba(X.iloc[va])[:, 1]
        roc = roc_auc_score(y.iloc[va], proba)
        pr = average_precision_score(y.iloc[va], proba)
        roc_scores.append(roc)
        pr_scores.append(pr)
        print(f"  fold {fold}/{CV_SPLITS}  ROC-AUC={roc:.4f}  PR-AUC={pr:.4f}")

    cv = {
        "roc_auc_mean": float(np.mean(roc_scores)), "roc_auc_std": float(np.std(roc_scores)),
        "pr_auc_mean":  float(np.mean(pr_scores)),  "pr_auc_std":  float(np.std(pr_scores)),
    }
    print(f"[cv] ROC-AUC = {cv['roc_auc_mean']:.4f} ± {cv['roc_auc_std']:.4f}")
    print(f"[cv] PR-AUC  = {cv['pr_auc_mean']:.4f} ± {cv['pr_auc_std']:.4f}")
    return cv


def main():
    print("=" * 70)
    print("SDM Churn Prediction — Stage 2 Training")
    print("=" * 70)

    X, y, data_info = load_training_data()
    print("\n[data]", data_info)

    X_tr, X_te, y_tr, y_te = split_data(X, y)
    model, spw = create_model(y_tr)
    print(f"\n[split] train={len(X_tr)}  test={len(X_te)}  scale_pos_weight={spw:.2f}")

    cv = cross_validate(X, y)

    print("\n[fit] training final model...")
    model.fit(X_tr, y_tr, eval_set=(X_te, y_te))
    best_iter = model.get_best_iteration()
    print(f"[fit] best_iteration = {best_iter}")

    proba = model.predict_proba(X_te)[:, 1]
    roc = float(roc_auc_score(y_te, proba))
    pr = float(average_precision_score(y_te, proba))
    print(f"\n[test] ROC-AUC={roc:.4f}  PR-AUC={pr:.4f}")
    print(classification_report(y_te, (proba >= 0.5).astype(int), digits=3))

    thresholds = pick_thresholds(y_te.to_numpy(), proba)
    test_metrics = calculate_metrics(y_te.to_numpy(), proba, thresholds["balanced"]["threshold"])
    print_metrics(test_metrics)

    # --- save ---
    print("\n[save] writing artifacts...")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, ARTIFACTS_DIR / "model.pkl")

    (ARTIFACTS_DIR / "feature_list.json").write_text(json.dumps({
        "version": "1.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_list": list(X.columns),
        "engineered_features": ENGINEERED_FEATURES,
        "cat_features": CAT_FEATURES,
        "drop_cols": DROP_COLS,
        "target": TARGET,
    }, indent=2, ensure_ascii=False))

    (ARTIFACTS_DIR / "threshold.json").write_text(json.dumps({
        "default": "balanced",
        **thresholds,
        "target_precision": TARGET_PRECISION,
        "target_recall": TARGET_RECALL,
    }, indent=2, ensure_ascii=False))

    (ARTIFACTS_DIR / "metrics.json").write_text(json.dumps({
        "test": {"roc_auc": roc, "pr_auc": pr, "default_threshold": test_metrics},
        "cv": cv,
        "data": {**data_info, "scale_pos_weight": spw},
        "model": {"type": "CatBoostClassifier", "best_iteration": best_iter, "params": MODEL_PARAMS},
        "targets": {
            "precision_target": TARGET_PRECISION, "recall_target": TARGET_RECALL,
            "precision_target_met": test_metrics["precision"] >= TARGET_PRECISION,
            "recall_target_met": test_metrics["recall"] >= TARGET_RECALL,
        },
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2, ensure_ascii=False))

    print("=" * 70)
    print("DONE.")
    print("=" * 70)


if __name__ == "__main__":
    main()