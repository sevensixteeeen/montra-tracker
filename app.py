"""Streamlit UI. Run with: uv run streamlit run app.py"""

import time
from contextlib import closing
from datetime import date

import psycopg
import streamlit as st

from montra.auth import (
    PIN_LENGTH,
    check_pin,
    has_pin,
    is_valid_pin,
    minutes_locked,
    set_pin,
    tries_left,
)
from montra.config import CATEGORIES, CURRENCY_SYMBOL
from montra.db import connect, create_tables
from montra.models import Expense
from montra.money import format_money, to_minor
from montra.repository import (
    add_expense,
    delete_expense,
    ensure_owner,
    list_expenses,
)
from montra.services import monthly_summary

st.set_page_config(
    page_title="Montra",
    page_icon=":material/account_balance_wallet:",
    layout="wide",
)

# Streamlit always draws white text on its main ("primary") buttons, which is
# hard to read on the lime accent colour. This one rule makes that text dark.
st.html(
    '<style>[data-testid^="stBaseButton-primary"] { color: #10130A !important; }'
    "</style>"
)

today = date.today()
state = st.session_state
state.setdefault("view_month", (today.year, today.month))


@st.cache_resource
def prepare_database() -> bool:
    """Create the tables once, when the app starts, not on every click."""
    with closing(connect()) as conn:
        create_tables(conn)
    return True


def database() -> psycopg.Connection:
    """This visitor's connection to the database, reused from click to click.

    Opening a connection is the slow part, so it is kept between clicks and
    reopened only when it has gone stale (the database sleeps when idle). If
    the database cannot be reached, say so plainly and show nothing else.
    """
    conn = state.get("db")
    if conn is not None and not conn.closed:
        try:
            conn.execute("SELECT 1")
            return conn
        except psycopg.OperationalError:
            conn.close()
    try:
        prepare_database()
        state.db = connect()
        return state.db
    except RuntimeError as problem:  # the database address is missing
        st.error(str(problem))
    except psycopg.OperationalError:
        st.error(
            "Montra cannot reach its database. Check your internet connection"
            " and try again."
        )
    st.stop()


def require_login(conn: psycopg.Connection) -> None:
    """Show the login screen, and nothing else, until the PIN is given."""
    if state.get("logged_in"):
        return

    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        st.title("Montra", anchor=False)
        wait = minutes_locked(conn)
        if not has_pin(conn):
            with st.form("create_pin"):
                st.subheader("Create your PIN", anchor=False)
                st.caption(
                    f"Exactly {PIN_LENGTH} digits. You will need it every time"
                    " you open Montra."
                )
                pin = st.text_input("PIN", type="password", max_chars=PIN_LENGTH)
                repeat = st.text_input(
                    "Type it again", type="password", max_chars=PIN_LENGTH
                )
                submitted = st.form_submit_button(
                    "Save PIN", type="primary", width="stretch"
                )
            if submitted:
                if not is_valid_pin(pin):
                    st.error(f"Use exactly {PIN_LENGTH} digits.")
                elif pin != repeat:
                    st.error("The two PINs do not match.")
                else:
                    # Never overwrite a PIN that was saved meanwhile.
                    if not has_pin(conn):
                        set_pin(conn, pin)
                        state.logged_in = True
                    st.rerun()
        elif wait:
            minutes = "1 minute" if wait == 1 else f"{wait} minutes"
            st.error(f"Too many wrong PINs. Montra is locked for {minutes}.")
            st.button("Try again")
        else:
            with st.form("login"):
                st.subheader("Enter your PIN", anchor=False)
                pin = st.text_input("PIN", type="password", max_chars=PIN_LENGTH)
                submitted = st.form_submit_button(
                    "Log in", type="primary", width="stretch"
                )
            if submitted:
                if not is_valid_pin(pin):
                    st.error(f"Enter your {PIN_LENGTH}-digit PIN.")
                else:
                    correct = check_pin(conn, pin)
                    if correct:
                        state.logged_in = True
                        st.rerun()
                    left = tries_left(conn)
                    locked = minutes_locked(conn) > 0
                    time.sleep(1)  # a short pause slows down PIN guessing
                    if locked:
                        st.rerun()  # shows the "locked" message above
                    tries = "1 try" if left == 1 else f"{left} tries"
                    st.error(f"That PIN is not right. {tries} left.")
    st.stop()


def shift_month(step: int) -> None:
    """Move the month being viewed forwards (+1) or backwards (-1)."""
    year, month = state.view_month
    months = year * 12 + (month - 1) + step
    state.view_month = (months // 12, months % 12 + 1)


def show_this_month() -> None:
    state.view_month = (today.year, today.month)


@st.dialog("Delete this expense?")
def confirm_delete(expense: Expense) -> None:
    st.text(expense.note or expense.category)
    st.caption(
        f"{format_money(expense.amount_minor)} · {expense.category}"
        f" · {expense.spent_on:%d %b %Y}"
    )
    keep, delete = st.columns(2)
    if keep.button("Keep it", width="stretch"):
        st.rerun()
    if delete.button("Delete", type="primary", width="stretch"):
        delete_expense(database(), state.user_id, expense.id)
        state.flash = (
            f"Deleted {format_money(expense.amount_minor)} · {expense.category}"
        )
        st.rerun()


def show_sidebar(conn: psycopg.Connection) -> None:
    """The add-expense form and the log out button."""
    with st.sidebar:
        st.title("Montra", anchor=False)
        st.caption("Monthly expenses")

        # enter_to_submit is off so Streamlit's "Press Enter to submit form" hint
        # does not sit on top of the amount being typed in the narrow side panel.
        with st.form(
            "add_expense", clear_on_submit=True, border=False, enter_to_submit=False
        ):
            st.subheader("Add expense", anchor=False)
            amount = st.number_input(
                f"Amount ({CURRENCY_SYMBOL})",
                min_value=0.0,
                value=None,
                step=10.0,
                format="%.2f",
                placeholder="0.00",
            )
            category = st.pills("Category", CATEGORIES, default=CATEGORIES[0])
            spent_on = st.date_input("Date", value=today, format="DD/MM/YYYY")
            note = st.text_input("Note (optional)", placeholder="What was it for?")
            submitted = st.form_submit_button(
                "Add expense", type="primary", icon=":material/add:", width="stretch"
            )

        if submitted:
            amount_minor = to_minor(amount or 0)
            if amount_minor <= 0:
                st.warning("Enter an amount greater than zero.")
            elif category is None:
                st.warning("Choose a category.")
            else:
                add_expense(
                    conn,
                    state.user_id,
                    Expense(spent_on, amount_minor, category, note.strip()),
                )
                # Jump to the month of the new expense so it is visible at once.
                state.view_month = (spent_on.year, spent_on.month)
                st.toast(
                    f"Added {format_money(amount_minor)} · {category}",
                    icon=":material/check_circle:",
                )

        st.divider()
        if st.button("Log out", icon=":material/logout:", width="stretch"):
            conn.close()
            state.clear()
            st.rerun()


def show_month(conn: psycopg.Connection) -> None:
    """The month heading, the three cards, the category bars and the list."""
    year, month = state.view_month
    expenses = list_expenses(conn, state.user_id, year, month)
    summary = monthly_summary(expenses)

    heading, nav = st.columns([3, 2], vertical_alignment="center")
    heading.title(f"{date(year, month, 1):%B %Y}", anchor=False)
    with nav.container(horizontal=True, horizontal_alignment="right"):
        if (year, month) != (today.year, today.month):
            st.button("This month", on_click=show_this_month)
        st.button(
            "",
            icon=":material/chevron_left:",
            help="Previous month",
            on_click=shift_month,
            args=(-1,),
        )
        st.button(
            "",
            icon=":material/chevron_right:",
            help="Next month",
            on_click=shift_month,
            args=(1,),
        )

    total_tile, count_tile, top_tile = st.columns([2, 1, 1])
    with total_tile.container(border=True, height="stretch"):
        st.caption("Total spent")
        st.title(f":primary[{format_money(summary.total_minor)}]", anchor=False)
    with count_tile.container(border=True, height="stretch"):
        st.caption("Expenses")
        st.header(str(summary.count), anchor=False)
    with top_tile.container(border=True, height="stretch"):
        st.caption("Top category")
        if summary.by_category:
            top_name, top_total = next(iter(summary.by_category.items()))
            st.header(top_name, anchor=False)
            st.caption(format_money(top_total))
        else:
            st.header("None yet", anchor=False)

    if not expenses:
        with st.container(border=True):
            st.subheader("Nothing recorded this month", anchor=False)
            st.caption(
                "Add an expense with the form, or go back to a month that has some."
            )
        return

    breakdown, listing = st.columns([2, 3])

    with breakdown.container(border=True):
        st.subheader("By category", anchor=False)
        biggest = max(summary.by_category.values())
        for name, total in summary.by_category.items():
            with st.container(gap=None):
                with st.container(horizontal=True, horizontal_alignment="distribute"):
                    st.markdown(f"**{name}**", width="content")
                    st.markdown(format_money(total), width="content")
                st.progress(total / biggest)

    with listing.container(border=True):
        st.subheader("Expenses", anchor=False)
        options = ["All", *summary.by_category]
        # The key includes the options so the filter resets when they change.
        chosen = st.pills(
            "Show",
            options,
            default="All",
            label_visibility="collapsed",
            key=f"filter-{year}-{month}-{'|'.join(options)}",
        )
        for expense in expenses:
            if chosen not in (None, "All", expense.category):
                continue
            with st.container(horizontal=True, vertical_alignment="center"):
                st.markdown(
                    f"**{expense.spent_on.day}**  \n{expense.spent_on:%b}", width=44
                )
                with st.container(gap=None):
                    st.text(expense.note or expense.category)
                    st.caption(expense.category)
                st.markdown(format_money(expense.amount_minor), width="content")
                if st.button(
                    "",
                    icon=":material/delete:",
                    key=f"delete-{expense.id}",
                    type="tertiary",
                    help="Delete this expense",
                ):
                    confirm_delete(expense)


conn = database()
require_login(conn)

# Whose expenses this is. Everything below is limited to this person.
if "user_id" not in state:
    state.user_id = ensure_owner(conn)

# A message saved just before the page reloads (see confirm_delete).
if "flash" in state:
    st.toast(state.pop("flash"), icon=":material/check_circle:")

show_sidebar(conn)
show_month(conn)
