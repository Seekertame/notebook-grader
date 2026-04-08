from pathlib import Path

import nbformat

from app.grader.parser import parse_notebook


def _make_notebook(tmp_path: Path) -> Path:
    nb = nbformat.v4.new_notebook()

    # Markdown cell with student info
    nb.cells.append(
        nbformat.v4.new_markdown_cell(
            "<!-- STUDENT_INFO -->\n"
            "ФИО: Иванов Иван Иванович\n"
            "Группа: БПИ-101"
        )
    )

    # Regular code cell (no task tag)
    nb.cells.append(nbformat.v4.new_code_cell("import pandas as pd"))

    # Task A1
    cell_a1 = nbformat.v4.new_code_cell("x = 2 + 2\nprint(x)")
    cell_a1.metadata["tags"] = ["task:A1"]
    nb.cells.append(cell_a1)

    # Task B2
    cell_b2 = nbformat.v4.new_code_cell("result = [i**2 for i in range(10)]")
    cell_b2.metadata["tags"] = ["task:B2", "optional"]
    nb.cells.append(cell_b2)

    path = tmp_path / "homework.ipynb"
    nbformat.write(nb, str(path))
    return path


def test_parse_student_info(tmp_path: Path):
    path = _make_notebook(tmp_path)
    result = parse_notebook(path)

    assert result.student.fio == "Иванов Иван Иванович"
    assert result.student.group == "БПИ-101"


def test_parse_tasks(tmp_path: Path):
    path = _make_notebook(tmp_path)
    result = parse_notebook(path)

    assert len(result.tasks) == 2
    assert result.tasks[0].task_code == "A1"
    assert "x = 2 + 2" in result.tasks[0].source
    assert result.tasks[1].task_code == "B2"


def test_missing_student_marker(tmp_path: Path):
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("x = 1"))
    path = tmp_path / "no_marker.ipynb"
    nbformat.write(nb, str(path))

    result = parse_notebook(path)
    assert result.student is None


def test_missing_group(tmp_path: Path):
    nb = nbformat.v4.new_notebook()
    nb.cells.append(
        nbformat.v4.new_markdown_cell(
            "<!-- STUDENT_INFO -->\nФИО: Иванов"
        )
    )
    path = tmp_path / "missing_group.ipynb"
    nbformat.write(nb, str(path))

    result = parse_notebook(path)
    assert result.student.fio == "Иванов"
    assert result.student.group == ""


def test_no_tasks(tmp_path: Path):
    nb = nbformat.v4.new_notebook()
    nb.cells.append(
        nbformat.v4.new_markdown_cell(
            "<!-- STUDENT_INFO -->\nФИО: Тест\nГруппа: Г-1"
        )
    )
    nb.cells.append(nbformat.v4.new_code_cell("pass"))
    path = tmp_path / "no_tasks.ipynb"
    nbformat.write(nb, str(path))

    result = parse_notebook(path)
    assert result.tasks == []


def test_markdown_bold_formatting(tmp_path: Path):
    """Student uses **bold** markdown around labels."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(
        nbformat.v4.new_markdown_cell(
            "<!-- STUDENT_INFO -->\n"
            "**ФИО:** Петров Петр Петрович\n"
            "**Группа:** БПИ-248"
        )
    )
    path = tmp_path / "bold.ipynb"
    nbformat.write(nb, str(path))

    result = parse_notebook(path)
    assert result.student.fio == "Петров Петр Петрович"
    assert result.student.group == "БПИ-248"


def test_single_line(tmp_path: Path):
    """All info on one line."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(
        nbformat.v4.new_markdown_cell(
            "<!-- STUDENT_INFO --> **ФИО:** Сидоров Сидор **Группа:** БПИ-100"
        )
    )
    path = tmp_path / "single_line.ipynb"
    nbformat.write(nb, str(path))

    result = parse_notebook(path)
    assert result.student.fio == "Сидоров Сидор"
    assert result.student.group == "БПИ-100"


def test_underscore_italic_formatting(tmp_path: Path):
    """Student uses _italic_ markdown."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(
        nbformat.v4.new_markdown_cell(
            "<!-- STUDENT_INFO -->\n"
            "_ФИО_: _Козлова Анна Сергеевна_\n"
            "_Группа_: _МПИ-201_"
        )
    )
    path = tmp_path / "italic.ipynb"
    nbformat.write(nb, str(path))

    result = parse_notebook(path)
    assert result.student.fio == "Козлова Анна Сергеевна"
    assert result.student.group == "МПИ-201"


def test_extra_spaces_around_colon(tmp_path: Path):
    """Spaces before/after colon."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(
        nbformat.v4.new_markdown_cell(
            "<!-- STUDENT_INFO -->\n"
            "ФИО :   Иванов Иван  \n"
            "Группа :  БПИ-101  "
        )
    )
    path = tmp_path / "spaces.ipynb"
    nbformat.write(nb, str(path))

    result = parse_notebook(path)
    assert result.student.fio == "Иванов Иван"
    assert result.student.group == "БПИ-101"


def test_setup_code_single_cell(tmp_path: Path):
    """A single cell tagged 'setup' is extracted into setup_code."""
    nb = nbformat.v4.new_notebook()

    setup = nbformat.v4.new_code_cell("import numpy as np\nimport pandas as pd")
    setup.metadata["tags"] = ["setup"]
    nb.cells.append(setup)

    task = nbformat.v4.new_code_cell("print(np.pi)")
    task.metadata["tags"] = ["task:A1"]
    nb.cells.append(task)

    path = tmp_path / "with_setup.ipynb"
    nbformat.write(nb, str(path))

    result = parse_notebook(path)
    assert "import numpy as np" in result.setup_code
    assert "import pandas as pd" in result.setup_code
    assert len(result.tasks) == 1


def test_setup_code_multiple_cells(tmp_path: Path):
    """Multiple setup cells are concatenated."""
    nb = nbformat.v4.new_notebook()

    s1 = nbformat.v4.new_code_cell("import os")
    s1.metadata["tags"] = ["setup"]
    nb.cells.append(s1)

    s2 = nbformat.v4.new_code_cell("import sys")
    s2.metadata["tags"] = ["setup"]
    nb.cells.append(s2)

    path = tmp_path / "multi_setup.ipynb"
    nbformat.write(nb, str(path))

    result = parse_notebook(path)
    assert "import os" in result.setup_code
    assert "import sys" in result.setup_code


def test_setup_code_absent(tmp_path: Path):
    """No setup tag means setup_code is empty."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("x = 1"))

    path = tmp_path / "no_setup.ipynb"
    nbformat.write(nb, str(path))

    result = parse_notebook(path)
    assert result.setup_code == ""
