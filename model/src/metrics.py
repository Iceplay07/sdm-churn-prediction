from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def calculate_metrics(y_true, probabilities, threshold):
    """
    Считает основные метрики бинарной классификации.

    probabilities — вероятности churn=1.
    threshold — порог, после которого считаем клиента рискованным.
    """

    predictions = (probabilities >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        predictions,
    ).ravel()

    return {
        "threshold": float(threshold),

        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "pr_auc": float(average_precision_score(y_true, probabilities)),

        "precision": float(
            precision_score(y_true, predictions, zero_division=0)
        ),
        "recall": float(
            recall_score(y_true, predictions, zero_division=0)
        ),
        "f1": float(
            f1_score(y_true, predictions, zero_division=0)
        ),

        "confusion_matrix": {
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "tn": int(tn),
        },
    }


def print_metrics(metrics: dict):
    """
    Красивый вывод метрик в консоль.
    """

    print("\nModel metrics")
    print("-" * 40)
    print(f"Threshold: {metrics['threshold']:.4f}")
    print(f"ROC-AUC:   {metrics['roc_auc']:.4f}")
    print(f"PR-AUC:    {metrics['pr_auc']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1-score:  {metrics['f1']:.4f}")

    cm = metrics["confusion_matrix"]

    print("\nConfusion matrix")
    print("-" * 40)
    print(f"TP: {cm['tp']}")
    print(f"FP: {cm['fp']}")
    print(f"FN: {cm['fn']}")
    print(f"TN: {cm['tn']}")