from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.security import get_current_teacher
from app.models.domain import Teacher

router = APIRouter(prefix="/template", tags=["template"])

_TEMPLATE_PATH = (
        Path(__file__).resolve().parents[2]
        / "assets"
        / "notebook_grader_template.ipynb"
)
_TEMPLATE_FILENAME = "notebook_grader_template.ipynb"


@router.get("/download")
def download_template(
        _current_teacher: Teacher = Depends(get_current_teacher),
):
    if not _TEMPLATE_PATH.is_file():
        raise HTTPException(status_code=500, detail="Template asset is missing")
    return FileResponse(
        path=_TEMPLATE_PATH,
        media_type="application/x-ipynb+json",
        filename=_TEMPLATE_FILENAME,
    )
