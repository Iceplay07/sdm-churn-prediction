
from catboost import CatBoostClassifier

from .config import (
    CAT_FEATURES,
    MODEL_PARAMS,
    RANDOM_STATE,
)


def calculate_scale_pos_weight(y_train):
    """
    Считает вес положительного класса.

    В churn-задаче уходящих клиентов обычно меньше, чем не уходящих.
    scale_pos_weight помогает модели сильнее обращать внимание на churn=1.
    """

    negative_count = (y_train == 0).sum()
    positive_count = (y_train == 1).sum()

    if positive_count == 0:
        return 1.0

    return negative_count / positive_count


def create_model(y_train):
    """
    Создаёт CatBoostClassifier для задачи предсказания оттока.
    """

    scale_pos_weight = calculate_scale_pos_weight(y_train)

    model = CatBoostClassifier(
        **MODEL_PARAMS,
        cat_features=CAT_FEATURES,
        scale_pos_weight=scale_pos_weight,
        loss_function="Logloss",
        eval_metric="AUC",
        random_seed=RANDOM_STATE,
        verbose=False,
        allow_writing_files=False,
    )

    return model, scale_pos_weight