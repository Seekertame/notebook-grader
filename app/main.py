import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.endpoints.assignments import router as assignments_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.submissions import router as submissions_router
from app.api.endpoints.template import router as template_router
from app.core.rate_limit import limiter

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
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS or ["*"],
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


@app.get("/")
def index():
    return FileResponse("templates/index.html")


@app.get("/dashboard")
def dashboard():
    return FileResponse("templates/dashboard.html")


@app.get("/assignment/{assignment_id}")
def assignment_page(assignment_id: int):
    return FileResponse("templates/assignment.html")
