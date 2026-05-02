# SDM Churn API

Бэкенд для дашборда «ИИ-Маркетолог СДМ Банка». FastAPI поверх готовой ML-модели (Этап 2).

## Запуск

### Локально

```bash
# Из корня sdm-churn-prediction/
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Документация Swagger: http://localhost:8000/docs

### Docker

```bash
docker compose up --build
```

При первом старте сервис ~3 секунды считает скоры для всех 8 471 активных клиентов и держит результат в памяти. До завершения precompute `/health` отвечает 503.

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| GET  | `/health` | Liveness |
| GET  | `/info` | Метаданные модели + 3 пресета порога |
| POST | `/predict` | Скор оттока для одного клиента |
| POST | `/predict/batch` | Пакетное предсказание (до 1000) |
| GET  | `/clients/at-risk` | Список клиентов в зоне риска (с офферами) |
| GET  | `/clients/{id}` | Карточка клиента |
| GET  | `/clients/{id}/transactions` | История транзакций (для графика) |
| GET  | `/offers/templates` | Все шаблоны офферов |

## Примеры

```bash
# Список 10 самых рискованных клиентов в Москве
curl 'http://localhost:8000/clients/at-risk?geography=Москва&limit=10'

# Скор для гипотетического клиента
curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"client_id":1,"age":30,"gender":"M","geography":"Москва",
       "salary_monthly_rub":80000,"balance_rub":5000,"n_products":1,
       "support_tickets_30d":2,"days_since_last_login":21,
       "inflow_drop_pct":1.0}'

# Переключиться на «широкий охват» (Recall ≥ 0.70)
curl 'http://localhost:8000/clients/at-risk?mode=high_recall&limit=20'
```

## Параметры `/clients/at-risk`

| Параметр | По умолчанию | Что делает |
|---|---|---|
| `mode` | `balanced` | Пресет порога: `balanced` / `high_precision` / `high_recall` |
| `min_score` | `0.0` | Скрыть клиентов со скором ниже |
| `geography` | — | Москва / Санкт-Петербург / Регион |
| `segment` | — | premium / standard / basic |
| `only_at_risk` | `true` | Показывать только тех, у кого `is_at_risk=true` |
| `limit` | `50` | До 500 |
| `offset` | `0` | Пагинация |
| `sort` | `-score` | `-score`, `score`, `-name`, `name`, `-segment`, `segment` |

## Тесты

```bash
make test
```

23 теста, ~3 секунды.

## Архитектура (короткая)

```
backend/
├── main.py          FastAPI routes
├── schemas.py       Pydantic-модели (DTO)
├── data_loader.py   precompute_scores (startup) + lazy transactions
├── offers.py        rules-based движок подбора офферов
├── settings.py      ENV-конфиг
└── tests/           pytest, 23 теста
```

Внутри `precompute_scores` вызывается `predict_batch` из `model/predict.py` — единый источник истины для скоров и top_factors. SHAP в горячем пути (`/clients/at-risk`) не запускается — всё уже посчитано на старте.
