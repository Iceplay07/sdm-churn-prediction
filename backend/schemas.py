"""Pydantic-модели для FastAPI. Все raw-фичи опциональны — predict.py заполнит дефолты."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict

ModeEnum = Literal["balanced", "high_precision", "high_recall"]
RiskLevel = Literal["low", "medium", "high"]


class ClientFeaturesIn(BaseModel):
    """Входной DTO для /predict. Все 29 raw-фич + client_id, всё опционально."""
    model_config = ConfigDict(extra="allow")  # допускаем engineered-фичи если фронт пришлёт

    client_id: Optional[int] = None

    age: Optional[int] = Field(default=None, ge=0, le=120)
    gender: Optional[Literal["M", "F"]] = None
    geography: Optional[str] = None
    tenure_years: Optional[int] = Field(default=None, ge=0, le=50)
    credit_score: Optional[int] = Field(default=None, ge=0, le=1000)
    salary_monthly_rub: Optional[int] = Field(default=None, ge=0)
    balance_rub: Optional[int] = None
    n_products: Optional[int] = Field(default=None, ge=0, le=10)
    has_credit_card: Optional[int] = Field(default=None, ge=0, le=1)
    is_active_member: Optional[int] = Field(default=None, ge=0, le=1)

    tx_count_90d: Optional[float] = None
    turnover_outflow_90d: Optional[float] = None
    tx_count_30d: Optional[float] = None
    turnover_outflow_30d: Optional[float] = None
    turnover_outflow_60d_prev: Optional[float] = None
    days_since_last_tx: Optional[int] = None

    inflow_30d: Optional[float] = None
    inflow_60d_prev: Optional[float] = None

    sessions_30d: Optional[float] = None
    sessions_60d_prev: Optional[float] = None
    days_since_last_login: Optional[int] = None

    unsubscribe_count_90d: Optional[float] = None
    support_tickets_30d: Optional[float] = None
    push_received_90d: Optional[float] = None
    push_opened_90d: Optional[float] = None

    turnover_drop_30d_vs_60d_pct: Optional[float] = None
    sessions_drop_30d_vs_60d_pct: Optional[float] = None
    push_open_rate_90d: Optional[float] = None
    inflow_drop_pct: Optional[float] = None


class TopFactor(BaseModel):
    feature: str
    value: float | str
    impact: float
    direction: Literal["+", "-"]


class PredictionOut(BaseModel):
    client_id: Optional[int] = None
    churn_score: float
    churn_probability_pct: int
    is_at_risk: bool
    risk_level: RiskLevel
    top_factors: list[TopFactor]
    threshold_mode: ModeEnum
    threshold_value: float


class BatchIn(BaseModel):
    rows: list[ClientFeaturesIn]


class BatchOut(BaseModel):
    items: list[PredictionOut]


class OfferOut(BaseModel):
    id: str
    title: str
    reason: str
    estimated_lift: float
    cta: str


class ClientCardOut(BaseModel):
    client_id: int
    full_name: str
    age: int
    gender: Optional[str] = None
    geography: str
    tenure_years: int
    n_products: int
    balance_rub: int
    salary_monthly_rub: int
    is_active_member: int
    churn_score: float
    churn_probability_pct: int
    risk_level: RiskLevel
    is_at_risk: bool
    top_factors: list[TopFactor]
    offer: Optional[OfferOut] = None


class AtRiskListOut(BaseModel):
    total: int
    returned: int
    mode: ModeEnum
    items: list[ClientCardOut]


class TransactionOut(BaseModel):
    date: str
    amount_rub: float
    category: str


class TransactionsResponse(BaseModel):
    client_id: int
    n_days: int
    n_transactions: int
    items: list[TransactionOut]
