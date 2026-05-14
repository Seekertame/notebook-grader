"""Разовый генератор файла notebook_grader_template.ipynb.

Запускается, когда нужно пересобрать статический шаблон:
    python -m app.assets._generate_template
"""
from pathlib import Path

import nbformat as nbf


def build_notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()

    student_cell = nbf.v4.new_markdown_cell(
        "<!-- STUDENT_INFO -->\n"
        "**ФИО:** Иванов Иван Иванович\n"
        "**Группа:** БПИ241"
    )

    intro_cell = nbf.v4.new_markdown_cell(
        "## Инструкция\n"
        "\n"
        "Это шаблон для выполнения задания в системе **Notebook Grader**.\n"
        "\n"
        "- Заполните ячейку выше своими ФИО и группой. Строку "
        "`<!-- STUDENT_INFO -->` удалять нельзя — по ней сервер находит "
        "вашу анкету. Никакого другого текста в этой ячейке быть не должно.\n"
        "- Решение каждой задачи пишите **только** в ячейке с тегом "
        "`task:<код>` (теги уже проставлены ниже). Не удаляйте теги — "
        "без них сервер не найдёт вашу задачу и поставит 0 баллов.\n"
        "- Ячейка с тегом `setup` выполняется **перед каждой** задачей: "
        "импорты и общие переменные пишите туда.\n"
        "- Можно добавлять собственные ячейки между задачами для черновых "
        "расчётов — они не повлияют на проверку.\n"
        "- Перед сдачей убедитесь, что коды задач (`task:1`, `task:2`, ...) "
        "совпадают с теми, что указал преподаватель."
    )

    setup_cell = nbf.v4.new_code_cell(
        "# Общие импорты выполняются перед каждой задачей.\n"
        "import numpy as np\n"
        "import pandas as pd\n"
    )
    setup_cell.metadata["tags"] = ["setup"]

    task1_cell = nbf.v4.new_code_cell(
        "# Задача 1 — проверка по правильному ответу.\n"
        "# Решение должно выводить ответ через print(...).\n"
        "# Сравнивается stdout с ожидаемым значением.\n"
        "result = 2 + 2\n"
        "print(result)\n"
    )
    task1_cell.metadata["tags"] = ["task:1"]

    task2_cell = nbf.v4.new_code_cell(
        "# Задача 2 — проверка по набору тестов.\n"
        "# Программа читает входные данные из stdin (input()) и печатает\n"
        "# результат в stdout (print). Каждый тест-кейс запускается отдельно.\n"
        "n = int(input())\n"
        "print(n * n)\n"
    )
    task2_cell.metadata["tags"] = ["task:2"]

    task3_cell = nbf.v4.new_code_cell(
        "# Задача 3 — машинное сравнение (reference_assert).\n"
        "# Преподаватель допишет проверочный код в конец ячейки.\n"
        "# Завершение без исключений → полный балл,\n"
        "# любое исключение (включая AssertionError) → 0 баллов.\n"
        "def solve(x):\n"
        "    return x * 2\n"
    )
    task3_cell.metadata["tags"] = ["task:3"]

    reminder_cell = nbf.v4.new_markdown_cell(
        "---\n"
        "\n"
        "**Напоминание.** Коды задач (`task:1`, `task:2`, `task:3`, ...) "
        "должны точно совпадать с кодами задач в карточке задания на сервере. "
        "Если преподаватель завёл задачи с кодами `A1`, `A2`, `A3` — "
        "переименуйте теги соответственно (например, `task:A1`)."
    )

    nb.cells = [
        student_cell,
        intro_cell,
        setup_cell,
        task1_cell,
        task2_cell,
        task3_cell,
        reminder_cell,
    ]
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata["language_info"] = {"name": "python", "pygments_lexer": "ipython3"}
    return nb


if __name__ == "__main__":
    out = Path(__file__).parent / "notebook_grader_template.ipynb"
    with out.open("w", encoding="utf-8") as f:
        nbf.write(build_notebook(), f)
    print(f"wrote {out}")
