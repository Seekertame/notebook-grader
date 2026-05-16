import logging
import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.endpoints.assignments import router as assignments_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.submissions import router as submissions_router
from app.api.endpoints.template import router as template_router
from app.core.database import get_db
from app.core.rate_limit import limiter


HEALTHCHECK_PATHS = frozenset({"/healthz", "/readyz"})


class TrustedHostMiddlewareWithExcludes:
    """TrustedHostMiddleware с whitelist путей, обходящих проверку Host header."""

    def __init__(self, app: ASGIApp, allowed_hosts: list[str], excluded_paths: frozenset[str]):
        self._app = app
        self._excluded_paths = excluded_paths
        self._guarded = TrustedHostMiddleware(app, allowed_hosts=allowed_hosts)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path") in self._excluded_paths:
            await self._app(scope, receive, send)
            return
        await self._guarded(scope, receive, send)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def _split_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


ENVIRONMENT = os.getenv("NBGRADER_ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"

ALLOWED_HOSTS = _split_csv_env("NBGRADER_ALLOWED_HOSTS")
CORS_ORIGINS = _split_csv_env("NBGRADER_CORS_ORIGINS")

if IS_PRODUCTION:
    if not ALLOWED_HOSTS:
        raise RuntimeError(
            "NBGRADER_ALLOWED_HOSTS must be set in production "
            "(comma-separated list of hostnames)"
        )
    if not CORS_ORIGINS:
        raise RuntimeError(
            "NBGRADER_CORS_ORIGINS must be set in production "
            "(comma-separated list of allowed origins)"
        )

_fastapi_kwargs: dict = {"title": "Notebook Grader API"}
if IS_PRODUCTION:
    _fastapi_kwargs.update(docs_url=None, redoc_url=None, openapi_url=None)

app = FastAPI(**_fastapi_kwargs)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    TrustedHostMiddlewareWithExcludes,
    allowed_hosts=ALLOWED_HOSTS or ["*"],
    excluded_paths=HEALTHCHECK_PATHS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(assignments_router, prefix="/api/v1", tags=["assignments"])
app.include_router(submissions_router, prefix="/api/v1", tags=["submissions"])
app.include_router(template_router, prefix="/api/v1", tags=["template"])


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="db unavailable")
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse("templates/index.html")


@app.get("/dashboard")
def dashboard():
    return FileResponse("templates/dashboard.html")


@app.get("/assignment/{assignment_id}")
def assignment_page(assignment_id: int):
    return FileResponse("templates/assignment.html")
