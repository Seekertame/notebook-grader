import pytest

from app.utils.csv_safety import escape_csv_value


@pytest.mark.parametrize(
    "value",
    [
        "=cmd|'/C calc'!A0",
        "+1+1",
        "-2+3",
        "@SUM(1+1)",
        "\tмалicious",
        "\rmalicious",
    ],
)
def test_dangerous_prefixes_are_escaped(value):
    result = escape_csv_value(value)
    assert result.startswith("'")
    assert result[1:] == value


@pytest.mark.parametrize(
    "value",
    [
        "Иванов Иван",
        "БПИ-101",
        "ok",
        "1+1",
        " =safe",
        "a=b",
        "",
    ],
)
def test_safe_values_pass_through(value):
    assert escape_csv_value(value) == value


def test_non_string_is_coerced():
    assert escape_csv_value(42) == "42"
    assert escape_csv_value(None) == "None"


def test_only_first_char_matters():
    assert escape_csv_value("=a=b") == "'=a=b"
    assert escape_csv_value("ab=c") == "ab=c"
