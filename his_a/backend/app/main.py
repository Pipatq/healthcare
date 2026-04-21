"""HIS A Backend – entry point for the Doctor's FHIR client application."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.db.database import close_pool, create_pool
from app.api.routes.auth import router as auth_router
from app.api.routes.fhir_proxy import router as fhir_router
from app.api.routes.fhir_proxy import startup_client, shutdown_client


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("HIS A Backend starting – Gateway target: {}", settings.GATEWAY_BASE_URL)
    await create_pool()
    await startup_client()
    yield
    await shutdown_client()
    await close_pool()
    logger.info("HIS A Backend shut down.")


_docs_url = None if settings.ENV == "prod" else "/docs"
_redoc_url = None if settings.ENV == "prod" else "/redoc"

app = FastAPI(
    title="HIS A – FHIR Client Backend",
    description="Authentication + FHIR proxy for HIS A (Requesting System).",
    version="1.0.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(fhir_router, prefix="/api/v1")

Instrumentator().instrument(app).expose(app)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"service": "his_a_backend", "status": "ok"}
