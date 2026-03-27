"""Data Palestine API: FastAPI application entry point."""

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import asyncpg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter by client IP."""

    def __init__(self, app, max_per_minute: int = 100):
        super().__init__(app)
        self.max_per_minute = max_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60

        # Clean old entries and count recent requests
        recent = [t for t in self._requests[client_ip] if t > window_start]
        self._requests[client_ip] = recent

        if len(recent) >= self.max_per_minute:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMITED", "message": "Too many requests. Limit: {}/minute.".format(self.max_per_minute)}},
                headers={"Retry-After": "60"},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and teardown the asyncpg connection pool."""
    # asyncpg uses the standard postgres:// scheme
    dsn = settings.database_url_sync  # postgresql://datapal:...@localhost/datapalestine
    app.state.pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    yield
    await app.state.pool.close()


app = FastAPI(
    title="Data Palestine API",
    description=(
        "Open data API for Palestinian statistical, humanitarian, "
        "and socioeconomic data. Free, transparent, and accessible."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
_cors_origins = (
    ["*"] if settings.environment == "development"
    else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Rate limiting
app.add_middleware(RateLimitMiddleware, max_per_minute=settings.rate_limit_per_minute)


@app.get("/health")
async def health_check(request: Request) -> dict:
    """Health check endpoint."""
    async with request.app.state.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) as n FROM observations")
        obs_count = row["n"]
    return {"status": "ok", "observations": obs_count, "environment": settings.environment}


# Error handler for consistent error envelope
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "NOT_FOUND", "message": str(exc.detail)}},
    )


# Import and register routers
from app.routers import datasets, indicators, observations, geographies, sources, export, curation  # noqa: E402

app.include_router(datasets.router, prefix="/api/v1", tags=["Datasets"])
app.include_router(indicators.router, prefix="/api/v1", tags=["Indicators"])
app.include_router(observations.router, prefix="/api/v1", tags=["Observations"])
app.include_router(geographies.router, prefix="/api/v1", tags=["Geographies"])
app.include_router(sources.router, prefix="/api/v1", tags=["Sources"])
app.include_router(export.router, prefix="/api/v1", tags=["Export"])
app.include_router(curation.router, prefix="/api/v1", tags=["Curation"])
