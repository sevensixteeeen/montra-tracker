# Montra

Personal monthly expense tracker. Python, SQLite and Streamlit, managed with uv.

## Run

On Windows, double-click `start-montra.bat` (or a shortcut to it). It starts the
app for this computer only and opens it in the browser. Close its window to stop.

From a terminal:

```powershell
uv run streamlit run app.py   # open the app in the browser
uv run pytest                 # run the tests
uv run ruff check             # lint
uv run ruff format            # format
```

## Login

The first time the app opens it asks you to create a 4-digit PIN. After that it
shows a PIN screen before anything else. Refreshing the page or opening a new
tab asks for the PIN again.

Five wrong PINs in a row lock the app for 5 minutes. While it is locked even the
right PIN is refused.

Forgot the PIN, or locked out? This clears the PIN and the lock and keeps your
expenses, so the app asks you to create a new PIN:

```powershell
uv run python -m montra.auth reset
```

Only a one-way hash of the PIN is stored, in `data/expenses.db`. The PIN
protects the app screen; it does not encrypt that database file.

## Structure

```
app.py                     Streamlit UI (the only file that knows about Streamlit)
.streamlit/config.toml     the app's look: colours, fonts, rounded corners
src/montra/
    config.py              database path, currency symbol, category list
    models.py              Expense dataclass
    money.py               rupees <-> paise conversion and formatting
    db.py                  SQLite connection and table schema
    auth.py                login PIN: hashing, checking, lockout, reset command
    repository.py          add / list / delete expenses (all SQL lives here)
    services.py            monthly totals and per-category breakdown
tests/                     pytest tests, run against an in-memory database
data/expenses.db           your data, created on first run, ignored by git
```

Each layer only talks to the one below it: `app.py` -> `services.py` ->
`repository.py` -> `db.py`.

Amounts are stored as whole paise (integers), not floats, so monthly totals are
exact. Dates are stored as `YYYY-MM-DD` text.
