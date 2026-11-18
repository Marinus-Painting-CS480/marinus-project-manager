"""Money helpers. Money is always Decimal, never float, and rounded to cents."""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def to_money(value) -> Decimal:
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def money_str(value) -> str:
    """Money as a string for JSON snapshots ("1250.00"), so no precision is lost."""
    return str(to_money(value))
