import pytest

from app_fi.core.dates import previous_month


@pytest.mark.parametrize(
    "year, month, expected",
    [
        (2026, 9, (2026, 8)),
        (2026, 1, (2025, 12)),
        (2026, 12, (2026, 11)),
    ],
)
def test_previous_month(year, month, expected):
    assert previous_month(year, month) == expected
