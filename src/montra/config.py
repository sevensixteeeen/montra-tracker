"""App-wide settings. Change values here rather than in the code that uses them."""

import os
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Private settings such as the database address. Never uploaded to GitHub.
SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"

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
    "Subscription",
    "Other",
]


def database_url() -> str:
    """The address of the Postgres database. It contains the password: never print it.

    Read from the DATABASE_URL environment variable if set (the hosting service
    and the tests use that), otherwise from the private settings file.
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url and SECRETS_FILE.exists():
        settings = tomllib.loads(SECRETS_FILE.read_text(encoding="utf-8-sig"))
        url = settings.get("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://")):
        raise RuntimeError(
            "No database address found. Put DATABASE_URL in .streamlit/secrets.toml;"
            " it should start with postgresql://"
        )
    return url
