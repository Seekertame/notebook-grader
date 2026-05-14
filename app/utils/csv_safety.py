# символы, с которых Excel/LibreOffice интерпретируют ячейку как формулу (CSV injection)
_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def escape_csv_value(value: str) -> str:
    if not isinstance(value, str):
        value = str(value)
    if value and value[0] in _DANGEROUS_PREFIXES:
        # одинарная кавычка-префикс отключает интерпретацию формулы в Excel
        return "'" + value
    return value
