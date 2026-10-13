"""Money helpers. Amounts are stored as whole paise (int) so sums never drift."""

from decimal import ROUND_HALF_UP, Decimal

from montra.config import CURRENCY_SYMBOL

MINOR_PER_MAJOR = 100


def to_minor(amount: Decimal | str | float) -> int:
    """Convert a rupee amount like 249.50 to paise (24950)."""
    paise = Decimal(str(amount)) * MINOR_PER_MAJOR
    return int(paise.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _group_indian(number: int) -> str:
    """Add commas the Indian way: last three digits, then pairs (12,34,567)."""
    digits = str(number)
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    pairs = []
    while head:
        pairs.insert(0, head[-2:])
        head = head[:-2]
    return ",".join([*pairs, tail])


def format_money(amount_minor: int) -> str:
    """Format paise for display, e.g. 24950 -> '₹249.50'."""
    major, minor = divmod(amount_minor, MINOR_PER_MAJOR)
    return f"{CURRENCY_SYMBOL}{_group_indian(major)}.{minor:02d}"
