"""FHIR Interoperability Gateway – routes FHIR requests from HIS A to HIS B."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.api.routes.proxy import router as proxy_router, startup_client, shutdown_client


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("FHIR Gateway starting – HIS B target: {}", settings.HIS_B_BASE_URL)
    await startup_client()
    yield
    await shutdown_client()
    logger.info("FHIR Gateway shut down.")


_docs_url = None if settings.ENV == "prod" else "/docs"
_redoc_url = None if settings.ENV == "prod" else "/redoc"

app = FastAPI(
    title="FHIR Interoperability Gateway",
    description="Validates and routes FHIR requests from HIS A to HIS B.",
    version="1.0.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    lifespan=lifespan,
)

app.include_router(proxy_router)

Instrumentator().instrument(app).expose(app)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"service": "fhir_gateway", "status": "ok", "his_b_target": settings.HIS_B_BASE_URL}
