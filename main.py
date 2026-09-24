from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.controllers.financial_controller import create_router
from backend.infrastructure.config import get_settings
from backend.infrastructure.database import check_database_connection
from backend.models.schemas import HealthResponse
from backend.repositories.financial_repository import repository

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", description="API de inteligencia financiera para CFO")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["system"])
def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs", "api": settings.api_prefix}


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    database_connected, database_error = check_database_connection()
    return HealthResponse(
        status="ok" if database_connected else "degraded",
        service=settings.app_name,
        environment=settings.environment,
        database="connected" if database_connected else "unavailable",
        database_error=database_error,
    )


app.include_router(create_router(repository), prefix=settings.api_prefix, tags=["financial"])