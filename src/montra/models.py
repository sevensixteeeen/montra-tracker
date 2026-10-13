"""Plain data objects passed between the layers."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Expense:
    spent_on: date
    amount_minor: int  # paise, see money.py
    category: str
    note: str = ""
    id: int | None = None  # None until the expense has been saved
