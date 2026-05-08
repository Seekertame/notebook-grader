from decimal import ROUND_HALF_UP, Decimal


def calculate_grade(total_score: int, max_total_score: int) -> int:
    if max_total_score <= 0:
        return 0
    raw = Decimal(total_score) * 10 / Decimal(max_total_score)
    grade = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return max(0, min(10, grade))
