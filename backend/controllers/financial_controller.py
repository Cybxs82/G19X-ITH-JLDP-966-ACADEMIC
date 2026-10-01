from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, Request, Response, UploadFile

from ..models.schemas import (
    AlertResponse,
    AlertSeverity,
    AlertStatus,
    AlertUpdate,
    AuthResponse,
    AuthUserResponse,
    ProfileUpdateRequest,
    DashboardResponse,
    FeedbackCreate,
    FeedbackResponse,
    ForecastResponse,
    IngestionResponse,
    KpiResponse,
    RecommendationResponse,
    RegisterRequest,
    LoginRequest,
    SyncCreate,
    SyncResponse,
)
from ..repositories.financial_repository import PostgreSQLRepository
from ..services.ingestion_service import ingest_erp_document, ingest_file
from ..services.auth_service import SESSION_COOKIE, authenticate_user, get_session_user, register_user, revoke_session, update_profile


def create_router(repository: PostgreSQLRepository) -> APIRouter:
    router = APIRouter()

    @router.post("/auth/register", response_model=AuthResponse, status_code=201)
    def register(payload: RegisterRequest, response: Response) -> AuthResponse:
        try:
            user = register_user(payload.email, payload.full_name, payload.password)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return AuthResponse(user=AuthUserResponse(**user))

    @router.post("/auth/login", response_model=AuthResponse)
    def login(payload: LoginRequest, request: Request, response: Response) -> AuthResponse:
        try:
            user, token = authenticate_user(
                payload.email,
                payload.password,
                request.headers.get("user-agent"),
                request.client.host if request.client else None,
            )
        except ValueError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=60 * 60 * 24 * 7,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/",
        )
        return AuthResponse(user=AuthUserResponse(**user))

    @router.get("/auth/session", response_model=AuthResponse)
    def session(request: Request) -> AuthResponse:
        user = get_session_user(request.cookies.get(SESSION_COOKIE))
        if user is None:
            raise HTTPException(status_code=401, detail="Sesión no iniciada")
        return AuthResponse(user=AuthUserResponse(**user))

    @router.patch("/auth/profile", response_model=AuthResponse)
    def profile(payload: ProfileUpdateRequest, request: Request) -> AuthResponse:
        user = get_session_user(request.cookies.get(SESSION_COOKIE))
        if user is None:
            raise HTTPException(status_code=401, detail="Sesión no iniciada")
        try:
            updated = update_profile(
                UUID(str(user["id"])),
                payload.email,
                payload.full_name,
                payload.username,
                payload.phone,
                payload.current_password,
                payload.new_password,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return AuthResponse(user=AuthUserResponse(**updated))

    @router.post("/auth/logout", status_code=204)
    def logout(request: Request, response: Response) -> Response:
        revoke_session(request.cookies.get(SESSION_COOKIE))
        response.delete_cookie(SESSION_COOKIE, path="/")
        response.status_code = 204
        return response

    @router.get("/kpis", response_model=List[KpiResponse])
    def get_kpis(period_from: Optional[date] = None, period_to: Optional[date] = None) -> List[KpiResponse]:
        return repository.list_kpis(period_from, period_to)

    @router.get("/forecast", response_model=ForecastResponse)
    def get_forecast(days: int = Query(default=90, ge=30, le=90)) -> ForecastResponse:
        if days not in (30, 60, 90):
            raise HTTPException(status_code=422, detail="days debe ser 30, 60 o 90")
        return repository.forecast(days)

    @router.get("/alerts", response_model=List[AlertResponse])
    def get_alerts(status: Optional[AlertStatus] = None, severity: Optional[AlertSeverity] = None) -> List[AlertResponse]:
        return repository.list_alerts(status, severity)

    @router.patch("/alerts/{alert_id}", response_model=AlertResponse)
    def update_alert(alert_id: int, payload: AlertUpdate) -> AlertResponse:
        alert = repository.update_alert(alert_id, payload.status, payload.comment, payload.attended_by)
        if alert is None:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")
        return alert

    @router.get("/recommendations", response_model=List[RecommendationResponse])
    def get_recommendations(period: Optional[date] = None) -> List[RecommendationResponse]:
        return repository.list_recommendations(period)

    @router.post("/feedback", response_model=FeedbackResponse, status_code=201)
    def create_feedback(payload: FeedbackCreate) -> FeedbackResponse:
        return repository.create_feedback(payload)

    @router.post("/sync", response_model=SyncResponse, status_code=202)
    def create_sync(payload: SyncCreate) -> SyncResponse:
        return repository.create_sync(payload.data_source_id)

    @router.post("/ingestion/files", response_model=IngestionResponse, status_code=202)
    async def ingest_financial_file(file: UploadFile = File(...), source_type: str = Query(default="erp")) -> IngestionResponse:
        if source_type not in {"erp", "banco"}:
            raise HTTPException(status_code=422, detail="source_type debe ser erp o banco")
        try:
            result = ingest_file(file.filename or "financial-file", await file.read(), source_type)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return IngestionResponse(**result)

    @router.post("/ingestion/documents", response_model=IngestionResponse, status_code=202)
    async def ingest_erp_document_route(request: Request, file: UploadFile = File(...)) -> IngestionResponse:
        if get_session_user(request.cookies.get(SESSION_COOKIE)) is None:
            raise HTTPException(status_code=401, detail="Sesión no iniciada")
        file_name = Path(file.filename or "").name
        if not file_name:
            raise HTTPException(status_code=422, detail="El archivo debe tener un nombre")
        if Path(file_name).suffix.lower() not in {".pdf", ".csv", ".xlsx", ".xlsm"}:
            raise HTTPException(status_code=415, detail="Usa un archivo PDF, CSV o Excel (.xlsx, .xlsm)")
        content = await file.read(20 * 1024 * 1024 + 1)
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="El archivo supera el límite de 20 MB")
        if not content:
            raise HTTPException(status_code=422, detail="El archivo está vacío")
        try:
            result = ingest_erp_document(file_name, content)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return IngestionResponse(**result)

    @router.get("/dashboard", response_model=DashboardResponse)
    def get_dashboard(
        period_from: Optional[date] = None,
        period_to: Optional[date] = None,
        cost_center_id: Optional[int] = Query(default=None, gt=0),
    ) -> DashboardResponse:
        end = period_to or date.today()
        start = period_from or end - timedelta(days=365)
        if start > end:
            raise HTTPException(status_code=422, detail="period_from no puede ser posterior a period_to")
        return DashboardResponse(
            period_from=start,
            period_to=end,
            last_sync=repository.last_sync,
            kpis=repository.list_kpis(start, end, cost_center_id),
            forecast=repository.forecast(90),
            alerts=repository.list_alerts(cost_center_id=cost_center_id),
            recommendations=repository.list_recommendations(),
        )

    return router
