from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    cfo = "cfo"
    analista = "analista"
    administrador = "administrador"


class AlertStatus(str, Enum):
    nueva = "nueva"
    en_revision = "en_revision"
    cerrada = "cerrada"
    falsa = "falsa"


class AlertSeverity(str, Enum):
    baja = "baja"
    media = "media"
    alta = "alta"


class FeedbackType(str, Enum):
    util = "util"
    no_util = "no_util"


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    database: str
    database_error: Optional[str] = None


class KpiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    category: str
    value: Decimal
    period: date
    cost_center_id: Optional[int] = None
    change_pct: Optional[Decimal] = None


class ForecastPointResponse(BaseModel):
    target_date: date
    predicted_value: Decimal
    lower_bound: Optional[Decimal] = None
    upper_bound: Optional[Decimal] = None


class ForecastResponse(BaseModel):
    forecast_run_id: int
    model_name: str
    generated_at: datetime
    horizon_days: int
    values: List[ForecastPointResponse]


class AlertResponse(BaseModel):
    id: int
    account_id: int
    cost_center_id: Optional[int] = None
    period: date
    budgeted_amount: Decimal
    actual_amount: Decimal
    deviation_pct: Decimal
    severity: AlertSeverity
    status: AlertStatus
    detected_at: datetime
    responsible_id: Optional[UUID] = None
    attended_by: Optional[UUID] = None
    attended_at: Optional[datetime] = None
    comment: Optional[str] = None


class AlertUpdate(BaseModel):
    status: AlertStatus
    comment: Optional[str] = Field(default=None, max_length=2000)
    attended_by: Optional[UUID] = None
    responsible_id: Optional[UUID] = None


class RecommendationResponse(BaseModel):
    id: int
    user_id: Optional[UUID] = None
    period: date
    situation: str
    impact: Optional[str] = None
    recommendation_text: str
    priority: str
    evidence: Optional[dict] = None
    prompt_version: str
    generated_text: str
    model_name: str
    generated_at: datetime


class FeedbackCreate(BaseModel):
    recommendation_id: int
    user_id: UUID
    feedback: FeedbackType
    comment: Optional[str] = Field(default=None, max_length=2000)


class FeedbackResponse(FeedbackCreate):
    id: int
    created_at: datetime


class SyncCreate(BaseModel):
    data_source_id: int = Field(gt=0)


class SyncResponse(BaseModel):
    id: int
    data_source_id: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    rows_ingested: int = 0


class IngestionResponse(BaseModel):
    sync_log_id: int
    data_source_id: int
    rows_ingested: int
    rows_rejected: int = 0
    status: str


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class AuthUserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool


class AuthResponse(BaseModel):
    user: AuthUserResponse


class DashboardResponse(BaseModel):
    period_from: date
    period_to: date
    last_sync: Optional[datetime]
    kpis: List[KpiResponse]
    forecast: ForecastResponse
    alerts: List[AlertResponse]
    recommendations: List[RecommendationResponse]
