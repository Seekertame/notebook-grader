import re
from pathlib import Path

import nbformat

from app.models.schemas import ParsedNotebook, StudentInfo, TaskCell

_MARKER_RE = re.compile(r"<!--\s*STUDENT[\s_-]*INFO\s*-->", re.IGNORECASE)

_TASK_TAG_RE = re.compile(r"^task:(.+)$")


def _strip_markdown(text: str) -> str:
    """Remove markdown bold/italic markers (* and _) and strip whitespace."""
    return re.sub(r"[*_]", "", text).strip()


def _normalize_source(cell) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        source = "".join(source)
    return source.replace("\r\n", "\n")


def _extract_student_info(nb: nbformat.NotebookNode) -> StudentInfo | None:
    for cell in nb.cells:
        if cell.cell_type != "markdown":
            continue
        source = _normalize_source(cell)
        if not _MARKER_RE.search(source):
            continue

        clean = _strip_markdown(source)
        flat = clean.replace("\n", " ")

        fio_match = re.search(
            r"ФИО\s*:\s*(.+?)(?=\s*Группа\s*:|$)",
            flat,
            re.IGNORECASE,
        )
        fio = fio_match.group(1).strip() if fio_match else ""

        group_match = re.search(
            r"Группа\s*:\s*(.+)",
            flat,
            re.IGNORECASE,
        )
        group = group_match.group(1).strip() if group_match else ""

        return StudentInfo(fio=fio, group=group)

    return None


def _extract_setup_code(nb: nbformat.NotebookNode) -> str:
    parts: list[str] = []
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        tags: list[str] = cell.metadata.get("tags", [])
        if "setup" in tags:
            parts.append(_normalize_source(cell))
    return "\n".join(parts)


def _extract_tasks(nb: nbformat.NotebookNode) -> list[TaskCell]:
    tasks: list[TaskCell] = []
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        tags: list[str] = cell.metadata.get("tags", [])
        for tag in tags:
            m = _TASK_TAG_RE.match(tag)
            if m:
                tasks.append(TaskCell(task_code=m.group(1), source=cell.source))
    return tasks


def parse_notebook(path: str | Path) -> ParsedNotebook:
    nb = nbformat.read(str(path), as_version=4)
    student = _extract_student_info(nb)
    setup_code = _extract_setup_code(nb)
    tasks = _extract_tasks(nb)
    return ParsedNotebook(student=student, tasks=tasks, setup_code=setup_code)


def parse_notebook_bytes(data: bytes) -> ParsedNotebook:
    import io

    nb = nbformat.read(io.BytesIO(data), as_version=4)
    student = _extract_student_info(nb)
    setup_code = _extract_setup_code(nb)
    tasks = _extract_tasks(nb)
    return ParsedNotebook(student=student, tasks=tasks, setup_code=setup_code)
