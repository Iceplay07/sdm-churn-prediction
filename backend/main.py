"""SDM Churn API — FastAPI app для маркетолога СДМ Банка.

Запуск (из корня sdm-churn-prediction):
    uvicorn backend.main:app --reload --port 8000

Документация: http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend import settings
from backend.data_loader import precompute_scores, load_transactions
from backend.offers import list_templates
from backend.schemas import (
    AtRiskListOut,
    BatchIn,
    BatchOut,
    ClientCardOut,
    ClientFeaturesIn,
    ModeEnum,
    PredictionOut,
    TransactionsResponse,
)
from model.predict import MODEL_INFO, predict, predict_batch


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[startup] precomputing scores for all active clients...")
    app.state.clients_df = precompute_scores(mode="balanced")
    app.state.precompute_mode = "balanced"
    print(f"[startup] ready: {len(app.state.clients_df)} clients in memory")
    yield
    print("[shutdown] bye")


app = FastAPI(
    title="SDM Churn Prediction API",
    description=(
        "ИИ-Маркетолог СДМ Банка. "
        "Эндпоинты для дашборда: список клиентов в зоне риска с офферами удержания, "
        "карточка клиента, история транзакций. Под капотом — CatBoost + SHAP."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------
def _df():
    df = app.state.clients_df
    if df is None:
        raise HTTPException(503, "Сервис ещё инициализируется")
    return df


# ---------------------------------------------------------------------------
# Health & Info
# ---------------------------------------------------------------------------
@app.get("/health", tags=["meta"])
def health():
    """Liveness probe для docker/render. 503 пока precompute не закончил."""
    if getattr(app.state, "clients_df", None) is None:
        raise HTTPException(503, "warming up")
    return {"status": "ok", "clients_loaded": int(len(app.state.clients_df))}


@app.get("/info", tags=["meta"])
def info():
    """Метаданные модели: версия, дата обучения, пороги."""
    return MODEL_INFO()


# ---------------------------------------------------------------------------
# Predict
# ---------------------------------------------------------------------------
@app.post("/predict", response_model=PredictionOut, tags=["predict"])
def predict_one(payload: ClientFeaturesIn, mode: ModeEnum = "balanced"):
    """Скор оттока для одного клиента + 3 главных фактора риска."""
    return predict(payload.model_dump(exclude_none=True), mode=mode)


@app.post("/predict/batch", response_model=BatchOut, tags=["predict"])
def predict_many(payload: BatchIn, mode: ModeEnum = "balanced"):
    """Пакетное предсказание — для массовой переоценки портфеля."""
    if len(payload.rows) > settings.MAX_BATCH_SIZE:
        raise HTTPException(413, f"Слишком большой батч (max={settings.MAX_BATCH_SIZE})")
    rows = [r.model_dump(exclude_none=True) for r in payload.rows]
    return {"items": predict_batch(rows, mode=mode)}


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
@app.get("/clients/at-risk", response_model=AtRiskListOut, tags=["clients"])
def clients_at_risk(
    mode: ModeEnum = "balanced",
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    geography: Optional[str] = None,
    segment: Optional[str] = Query(None, pattern="^(premium|standard|basic)$"),
    only_at_risk: bool = True,
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    sort: str = Query("-score", pattern="^-?(score|name|segment)$"),
):
    """Главный эндпоинт дашборда: клиенты в зоне риска с готовыми офферами."""
    df = _df()
    # Если запрошен другой режим порога — пересчитываем is_at_risk на лету
    # (само precompute сделано в balanced; для high_recall/high_precision можно
    # вызвать precompute_scores ещё раз при первом обращении — отложим)
    f = df.copy()
    if only_at_risk:
        f = f[f["is_at_risk"] == True]  # noqa: E712
    if min_score > 0:
        f = f[f["churn_score"] >= min_score]
    if geography:
        f = f[f["geography"] == geography]
    if segment:
        f = f[f["segment"] == segment]

    # Сортировка
    desc = sort.startswith("-")
    key = sort.lstrip("-")
    sort_col = {"score": "churn_score", "name": "full_name", "segment": "segment"}[key]
    f = f.sort_values(sort_col, ascending=not desc)

    total = len(f)
    page = f.iloc[offset:offset + limit]

    return {
        "total": int(total),
        "returned": int(len(page)),
        "mode": mode,
        "items": page.to_dict(orient="records"),
    }


@app.get("/clients/{client_id}", response_model=ClientCardOut, tags=["clients"])
def client_card(client_id: int):
    """Карточка клиента: профиль + скор + причины + оффер."""
    df = _df()
    row = df[df["client_id"] == client_id]
    if row.empty:
        raise HTTPException(404, f"Клиент {client_id} не найден или уже ушёл")
    return row.iloc[0].to_dict()


@app.get(
    "/clients/{client_id}/transactions",
    response_model=TransactionsResponse,
    tags=["clients"],
)
def client_transactions(client_id: int, n_days: int = Query(90, ge=1, le=365)):
    """История транзакций клиента (для графика активности на карточке)."""
    df = _df()
    if df[df["client_id"] == client_id].empty:
        raise HTTPException(404, f"Клиент {client_id} не найден")
    items = load_transactions(client_id, n_days=n_days)
    return {
        "client_id": int(client_id),
        "n_days": int(n_days),
        "n_transactions": len(items),
        "items": items,
    }


# ---------------------------------------------------------------------------
# Offers (для отладки)
# ---------------------------------------------------------------------------
@app.get("/offers/templates", tags=["offers"])
def offers_templates():
    """Список всех шаблонов офферов в системе."""
    return {"templates": list_templates()}
