# Этап 2 — ML-модель. План выполнения

> Часы 3–8 по общему графику хакатона.
> Ответственные: **Миша** (DS, основной), **Давид** (ML-архитектор, ревью + экспорт), **Самир** (подключит модель в FastAPI на Этапе 3).

## 0. Что уже есть на старте этапа

- `data/raw/` — clients, transactions, app_sessions, communications (синтетика, seed=42).
- `data/processed/features.csv` — **готовая feature-матрица** (10 000 строк × 32 колонки), таргет `churned_in_next_28d`.
- Sanity по датасету: 8 471 активных клиента, **churn-rate ≈ 5.56% (471 позитивов)** — **сильный дисбаланс классов**.
- Референс-ноутбук: `customer-churn-prediction-in-banking-sector.ipynb` (Kaggle baseline, можно подсмотреть структуру).

> Важно: основной feature engineering уже сделан Мишей. На Этапе 2 фокус на **обучение, тюнинг, объяснимость и экспорт**, а не на повторную сборку фич.

## 1. Структура папок (создаём в начале этапа)

```
sdm-churn-prediction/
├── notebooks/
│   ├── 01_eda.ipynb              # быстрый EDA на features.csv
│   ├── 02_baseline.ipynb         # logreg + catboost baseline
│   ├── 03_tuning.ipynb           # подбор гиперпараметров и порога
│   └── 04_shap.ipynb             # объяснимость
├── model/
│   ├── train.py                  # воспроизводимое обучение → model.pkl
│   ├── predict.py                # функция predict(client_dict) → {score, top_factors}
│   ├── model.pkl                 # финальная модель (joblib)
│   ├── threshold.json            # выбранный порог + метрики на нём
│   ├── feature_list.json         # порядок фич, типы, cat_features
│   └── metrics.json              # ROC-AUC, PR-AUC, precision, recall, F1
└── reports/
    ├── shap_summary.png
    ├── pr_curve.png
    └── confusion_matrix.png
```

Самиру это даст всё, что нужно для интеграции: `model.pkl + predict.py + feature_list.json + threshold.json`.

## 2. Подзадачи и тайминг

### 2.1 EDA и sanity-check (≈30 мин) — Миша

- Загрузить `features.csv`, отфильтровать `already_churned_at_snapshot == 0`.
- Распределения таргета, дисбаланс, NaN-ы, выбросы по фичам.
- Корреляции с таргетом (по data/README.md ожидаем топ-3: `support_tickets_30d`, `unsubscribe_count_90d`, `days_since_last_login`).
- Парные графики ключевых сигналов: `turnover_drop_30d_vs_60d_pct`, `sessions_drop_30d_vs_60d_pct`, `inflow_drop_pct`.
- Вывод: ничего не утекает (`churn_date`, `will_churn` отсутствуют в features), фичи не имеют look-ahead bias.

### 2.2 Train/Test split (10 мин) — Миша

- `X = df.drop(["client_id", "churned_in_next_28d", "already_churned_at_snapshot"])`, `y = churned_in_next_28d`.
- `train_test_split(test_size=0.2, stratify=y, random_state=42)`.
- Доп. **валидация: StratifiedKFold (n=5)** — чтобы метрики на дисбалансе были стабильные.
- `cat_features = ["gender", "geography"]` для CatBoost.

### 2.3 Baseline-модели (≈40 мин) — Миша + Давид

Цель — иметь точку отсчёта и убедиться, что задача в принципе решается.

| Модель | Зачем |
|---|---|
| DummyClassifier (most_frequent) | Базовая проверка, что любая модель должна бить ~94.4% accuracy за счёт большинства |
| LogisticRegression (с `class_weight="balanced"`) | Линейный baseline, проверка интерпретируемости коэффициентов |
| CatBoostClassifier (default) | Главный кандидат, нативно работает с категориями |
| LightGBM (для сравнения) | Резервный, если CatBoost начнёт переобучаться |

Метрики, которые считаем для всех: **ROC-AUC, PR-AUC, Precision@K=10%, Recall, F1**. Accuracy не смотрим — бесполезна на 5.56% дисбалансе.

### 2.4 Борьба с дисбалансом (≈30 мин) — Миша

В порядке предпочтения, тестируем 1–2 подхода:

1. **`scale_pos_weight = neg/pos ≈ 17`** в CatBoost/LightGBM — проще всего, обычно достаточно.
2. **`auto_class_weights="Balanced"`** в CatBoost — встроенная альтернатива.
3. SMOTE/oversampling — НЕ рекомендую, на табличке часто шумит. Если время есть — сравнить честно.

Обязательно фиксируем результат до/после: какая опция дала лучший PR-AUC.

### 2.5 Основная модель и подбор гиперпараметров (≈60 мин) — Миша + Давид

CatBoost — основной кандидат:

```python
CatBoostClassifier(
    cat_features=["gender", "geography"],
    iterations=1000,
    depth=6,
    learning_rate=0.05,
    l2_leaf_reg=3,
    scale_pos_weight=17,
    eval_metric="AUC",
    early_stopping_rounds=50,
    random_seed=42,
    verbose=False,
)
```

Тюнинг быстрый и прицельный (**Optuna / RandomizedSearch с 20–30 trials, не больше — времени мало**):

- `depth`: 4–8
- `learning_rate`: 0.01–0.1
- `l2_leaf_reg`: 1–10
- `iterations` через `early_stopping_rounds`

Кросс-валидация — `StratifiedKFold(n_splits=5)`, оптимизируем по **PR-AUC** (а не ROC-AUC, потому что задача с дисбалансом).

### 2.6 Подбор порога срабатывания (≈20 мин) — Миша

Цели по плану: **Precision > 75%, Recall > 70%**. На churn-rate 5.56% это амбициозно; нужен честный анализ trade-off.

- Построить PR-кривую, найти порог, где Precision ≥ 0.75 и Recall максимальный.
- Если оба не достигаются одновременно — дать **2 рабочих режима**:
  - «Высокая точность» (Precision ≥ 0.80) — для авто-офферов.
  - «Широкий охват» (Recall ≥ 0.70) — для ручной работы маркетолога.
- Сохранить выбранный порог в `model/threshold.json`:
  ```json
  {"threshold": 0.42, "precision": 0.78, "recall": 0.71, "f1": 0.74}
  ```

### 2.7 SHAP-объяснимость (≈30 мин) — Миша

- `shap.TreeExplainer(model)` → `shap_values` на test-сете.
- Сохранить:
  - `reports/shap_summary.png` — глобальная важность фич (для презентации).
  - `reports/shap_dependence_*.png` для топ-3 фич.
- В `predict.py` вернуть **топ-3 фактора риска для конкретного клиента** — это нужно фронту для карточки клиента (Антон) и для скрипта офферов (Самир).

```python
def explain(model, x_row):
    sv = explainer.shap_values(x_row)
    contribs = sorted(zip(feature_names, sv[0]), key=lambda t: -abs(t[1]))[:3]
    return [{"feature": f, "impact": float(v)} for f, v in contribs]
```

### 2.8 Экспорт модели и predict-функция (≈30 мин) — Давид

`model/train.py` — один воспроизводимый скрипт:

```bash
python model/train.py
# → читает data/processed/features.csv
# → обучает финальную модель на всём train (best params из тюнинга, фиксированы)
# → сохраняет model/model.pkl, threshold.json, feature_list.json, metrics.json
```

`model/predict.py` — публичный интерфейс для бэкенда:

```python
def predict(client_features: dict) -> dict:
    """
    Returns:
      {
        "client_id": int,
        "churn_score": float,        # 0..1
        "churn_probability_pct": int,# 0..100
        "is_at_risk": bool,          # score >= threshold
        "top_factors": [{"feature": str, "impact": float}, ...]
      }
    """
```

Контракт фиксируем заранее и согласовываем с Самиром — он повесит это на эндпоинт `/predict`.

### 2.9 Финальный отчёт по метрикам (≈15 мин) — Миша

`model/metrics.json` + короткий summary в чат команды:

- ROC-AUC, PR-AUC (cv-mean ± std).
- Precision/Recall/F1 на выбранном пороге.
- Confusion matrix (TP/FP/FN/TN).
- Топ-10 фич по SHAP (для слайдов на Этап 5).

## 3. Чек-лист «готово к Этапу 3»

- [ ] `model/model.pkl` существует, грузится через `joblib.load`.
- [ ] `model/predict.py::predict(features_dict)` работает на одном клиенте за < 50 мс.
- [ ] `model/feature_list.json` описывает порядок и типы всех 29 фич (без таргета и id).
- [ ] `model/threshold.json` зафиксирован.
- [ ] `metrics.json` показывает Precision ≥ 0.75 **или** Recall ≥ 0.70 (в идеале — оба, но честно по trade-off).
- [ ] SHAP `top_factors` отдаются predict-функцией, не падают на edge-case клиентах (нулевая активность, NaN).
- [ ] Самир протестировал интеграцию: `from model.predict import predict` импортируется из `backend/`.

## 4. Риски и митигации

| Риск | Митигация |
|---|---|
| Не достигаем Precision 75% и Recall 70% одновременно | Даём 2 порога/режима, в презентации честно показываем PR-кривую |
| Модель переобучается на синтетике (фичи слишком «чистые») | Кросс-валидация + early stopping; в SHAP проверяем что топ-фичи совпадают с теми, что заложил генератор |
| Долгий тюнинг съедает время Этапа 3 | Жёсткий timebox 60 мин на Optuna; если не лучше baseline на 2 п.п. — оставляем baseline |
| Конфликт версий `catboost`/`shap` с бэкендом Самира | Фиксируем версии в `model/requirements.txt` и переиспользуем их в `backend/requirements.txt` |

## 5. Минимальный воспроизводимый код для старта (Миша запускает первым)

```python
import pandas as pd
from sklearn.model_selection import train_test_split
from catboost import CatBoostClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, classification_report

df = pd.read_csv("data/processed/features.csv")
df = df[df["already_churned_at_snapshot"] == 0].reset_index(drop=True)

y = df["churned_in_next_28d"]
X = df.drop(columns=["client_id", "churned_in_next_28d", "already_churned_at_snapshot"])

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

model = CatBoostClassifier(
    cat_features=["gender", "geography"],
    iterations=1000, depth=6, learning_rate=0.05,
    scale_pos_weight=(y_tr == 0).sum() / (y_tr == 1).sum(),
    eval_metric="AUC", early_stopping_rounds=50,
    random_seed=42, verbose=100,
)
model.fit(X_tr, y_tr, eval_set=(X_te, y_te))

proba = model.predict_proba(X_te)[:, 1]
print("ROC-AUC :", roc_auc_score(y_te, proba))
print("PR-AUC  :", average_precision_score(y_te, proba))
print(classification_report(y_te, (proba >= 0.5).astype(int), digits=3))
```

Если этот скрипт даёт ROC-AUC > 0.90 (а на такой синтетике скорее всего даст 0.95+) — **дальше идём в подбор порога и SHAP, не закапываемся в тюнинг**.
