"""App-wide settings. Change values here rather than in the code that uses them."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Set the MONTRA_DB environment variable to keep the database elsewhere.
DB_PATH = Path(os.environ.get("MONTRA_DB", PROJECT_ROOT / "data" / "expenses.db"))

CURRENCY_SYMBOL = "₹"

CATEGORIES = [
    "Food",
    "Groceries",
    "Rent",
    "Transport",
    "Utilities",
    "Shopping",
    "Health",
    "Entertainment",
    "Other",
]
