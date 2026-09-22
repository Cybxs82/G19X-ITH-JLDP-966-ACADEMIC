from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import create_router
from backend.config import get_settings
from backend.database import check_database_connection
from backend.repository import repository
from backend.schemas import HealthResponse

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