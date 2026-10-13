# Montra

Personal monthly expense tracker. Python, SQLite and Streamlit, managed with uv.

## Run

```powershell
uv run streamlit run app.py   # open the app in the browser
uv run pytest                 # run the tests
uv run ruff check             # lint
uv run ruff format            # format
```

## Structure

```
app.py                     Streamlit UI (the only file that knows about Streamlit)
.streamlit/config.toml     the app's look: colours, fonts, rounded corners
src/montra/
    config.py              database path, currency symbol, category list
    models.py              Expense dataclass
    money.py               rupees <-> paise conversion and formatting
    db.py                  SQLite connection and table schema
    repository.py          add / list / delete expenses (all SQL lives here)
    services.py            monthly totals and per-category breakdown
tests/                     pytest tests, run against an in-memory database
data/expenses.db           your data, created on first run, ignored by git
```

Each layer only talks to the one below it: `app.py` -> `services.py` ->
`repository.py` -> `db.py`.

Amounts are stored as whole paise (integers), not floats, so monthly totals are
exact. Dates are stored as `YYYY-MM-DD` text.
