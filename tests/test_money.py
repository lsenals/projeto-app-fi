import pytest

from app_fi.core.money import format_brl, parse_brl


@pytest.mark.parametrize(
    "cents, text",
    [
        (0, "R$ 0,00"),
        (5, "R$ 0,05"),
        (3490, "R$ 34,90"),
        (100000, "R$ 1.000,00"),
        (123456, "R$ 1.234,56"),
        (-123456, "-R$ 1.234,56"),
    ],
)
def test_format_brl(cents, text):
    assert format_brl(cents) == text


@pytest.mark.parametrize(
    "text, cents",
    [
        ("34,90", 3490),
        ("R$ 34,90", 3490),
        ("1.234,56", 123456),
        ("1000", 100000),
        ("0,05", 5),
        ("  R$ 7,00 ", 700),
    ],
)
def test_parse_brl(text, cents):
    assert parse_brl(text) == cents


def test_parse_brl_round_trips_format():
    for cents in (0, 1, 99, 3490, 123456, 999999):
        assert parse_brl(format_brl(cents)) == cents


@pytest.mark.parametrize("bad", ["", "   ", "abc", "R$", "12,,3"])
def test_parse_brl_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_brl(bad)
