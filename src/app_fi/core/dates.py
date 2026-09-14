"""Aritmética de ano/mês sem depender de `datetime` (que não faz mês-1 direto)."""

from __future__ import annotations


def previous_month(year: int, month: int) -> tuple[int, int]:
    """(2026, 9) -> (2026, 8)   ·   (2026, 1) -> (2025, 12)"""
    return (year - 1, 12) if month == 1 else (year, month - 1)
