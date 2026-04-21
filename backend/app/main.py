from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import close_pool, create_pool
from app.api.routes import auth, fhir


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await create_pool()
    yield
    await close_pool()


# Disable interactive docs in production to reduce attack surface.
_docs_url = None if settings.ENV == "prod" else "/docs"
_redoc_url = None if settings.ENV == "prod" else "/redoc"

app = FastAPI(
    title="HIS-HIS FHIR Integration API",
    version="1.0.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — origins are read from the ALLOWED_ORIGINS environment variable.
# Never allow wildcard "*" in production; provide an explicit list.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/v1")
app.include_router(fhir.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
