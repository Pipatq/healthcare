"""HIS B FHIR Facade – maps legacy HIS B database to HL7 FHIR R5 resources."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.db.database import close_pool, create_pool
from app.api.routes import fhir


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("HIS B Facade starting – connecting to legacy database…")
    await create_pool()
    logger.info("Database pool ready.")
    yield
    await close_pool()
    logger.info("HIS B Facade shut down.")


_docs_url = None if settings.ENV == "prod" else "/docs"
_redoc_url = None if settings.ENV == "prod" else "/redoc"

app = FastAPI(
    title="HIS B – FHIR Facade (Data Provider)",
    description="Exposes legacy HIS B data as HL7 FHIR R5 resources.",
    version="1.0.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Internal service – gateway is the public face
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fhir.router, prefix="/fhir")

# Prometheus metrics at /metrics
Instrumentator().instrument(app).expose(app)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"service": "his_b_facade", "status": "ok"}
