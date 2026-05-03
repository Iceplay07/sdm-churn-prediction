
import numpy as np
from sklearn.metrics import precision_recall_curve

from .config import TARGET_PRECISION, TARGET_RECALL


def make_threshold_info(threshold, precision, recall, f1):
    """
    Упаковывает информацию о пороге в словарь.
    """

    return {
        "threshold": float(threshold),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def pick_thresholds(
    y_true,
    probabilities,
    target_precision=TARGET_PRECISION,
    target_recall=TARGET_RECALL,
):
    """
    Подбирает три порога:

    balanced:
        максимальный F1-score.

    high_precision:
        режим экономии бюджета.
        Меньше ложных тревог, но можно пропустить часть уходящих.

    high_recall:
        агрессивное удержание.
        Находим больше уходящих, но больше ложных тревог.
    """

    precision, recall, thresholds = precision_recall_curve(
        y_true,
        probabilities,
    )

    # precision и recall на один элемент длиннее, чем thresholds.
    # Поэтому для F1, связанного с thresholds, берём все кроме последнего.
    precision_for_thresholds = precision[:-1]
    recall_for_thresholds = recall[:-1]

    f1 = (
        2
        * precision_for_thresholds
        * recall_for_thresholds
        / (precision_for_thresholds + recall_for_thresholds + 1e-12)
    )

    best_f1_index = int(np.argmax(f1))

    balanced = make_threshold_info(
        thresholds[best_f1_index],
        precision_for_thresholds[best_f1_index],
        recall_for_thresholds[best_f1_index],
        f1[best_f1_index],
    )

    high_precision = find_high_precision_threshold(
        thresholds,
        precision_for_thresholds,
        recall_for_thresholds,
        f1,
        target_precision,
    )

    high_recall = find_high_recall_threshold(
        thresholds,
        precision_for_thresholds,
        recall_for_thresholds,
        f1,
        target_recall,
    )

    return {
        "default": "balanced",
        "balanced": balanced,
        "high_precision": high_precision,
        "high_recall": high_recall,
    }


def find_high_precision_threshold(
    thresholds,
    precision,
    recall,
    f1,
    target_precision,
):
    """
    Ищет порог, где precision >= target_precision.
    Среди таких вариантов выбираем тот, где recall максимальный.
    """

    candidate_indices = np.where(precision >= target_precision)[0]

    if len(candidate_indices) == 0:
        return None

    best_index = max(
        candidate_indices,
        key=lambda i: recall[i],
    )

    return make_threshold_info(
        thresholds[best_index],
        precision[best_index],
        recall[best_index],
        f1[best_index],
    )


def find_high_recall_threshold(
    thresholds,
    precision,
    recall,
    f1,
    target_recall,
):
    """
    Ищет порог, где recall >= target_recall.
    Среди таких вариантов выбираем тот, где precision максимальный.
    """

    candidate_indices = np.where(recall >= target_recall)[0]

    if len(candidate_indices) == 0:
        return None

    best_index = max(
        candidate_indices,
        key=lambda i: precision[i],
    )

    return make_threshold_info(
        thresholds[best_index],
        precision[best_index],
        recall[best_index],
        f1[best_index],
    )