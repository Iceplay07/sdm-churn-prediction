
import pandas as pd
from sklearn.model_selection import train_test_split

from .config import (
    DATA_PATH,
    TARGET,
    DROP_COLS,
    TEST_SIZE,
    RANDOM_STATE,
)
from .features import add_engineered_features, ENGINEERED_FEATURES


def load_raw_features(path=DATA_PATH) -> pd.DataFrame:
    """
    Загружает готовый features.csv.
    """

    return pd.read_csv(path)


def filter_active_clients(df: pd.DataFrame) -> pd.DataFrame:
    """
    Убирает клиентов, которые уже ушли на момент snapshot.

    Предсказывать уход уже ушедшего клиента бессмысленно.
    """

    if "already_churned_at_snapshot" not in df.columns:
        return df

    return df[df["already_churned_at_snapshot"] == 0].reset_index(drop=True)


def prepare_xy(df: pd.DataFrame):
    """
    Делает из общей таблицы:

    X — признаки модели;
    y — правильный ответ, то есть target.
    """

    if TARGET not in df.columns:
        raise ValueError(f"В данных нет целевой колонки: {TARGET}")

    y = df[TARGET].astype(int)

    X = df.drop(columns=DROP_COLS, errors="ignore")

    return X, y


def load_training_data(path=DATA_PATH):
    """
    Полная подготовка данных для обучения:

    1. загружаем features.csv;
    2. убираем уже ушедших клиентов;
    3. добавляем инженерные признаки;
    4. разделяем на X и y;
    5. возвращаем дополнительную информацию о данных.
    """

    df = load_raw_features(path)

    total_rows = len(df)

    df = filter_active_clients(df)

    active_rows = len(df)

    df = add_engineered_features(df)

    X, y = prepare_xy(df)

    data_info = {
        "total_rows": int(total_rows),
        "active_rows": int(active_rows),
        "dropped_rows": int(total_rows - active_rows),
        "n_features": int(X.shape[1]),
        "n_engineered_features": int(len(ENGINEERED_FEATURES)),
        "positive_rate": float(y.mean()),
        "positive_count": int((y == 1).sum()),
        "negative_count": int((y == 0).sum()),
    }

    return X, y, data_info


def split_data(X, y):
    """
    Делит данные на train и test.

    stratify=y нужен, чтобы доля churn=1 была одинаковой
    и в обучении, и в тесте.
    """

    return train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )