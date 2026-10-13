# Montra

Monthly expense tracker. Python, Postgres and Streamlit, managed with uv.

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

The app needs an internet connection: its data lives in an online Postgres
database (Neon).

## Database address

The app finds its database through one private setting, `DATABASE_URL`. On your
computer it lives in `.streamlit/secrets.toml`:

```toml
DATABASE_URL = "postgresql://..."
```

That address contains the database password. The file is listed in `.gitignore`
and must never be uploaded or shared.

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

Only a one-way hash of the PIN is stored, in the database. The PIN protects the
app screen; it does not encrypt the database.

## Tests

The tests never touch the online database. They start a small Postgres server on
your own computer (in `data/test-postgres`, which git ignores) and empty it
before each test. The first run takes about 15 seconds to set that server up.

## Structure

```
app.py                     Streamlit UI (the only file that knows about Streamlit)
.streamlit/config.toml     the app's look: colours, fonts, rounded corners
.streamlit/secrets.toml    private settings (not in git)
src/montra/
    config.py              database address, currency symbol, category list
    models.py              Expense dataclass
    money.py               rupees <-> paise conversion and formatting
    db.py                  Postgres connection and table schema
    auth.py                login PIN: hashing, checking, lockout, reset command
    repository.py          add / list / delete one person's expenses (all SQL lives here)
    services.py            monthly totals and per-category breakdown
    sqlite_import.py       one-off copy of the old laptop file into Postgres
tests/                     pytest tests, run against a local throwaway Postgres
data/                      old laptop database and its backup, ignored by git
```

`app.py` asks `repository.py` for one person's expenses and hands that list to
`services.py` for the totals. Only `repository.py` and `auth.py` send SQL, through
the connection that `db.py` opens.

Amounts are stored as whole paise (integers), not floats, so monthly totals are
exact.
