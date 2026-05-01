# Датасет SDM Churn

Синтетические данные для прогноза оттока клиентов СДМ Банка.
Сгенерированы скриптом `generate_dataset.py` (seed=42, воспроизводимо).

## Структура

```
data/
├── generate_dataset.py        # генератор
├── README.md                  # этот файл
├── raw/
│   ├── clients.csv            # статичные профили (10 000)
│   ├── transactions.csv       # ~2.16M строк, ежедневные транзакции
│   ├── app_sessions.csv       # ~1.63M строк, входы в моб. приложение
│   ├── communications.csv     # ~470k событий: push, отписки, тикеты
│   └── _profiles_full.pkl     # служебный кеш (содержит churn_day_idx)
└── processed/
    └── features.csv           # 10 000 строк, готов к ML
```

## Параметры генерации

| Параметр | Значение |
|---|---|
| Клиентов | 10 000 |
| Глубина истории | 180 дней (01.11.2025 — 29.04.2026) |
| Доля будущих churners | 20% |
| Окно затухания перед уходом | 28–56 дней |
| Snapshot date (T0) | 01.04.2026 |
| Окно наблюдения | последние 90 дней до T0 |
| Горизонт прогноза | 28 дней после T0 |

## Таблицы

### raw/clients.csv

Статичный профиль клиента + истинная разметка (для ML использовать только `churned_in_next_28d` из features.csv).

| Колонка | Тип | Описание |
|---|---|---|
| client_id | int | первичный ключ |
| first_name, last_name | str | ФИО |
| gender | M/F | пол |
| age | int | возраст |
| geography | Москва / Санкт-Петербург / Регион | регион |
| tenure_years | int 0..10 | стаж клиента |
| credit_score | int 350..850 | кредитный скор |
| salary_monthly_rub | int | зарплата в рублях |
| balance_rub | int | остаток на счёте |
| n_products | 1..4 | кол-во продуктов банка |
| has_credit_card | 0/1 | есть ли кредитка |
| is_active_member | 0/1 | флаг активного клиента |
| will_churn | 0/1 | **служебное** — истинный лейбл будущего ухода |
| churn_date | YYYY-MM-DD | **служебное** — дата ухода (пусто если не ушёл) |

### raw/transactions.csv

| Колонка | Тип | Описание |
|---|---|---|
| client_id | int | FK |
| date | YYYY-MM-DD | дата транзакции |
| amount_rub | int | сумма; **отрицательная = расход**, положительная = поступление |
| category | str | grocery, restaurants, transport, entertainment, utilities, online_shopping, pharmacy, transfer_out, transfer_in, atm_withdrawal |

### raw/app_sessions.csv

| Колонка | Тип | Описание |
|---|---|---|
| client_id | int | FK |
| date | YYYY-MM-DD | дата сессии |
| duration_sec | int | длительность сессии в секундах |

### raw/communications.csv

| Колонка | Тип | Описание |
|---|---|---|
| client_id | int | FK |
| date | YYYY-MM-DD | дата события |
| event | str | push_sent, push_opened, unsubscribe, support_ticket |

### processed/features.csv

Агрегированный feature-set, готов к подаче в CatBoost / LightGBM. Один клиент = одна строка.

**Статичные фичи**: age, gender, geography, tenure_years, credit_score, salary_monthly_rub, balance_rub, n_products, has_credit_card, is_active_member.

**Поведенческие фичи** (агрегаты на окне 60–30–0 дней до snapshot):

| Фича | Описание |
|---|---|
| tx_count_90d, tx_count_30d | кол-во транзакций |
| turnover_outflow_90d / 30d / 60d_prev | расходы (сумма) |
| inflow_30d, inflow_60d_prev | входящие переводы (зарплата) |
| sessions_30d, sessions_60d_prev | кол-во входов в приложение |
| days_since_last_tx, days_since_last_login | дней с последней активности |
| unsubscribe_count_90d | сколько раз отписался |
| support_tickets_30d | сколько обращений в поддержку |
| push_received_90d, push_opened_90d | пуши |

**Производные фичи (главные сигналы оттока)**:

| Фича | Описание |
|---|---|
| **turnover_drop_30d_vs_60d_pct** | (обороты_60d_prev − обороты_30d) / обороты_60d_prev. Положительное = падение |
| **sessions_drop_30d_vs_60d_pct** | то же для входов в приложение |
| **inflow_drop_pct** | падение поступлений (зарплата) |
| **push_open_rate_90d** | доля открытых пушей |

**Таргет**:

| Колонка | Описание |
|---|---|
| `churned_in_next_28d` | 1 если клиент уйдёт в окне (T0, T0+28] |
| `already_churned_at_snapshot` | 1 если уже ушёл к T0 — **этих клиентов нужно фильтровать перед обучением** |

## Использование (минимальный пример)

```python
import pandas as pd
from sklearn.model_selection import train_test_split
from catboost import CatBoostClassifier

df = pd.read_csv("data/processed/features.csv")
df = df[df["already_churned_at_snapshot"] == 0]  # убираем уже ушедших

y = df["churned_in_next_28d"]
X = df.drop(columns=["client_id", "churned_in_next_28d", "already_churned_at_snapshot"])

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

model = CatBoostClassifier(
    cat_features=["gender", "geography"],
    iterations=500, depth=6, learning_rate=0.05,
    eval_metric="AUC", verbose=False,
)
model.fit(X_train, y_train, eval_set=(X_test, y_test))
```

## Репродуцируемость

Скрипт идемпотентный — если CSV уже в `raw/`, шаг пропускается. Чтобы перегенерить с нуля:

```bash
rm data/raw/*.csv data/raw/*.pkl data/processed/*.csv
python data/generate_dataset.py
```

Время выполнения с нуля: ~60–90 сек на ноуте.

## Что в данных «зашито» как сигнал оттока

Для будущих churners за 28–56 дней до `churn_date` интенсивность активности линейно затухает (до 20% от базы):

* транзакции (количество и сумма) — падают
* входы в приложение — реже
* открываемость push — снижается, чаще отписки
* обращения в поддержку — заметно чаще, чем у стабильных клиентов

После `churn_date` активность нулевая. Это даёт модели реальный поведенческий сигнал, который проверяется через стандартные feature-importance / SHAP-объяснения.

## Sanity-check (на текущем сиде)

| Показатель | Значение |
|---|---|
| Активных клиентов на snapshot | 8 471 |
| Из них уйдут в 28-дневном горизонте | 471 (5.56%) |
| Уже ушли к snapshot (фильтруются) | 1 529 |
| Топ-3 по корреляции с таргетом | support_tickets_30d (+0.55), unsubscribe_count_90d (+0.30), days_since_last_login (+0.26) |
