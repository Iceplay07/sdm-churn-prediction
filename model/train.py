"""SDM Churn — обучение модели предсказания оттока (Этап 2 хакатона).

Запуск:  python -m model.train

Артефакты в model/:
  - model.pkl, feature_list.json, threshold.json, metrics.json
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split

from model.features import ENGINEERED_FEATURES, add_engineered_features

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "processed" / "features.csv"
MODEL_DIR = ROOT / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_SPLITS = 5

CAT_FEATURES = ["gender", "geography"]
DROP_COLS = ["client_id", "churned_in_next_28d", "already_churned_at_snapshot"]
TARGET = "churned_in_next_28d"

TARGET_PRECISION = 0.75
TARGET_RECALL = 0.70

MODEL_PARAMS = dict(
    iterations=2000,
    depth=6,
    learning_rate=0.03,
    l2_leaf_reg=5.0,
    min_data_in_leaf=20,
    early_stopping_rounds=80,
)


def load_data(path: Path):
    df = pd.read_csv(path)
    n_total = len(df)
    df = df[df["already_churned_at_snapshot"] == 0].reset_index(drop=True)
    n_active = len(df)
    df = add_engineered_features(df)

    y = df[TARGET].astype(int)
    X = df.drop(columns=DROP_COLS)
    features = X.columns.tolist()

    print(f"[data] total rows         : {n_total}")
    print(f"[data] active (post-filter): {n_active}  (dropped {n_total - n_active})")
    print(f"[data] target positive rate: {y.mean():.4f}  ({int(y.sum())} positives)")
    print(f"[data] features total ({len(features)}), of which engineered: {len(ENGINEERED_FEATURES)}")
    return X, y, features


def build_model(scale_pos_weight: float) -> CatBoostClassifier:
    return CatBoostClassifier(
        cat_features=CAT_FEATURES,
        scale_pos_weight=scale_pos_weight,
        eval_metric="AUC",
        loss_function="Logloss",
        random_seed=RANDOM_STATE,
        verbose=False,
        allow_writing_files=False,
        **MODEL_PARAMS,
    )


def pick_threshold(y_true, proba, target_precision, target_recall):
    precision, recall, thr = precision_recall_curve(y_true, proba)
    f1 = (2 * precision * recall) / (precision + recall + 1e-12)

    def at(i):
        return {
            "threshold": float(thr[i]),
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
        }

    best_f1_i = int(np.argmax(f1[:-1]))
    balanced = at(best_f1_i)

    hp = [i for i in range(len(thr)) if precision[i] >= target_precision and recall[i] > 0]
    high_precision = at(max(hp, key=lambda i: recall[i])) if hp else None

    hr = [i for i in range(len(thr)) if recall[i] >= target_recall]
    high_recall = at(max(hr, key=lambda i: precision[i])) if hr else None

    return {"balanced": balanced, "high_precision": high_precision, "high_recall": high_recall}


def metrics_at_threshold(y_true, proba, thr):
    pred = (proba >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred).ravel()
    return {
        "threshold": float(thr),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "confusion_matrix": {"tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)},
    }


def cross_validate(X, y, scale_pos_weight):
    skf = StratifiedKFold(n_splits=CV_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    roc_scores, pr_scores = [], []
    for fold, (tr_idx, va_idx) in enumerate(skf.split(X, y), 1):
        m = build_model(scale_pos_weight)
        m.fit(X.iloc[tr_idx], y.iloc[tr_idx], eval_set=(X.iloc[va_idx], y.iloc[va_idx]), verbose=False)
        proba = m.predict_proba(X.iloc[va_idx])[:, 1]
        roc = roc_auc_score(y.iloc[va_idx], proba)
        pr = average_precision_score(y.iloc[va_idx], proba)
        roc_scores.append(roc)
        pr_scores.append(pr)
        print(f"  [cv fold {fold}/{CV_SPLITS}] ROC-AUC={roc:.4f}  PR-AUC={pr:.4f}")
    return {
        "roc_auc_mean": float(np.mean(roc_scores)),
        "roc_auc_std": float(np.std(roc_scores)),
        "pr_auc_mean": float(np.mean(pr_scores)),
        "pr_auc_std": float(np.std(pr_scores)),
    }


def main():
    print("=" * 70)
    print("SDM Churn Prediction — Stage 2 Training")
    print("=" * 70)

    X, y, feature_list = load_data(DATA_PATH)

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    spw = float((y_tr == 0).sum() / max((y_tr == 1).sum(), 1))
    print(f"\n[split] train={len(X_tr)}  test={len(X_te)}  scale_pos_weight={spw:.2f}")

    print("\n[cv] 5-fold stratified cross-validation on full dataset...")
    cv = cross_validate(X, y, spw)
    print(f"[cv] ROC-AUC = {cv['roc_auc_mean']:.4f} +/- {cv['roc_auc_std']:.4f}")
    print(f"[cv] PR-AUC  = {cv['pr_auc_mean']:.4f} +/- {cv['pr_auc_std']:.4f}")

    print("\n[fit] training final model on train split...")
    model = build_model(spw)
    model.fit(X_tr, y_tr, eval_set=(X_te, y_te), verbose=False)
    best_iter = model.get_best_iteration()
    print(f"[fit] best_iteration = {best_iter}")

    proba = model.predict_proba(X_te)[:, 1]
    roc = roc_auc_score(y_te, proba)
    pr = average_precision_score(y_te, proba)
    print(f"\n[test] ROC-AUC = {roc:.4f}")
    print(f"[test] PR-AUC  = {pr:.4f}")
    print("\n[test] classification report at threshold=0.5:")
    print(classification_report(y_te, (proba >= 0.5).astype(int), digits=3))

    print("[threshold] picking thresholds...")
    thresholds = pick_threshold(
        y_te.to_numpy(), proba,
        target_precision=TARGET_PRECISION, target_recall=TARGET_RECALL,
    )
    print(f"[threshold] balanced       : {thresholds['balanced']}")
    print(f"[threshold] high_precision : {thresholds['high_precision']}")
    print(f"[threshold] high_recall    : {thresholds['high_recall']}")

    default_thr = thresholds["balanced"]["threshold"]
    test_metrics = metrics_at_threshold(y_te.to_numpy(), proba, default_thr)
    print(f"\n[final] metrics at default threshold={default_thr:.4f}:")
    print(f"        precision={test_metrics['precision']:.3f}  "
          f"recall={test_metrics['recall']:.3f}  f1={test_metrics['f1']:.3f}")

    print("\n[save] writing artifacts...")
    model_path = MODEL_DIR / "model.pkl"
    joblib.dump(model, model_path)
    print(f"  - {model_path}")

    feature_meta = {
        "version": "1.0",
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "feature_list": feature_list,
        "engineered_features": ENGINEERED_FEATURES,
        "cat_features": CAT_FEATURES,
        "drop_cols": DROP_COLS,
        "target": TARGET,
        "n_features": len(feature_list),
    }
    (MODEL_DIR / "feature_list.json").write_text(
        json.dumps(feature_meta, indent=2, ensure_ascii=False)
    )
    print(f"  - {MODEL_DIR / 'feature_list.json'}")

    threshold_meta = {
        "default": "balanced",
        "balanced": thresholds["balanced"],
        "high_precision": thresholds["high_precision"],
        "high_recall": thresholds["high_recall"],
        "target_precision": TARGET_PRECISION,
        "target_recall": TARGET_RECALL,
    }
    (MODEL_DIR / "threshold.json").write_text(
        json.dumps(threshold_meta, indent=2, ensure_ascii=False)
    )
    print(f"  - {MODEL_DIR / 'threshold.json'}")

    metrics_meta = {
        "test": {
            "roc_auc": float(roc),
            "pr_auc": float(pr),
            "default_threshold": test_metrics,
        },
        "cv": cv,
        "data": {
            "n_train": int(len(X_tr)),
            "n_test": int(len(X_te)),
            "positive_rate": float(y.mean()),
            "scale_pos_weight": spw,
        },
        "model": {
            "type": "CatBoostClassifier",
            "best_iteration": int(best_iter),
            "params": MODEL_PARAMS,
        },
        "targets": {
            "precision_target": TARGET_PRECISION,
            "recall_target": TARGET_RECALL,
            "precision_target_met": test_metrics["precision"] >= TARGET_PRECISION,
            "recall_target_met": test_metrics["recall"] >= TARGET_RECALL,
        },
    }
    (MODEL_DIR / "metrics.json").write_text(
        json.dumps(metrics_meta, indent=2, ensure_ascii=False)
    )
    print(f"  - {MODEL_DIR / 'metrics.json'}")

    print("\n" + "=" * 70)
    print("DONE.")
    print("=" * 70)


if __name__ == "__main__":
    main()
