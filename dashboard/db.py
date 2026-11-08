"""Database access for the dashboard.

Every number on screen comes from a view created by sql/05_dashboard_views.sql.
The dashboard only reads (SELECT); all business logic stays in PostgreSQL.
"""
import os
from decimal import Decimal

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()

# Views the dashboard is allowed to read (names are never built from user input).
VIEWS = {
    "v_dash_q1_kpi", "v_dash_global", "v_dash_q2_produits", "v_dash_q4_tranches",
    "v_dash_q5_pivot", "v_dash_q6a_ratio", "v_dash_q6b_profils",
    "v_dash_q7_historique", "v_dash_q8_alerte",
}

# Shared colours: one accent for "above average / at risk", neutral grey otherwise.
RISK = "#C0392B"
NEUTRAL = "#9AA5B1"
REFERENCE = "#34495E"


@st.cache_resource
def get_engine():
    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "credit_risk"),
    )
    return create_engine(url, connect_args={"options": "-csearch_path=credit,public"})


def _to_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """PostgreSQL NUMERIC arrives as Decimal; convert those columns to float."""
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = df[col].astype(float)
    return df


@st.cache_data(ttl=600, show_spinner=False)
def view(name: str) -> pd.DataFrame:
    """Return SELECT * FROM <name> for one of the whitelisted dashboard views."""
    if name not in VIEWS:
        raise ValueError(f"Unknown view: {name}")
    with get_engine().connect() as conn:
        return _to_numeric(pd.read_sql(text(f"SELECT * FROM {name}"), conn))


def global_rate() -> float:
    """Share of clients in difficulty (target = 1), in %."""
    return float(view("v_dash_global").iloc[0]["taux_difficulte_pct"])


def check_connection() -> None:
    """Stop the page with a readable message if the database or views are missing."""
    try:
        view("v_dash_global")
    except Exception as exc:  # noqa: BLE001 - show any connection/setup error to the user
        st.error(
            "Cannot read the database. Check the .env settings, then run "
            "04_analytical_queries.sql and 05_dashboard_views.sql.\n\n"
            f"Details: {exc}"
        )
        st.stop()


def footer() -> None:
    st.caption(
        "Data: sample of the public Home Credit Default Risk dataset (1,300 clients). "
        "Days are relative to each client's current application, there is no shared calendar. "
        "Difficulty = target 1 (payment difficulty on the current loan). "
        "Late rates are computed on instalments that have a payment date."
    )