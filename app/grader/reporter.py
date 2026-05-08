import csv
import io

from app.models.schemas import StudentWorkResult
from app.utils.grading import calculate_grade


def generate_csv_report(
    results: list[StudentWorkResult], max_total_score: int
) -> bytes:
    task_codes: list[str] = []
    seen: set[str] = set()
    for result in results:
        for tr in result.task_results:
            if tr.task_code not in seen:
                seen.add(tr.task_code)
                task_codes.append(tr.task_code)

    header = ["ФИО", "Группа"]
    for code in task_codes:
        header.append(code)
    header.append("Итоговый балл")
    header.append("Оценка")
    header.append("Статус проверки")

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(header)

    for result in results:
        task_map = {tr.task_code: tr for tr in result.task_results}

        row: list[str] = [
            result.student.fio,
            result.student.group,
        ]

        statuses = []
        for code in task_codes:
            tr = task_map.get(code)
            if tr:
                row.append(str(tr.awarded_points))
                if tr.status != "успешно":
                    detail = f"{code}: {tr.status}"
                    if tr.explanation:
                        detail += f" ({tr.explanation})"
                    statuses.append(detail)
            else:
                row.append("0")
                statuses.append(f"{code}: не найдена")

        row.append(str(result.total_score))
        row.append(str(calculate_grade(result.total_score, max_total_score)))
        row.append("; ".join(statuses) if statuses else "успешно")

        writer.writerow(row)

    return ("﻿" + buf.getvalue()).encode("utf-8")
