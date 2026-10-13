from decimal import Decimal

from montra.money import format_money, to_minor


def test_to_minor():
    assert to_minor("249.50") == 24950
    assert to_minor(Decimal("0.01")) == 1
    assert to_minor(19.99) == 1999
    assert to_minor(0.1 + 0.2) == 30


def test_format_money():
    assert format_money(24950) == "₹249.50"
    assert format_money(5) == "₹0.05"
    assert format_money(99900) == "₹999.00"
    assert format_money(1400000) == "₹14,000.00"
    assert format_money(10000000) == "₹1,00,000.00"
    assert format_money(123456789) == "₹12,34,567.89"
