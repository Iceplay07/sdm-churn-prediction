# Этап 3 — Backend и API. План выполнения

> Часы 5–10 по общему графику хакатона.
> Ответственные: **Самир** (основной), **Давид** (помощь по offers + ревью).

## 0. Что уже есть на старте этапа

Полностью готов вход для бэкенда (артефакты Этапа 2 в `model/`):

- `model/predict.py::predict(client_dict, mode)` → dict со score, is_at_risk, risk_level, top_factors[3], threshold_mode/value. **17 мс** на одного клиента (с SHAP).
- `model/predict.py::predict_batch(rows, mode)` → список dict, **1 мс/клиент** в батче.
- `model/predict.py::MODEL_INFO()` → метаданные модели для эндпоинта `/info`.
- `model/threshold.json` — три пресета: `balanced` (default, P=0.766/R=0.628), `high_precision` (для авто-кампаний), `high_recall` (для широкого охвата).
- `data/processed/features.csv` — фича-матрица 10 000 клиентов.
- `data/raw/clients.csv` — статичные профили (ФИО, возраст, регион). Нужно мерджить с features по `client_id`.

**Важно**: `predict.py` импортируется как `from model.predict import predict` — бэкенд просто кладёт `model/` в `PYTHONPATH` (либо запускается из корня проекта).

## 1. Структура папок

```
sdm-churn-prediction/
└── backend/
    ├── main.py                  # FastAPI app, роуты
    ├── schemas.py               # Pydantic-модели запросов/ответов
    ├── offers.py                # движок подбора офферов (правила + шаблоны)
    ├── data_loader.py           # пред-расчёт скоров для всех клиентов на старте
    ├── settings.py              # пути, CORS-origins, порт
    ├── tests/
    │   ├── conftest.py
    │   ├── test_api.py
    │   └── test_offers.py
    ├── Dockerfile
    ├── requirements.txt
    └── README.md
```

В корне проекта добавим `docker-compose.yml` (бэкенд + фронт Антона + nginx, если успеем).

## 2. Эндпоинты — финальный API

Целевая схема. **Контракт фиксируем в начале этапа** и шарим Антону, чтобы он не ждал реальный сервер.

| Метод | Путь | Назначение | Использует |
|---|---|---|---|
| GET | `/health` | Liveness probe (для Docker/Render) | — |
| GET | `/info` | Метаданные модели + пороги | `MODEL_INFO()` |
| POST | `/predict` | Скор для одного клиента (приходит dict с фичами) | `predict()` |
| POST | `/predict/batch` | Скоры для списка клиентов | `predict_batch()` |
| GET | `/clients/at-risk` | **Главный эндпоинт фронта** — список клиентов в зоне риска, с офферами. Поддерживает фильтры. | предрасчёт + offers |
| GET | `/clients/{client_id}` | Карточка одного клиента: профиль + скор + причины + история | предрасчёт + offers + raw csv |
| GET | `/clients/{client_id}/transactions` | История транзакций за 90 дней (для графиков Антона) | `data/raw/transactions.csv` |
| GET | `/offers/templates` | Список шаблонов офферов (для отладки) | `offers.py` |

### Параметры `/clients/at-risk`

```
GET /clients/at-risk
  ?mode=balanced|high_precision|high_recall   (default: balanced)
  &min_score=0.0                              (для слайдера на фронте)
  &geography=Москва|Санкт-Петербург|Регион    (фильтр Антона)
  &segment=premium|standard|basic             (по balance/n_products)
  &limit=50                                   (default 50, max 500)
  &offset=0                                   (пагинация)
  &sort=-score|name|days_silent               (default: -score)
```

Ответ:

```json
{
  "total": 471,
  "returned": 50,
  "mode": "balanced",
  "items": [
    {
      "client_id": 4242,
      "full_name": "Иван Петров",
      "geography": "Москва",
      "age": 34,
      "balance_rub": 12000,
      "n_products": 1,
      "churn_score": 0.94,
      "risk_level": "high",
      "top_factors": [
        {"feature": "support_tickets_30d", "value": 2, "impact": 1.52, "direction": "+"},
        ...
      ],
      "offer": {
        "id": "cashback_5pct_grocery",
        "title": "Повышенный кешбэк 5% на продукты",
        "reason": "Клиент тратит много на категорию grocery, активность падает",
        "estimated_lift": 0.18
      }
    }
  ]
}
```

## 3. Подзадачи и тайминг (часы 5–10 = 5 часов)

> Порядок выстроен так, чтобы **Антон смог начать фронт на часах 5:30**, а офферы появились в ответах позже без поломки контракта (поле `offer: null` сначала, потом заполняется).

### 3.1 Skeleton + /health + /info (≈30 мин, часы 5:00–5:30) — Самир

- Создать `backend/`, `requirements.txt`, `settings.py`.
- FastAPI app с CORS-middleware (origins: `http://localhost:3000`, `http://localhost:5173`).
- `GET /health` → `{"status": "ok"}`.
- `GET /info` → результат `MODEL_INFO()`.
- Запустить `uvicorn backend.main:app --reload --port 8000`. Открыть Swagger по `/docs`.
- **Закоммитить и сообщить Антону URL** — он сможет сразу проверить CORS.

### 3.2 Pydantic schemas + /predict + /predict/batch (≈45 мин, часы 5:30–6:15) — Самир

- В `schemas.py`:
  - `ClientFeaturesIn` — все 29 raw-фич + опциональный `client_id`. Все поля `Optional`, дефолты совпадают с `RAW_FEATURE_DEFAULTS` из `predict.py`.
  - `PredictionOut` — точно повторяет dict из `predict()`.
  - `BatchIn` / `BatchOut`.
  - `ModeEnum` — Literal `["balanced", "high_precision", "high_recall"]`.
- `POST /predict` → вызов `predict(payload.dict(), mode=mode)`.
- `POST /predict/batch` → `predict_batch(rows, mode)`.
- Smoke через Swagger: at-risk и loyal клиенты → ожидаемые скоры.

### 3.3 data_loader + /clients/at-risk + /clients/{id} (≈60 мин, часы 6:15–7:15) — Самир

**Ключевая идея**: на старте сервиса один раз считаем `predict_batch` для всех 8 471 активных клиентов (~9 секунд) и держим результат в памяти как DataFrame. Запросы фронта работают с in-memory таблицей — миллисекунды, никакого SHAP в горячем пути.

- В `data_loader.py`:
  - `load_all_clients()` → мерджит `clients.csv` с `features.csv` по `client_id`, фильтрует `already_churned_at_snapshot==0`.
  - `precompute_scores()` → вызывает `predict_batch` на всех активных клиентах для каждого из 3 mode (можно лениво: только `balanced` сразу, остальные по запросу).
  - Результат: pandas DataFrame с колонками `[client_id, full_name, geography, age, balance_rub, n_products, churn_score, risk_level, top_factors_json]`.
  - Хранится в `app.state.clients_df`.
  - При старте: `@app.on_event("startup")`.
- `GET /clients/at-risk` → фильтрует `clients_df` по параметрам, сортирует, paginates, добавляет `offer` (пока `None`).
- `GET /clients/{id}` → одна строка из `clients_df` + raw-профиль из `clients.csv`.
- `GET /clients/{id}/transactions` → `transactions.csv` по client_id, последние 90 дней, для графика на фронте.

**Сообщить Антону**: «эндпоинты для фронта живые, можно интегрировать. Поле `offer` пока `null` — появится через час».

### 3.4 offers.py — движок подбора офферов (≈60 мин, часы 7:15–8:15) — Самир + Давид

Подход: **rules-based + шаблоны**, без LLM (быстрее, детерминированно, легче объяснить жюри). LLM можно пристегнуть позже как украшение.

Логика выбора:

1. Берём `top_factors[0]` клиента (главная причина риска по SHAP).
2. По справочнику `RULES` — какой оффер триггерит этот фактор.
3. Уточняем по сегменту (`balance_rub`, `n_products`, `salary_monthly_rub`) — какой именно вариант шаблона.
4. Если ничего не подошло — fallback `default_retention_call`.

Шаблоны офферов (≈8 штук, покрывают все ключевые сигналы):

| Триггер (топ-фактор) | Оффер | Шаблон сообщения |
|---|---|---|
| `support_tickets_30d` высокий | Звонок персонального менеджера | «Иван, мы видим, что у вас были вопросы — менеджер свяжется завтра» |
| `unsubscribe_count_90d > 0` | Перенастройка коммуникаций | «Настройте уведомления по своему вкусу — только важное» |
| `inflow_drop_pct > 0.7` (зарплата ушла) | Бонус за перевод зарплаты | «Переведите зарплату — 1% дополнительно к вкладу» |
| `turnover_drop_*` + категория grocery | Кешбэк 5% на продукты | «Повышенный кешбэк на продукты на 3 месяца» |
| `sessions_drop_*` высокий | Реактивация в приложении | «Откройте приложение — подарок на главном экране» |
| `days_since_last_login >= 21` | Push-реактивация + бонус | «Скучаем! 500 ₽ на счёт за вход в приложение» |
| `n_products == 1` + balance высокий | Кросс-продажа вклада | «Откройте накопительный счёт — 14% годовых» |
| fallback | Звонок-удержание | «Передадим в отдел удержания» |

В `offers.py`:

- `OFFER_TEMPLATES` — список dict (id, title, reason_template, estimated_lift).
- `RULES` — список predicates `(factor_name, condition_fn) -> offer_id`.
- `pick_offer(client_row, top_factors) -> dict | None`.
- Юнит-тестируем на 5 эталонных клиентах из data.

После реализации — обновить `data_loader.precompute_scores`, чтобы сразу прикладывать `offer` к каждой строке `clients_df`. Антон автоматически увидит офферы в ответах без изменения контракта.

### 3.5 Pytest автотесты (≈45 мин, часы 8:15–9:00) — Самир

В `tests/conftest.py`:

- `client = TestClient(app)` фикстура.
- Перед всем — фикстура `precompute_done`, ждёт окончания startup-расчёта.

Покрываем минимально (8–10 тестов):

- `test_health` — 200 + status ok.
- `test_info` — есть thresholds.balanced/high_precision/high_recall.
- `test_predict_at_risk` — для эталонного «уходящего» клиента score > 0.7, is_at_risk True.
- `test_predict_loyal` — для эталонного лояльного score < 0.3.
- `test_predict_batch_keeps_order` — порядок ответа = порядок входа.
- `test_predict_mode_changes_threshold` — высокий-recall режим даёт больше is_at_risk=True.
- `test_at_risk_default` — список не пуст, отсортирован по score desc.
- `test_at_risk_pagination` — limit/offset работают.
- `test_at_risk_filters` — geography + min_score сужают выборку.
- `test_offers_attached` — у каждого at-risk клиента есть `offer`.
- `test_client_card_404` — несуществующий id → 404.

Запуск: `pytest backend/tests -v`. CI можно не ставить, но команда `make test` не помешает.

### 3.6 Dockerfile + docker-compose + E2E smoke (≈60 мин, часы 9:00–10:00) — Самир

- `backend/Dockerfile`: python:3.11-slim, копируем `model/` + `data/processed/features.csv` + `data/raw/clients.csv` + `backend/`. RUN `pip install -r backend/requirements.txt`. CMD `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
- `docker-compose.yml` в корне:
  ```yaml
  services:
    backend:
      build: ./backend
      ports: ["8000:8000"]
      volumes:
        - ./model:/app/model:ro
        - ./data:/app/data:ro
    frontend:
      build: ./frontend            # Антон добавит когда готово
      ports: ["3000:3000"]
      environment:
        - VITE_API_URL=http://localhost:8000
  ```
- E2E smoke: `docker compose up --build`, открыть `http://localhost:8000/docs` — все эндпоинты живые.

## 4. Параллелизм с другими этапами

```
часы:           5:00      6:00      7:00      8:00      9:00      10:00
Самир (3.1-3.6) ███skel███[at-risk][predict][offers ][ tests ][ docker ]
Антон  (этап 4)         ╚═══ старт фронта на mock ══════[switch to live API]
Миша   (этап 2)         ╚═══ доводка SHAP/refit если нужно
Давид           ╚═══════════ ревью + помощь по offers
```

Антон стартует фронт **в 5:30** на моках (контракт `/clients/at-risk` зафиксирован в этом плане). К часу 7 у него живой `/clients/at-risk` без офферов, к 8:15 — с офферами. Без блокировок.

## 5. Чек-лист «готово к Этапу 4»

- [ ] `docker compose up` поднимает бэкенд за < 30 секунд (включая precompute).
- [ ] Swagger `/docs` показывает все 8 эндпоинтов с примерами.
- [ ] CORS пропускает запросы Антона с `localhost:3000` и `localhost:5173`.
- [ ] `/clients/at-risk` возвращает 471 клиент в `balanced` режиме за < 100 мс.
- [ ] У каждого at-risk клиента есть `offer` (никаких `null`).
- [ ] `pytest` зелёный (≥10 тестов).
- [ ] `/health` отвечает 200 — годится для Render/Railway.
- [ ] README в `backend/` с примерами `curl`.

## 6. Риски и митигации

| Риск | Митигация |
|---|---|
| Precompute на старте занимает 9 секунд → долгий редеплой | Вынести в фоновую задачу + `/health` сначала отвечает 503 пока precompute не закончил, потом 200 |
| SHAP в `predict_batch` для 8 471 клиентов медленный/жрёт память | Использовать `predict_batch` пакетами по 1000, агрегировать. Или для at-risk таблицы хранить только score+offer, top_factors считать лениво в `/clients/{id}` |
| Антон ждёт офферы и блокируется | Контракт ответа уже включает `offer` (пусть `null` сначала). Антон рендерит «оффер появится» плейсхолдер до часа 8 |
| `from model.predict import predict` не находит модуль в Docker | Запускать `uvicorn` из корня проекта (`/app`), а не из `/app/backend`. PYTHONPATH=`/app` |
| LLM-офферы по плану — соблазн «улучшить» правилами LLM в последнюю минуту | НЕ трогаем. Rules-based детерминированно, тестируется, объяснимо. LLM — backlog для пост-хакатона |
| Несовместимость catboost/shap версий backend ↔ model | `backend/requirements.txt` начинается со `-r ../model/requirements.txt` |

## 7. Минимальный костяк main.py для старта

```python
# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from model.predict import predict, predict_batch, MODEL_INFO
from backend.schemas import ClientFeaturesIn, PredictionOut, ModeEnum
from backend.data_loader import precompute_scores, get_clients_df
from backend.offers import pick_offer


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[startup] precomputing scores for all clients...")
    app.state.clients_df = precompute_scores(mode="balanced")
    print(f"[startup] ready, {len(app.state.clients_df)} clients in memory")
    yield


app = FastAPI(title="SDM Churn API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/info")
def info():
    return MODEL_INFO()


@app.post("/predict", response_model=PredictionOut)
def predict_one(payload: ClientFeaturesIn, mode: ModeEnum = "balanced"):
    return predict(payload.dict(exclude_none=True), mode=mode)


@app.get("/clients/at-risk")
def clients_at_risk(
    mode: ModeEnum = "balanced",
    min_score: float = 0.0,
    geography: str | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    df = app.state.clients_df
    df = df[df["churn_score"] >= min_score]
    if geography:
        df = df[df["geography"] == geography]
    df = df.sort_values("churn_score", ascending=False)
    total = len(df)
    page = df.iloc[offset:offset + limit]
    return {
        "total": int(total),
        "returned": len(page),
        "mode": mode,
        "items": page.to_dict(orient="records"),
    }
```

С этим скелетом фронт стартует мгновенно, дальше доращиваем эндпоинты.
