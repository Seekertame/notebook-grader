import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.endpoints.assignments import router as assignments_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.submissions import router as submissions_router
from app.api.endpoints.template import router as template_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Notebook Grader API")

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