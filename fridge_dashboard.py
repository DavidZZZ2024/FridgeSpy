"""
Fridge Price & Rating Tracker — Snowflake Streamlit Dashboard
=============================================================
Paste this file into a Snowflake Streamlit app.

Assumptions
-----------
• Your table (or view) is accessible as:  FRIDGE_DATA.PUBLIC.TGG_FRIDGE_CHECK
  Adjust DATABASE / SCHEMA / TABLE below if different.
• Columns expected:
    DATE_RAW      VARCHAR  (YYYY-MM-DD)
    RETAILER      VARCHAR
    BRAND         VARCHAR
    MODEL         VARCHAR
    TITLE         VARCHAR
    PRICE_RAW     FLOAT
    RATING_RAW    FLOAT
"""

import streamlit as st
import pandas as pd
from snowflake.snowpark.context import get_active_session

# ── Configuration ─────────────────────────────────────────────────────────────
DATABASE  = "FRIDGE_DB"
SCHEMA    = "RAW"
TABLE     = "TGG_FRIDGES_RAW"
FULL_TABLE = f"{DATABASE}.{SCHEMA}.{TABLE}"

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fridge Price & Rating Tracker",
    page_icon="🧊",
    layout="wide",
)

st.title("🧊 Fridge Price & Rating Tracker")
st.caption("Historical price and rating trends across retailers and models.")

# ── Session & data ────────────────────────────────────────────────────────────
session = get_active_session()

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    df = session.sql(f"""
        SELECT
            TRY_TO_DATE(DATE_RAW, 'YYYY-MM-DD')  AS SNAPSHOT_DATE,
            RETAILER,
            BRAND,
            MODEL,
            TITLE,
            PRICE_RAW,
            RATING_RAW
        FROM {FULL_TABLE}
        WHERE DATE_RAW IS NOT NULL
          AND MODEL     IS NOT NULL
    """).to_pandas()
    df["SNAPSHOT_DATE"] = pd.to_datetime(df["SNAPSHOT_DATE"])
    return df

df = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 Filters")

    brands = sorted(df["BRAND"].dropna().unique())
    sel_brands = st.multiselect(
        "Brand",
        options=brands,
        default=brands,
        help="Select one or more brands.",
    )

    retailers = sorted(df["RETAILER"].dropna().unique())
    sel_retailers = st.multiselect(
        "Retailer",
        options=retailers,
        default=retailers,
        help="Select one or more retailers.",
    )

    # Models filtered by selected brands/retailers
    filtered_models_df = df[
        df["BRAND"].isin(sel_brands) & df["RETAILER"].isin(sel_retailers)
    ]
    models = sorted(filtered_models_df["MODEL"].dropna().unique())
    sel_models = st.multiselect(
        "Model",
        options=models,
        default=models,
        help="Select one or more models.",
    )

# ── Apply filters ─────────────────────────────────────────────────────────────
mask = (
    df["BRAND"].isin(sel_brands)
    & df["RETAILER"].isin(sel_retailers)
    & df["MODEL"].isin(sel_models)
)
filtered = df[mask].copy()

if filtered.empty:
    st.warning("No data matches the current filters. Please adjust your selections.")
    st.stop()

# ── KPI summary cards ─────────────────────────────────────────────────────────
st.subheader("📊 Model Summary")

summary = (
    filtered.groupby(["BRAND", "RETAILER", "MODEL", "TITLE"])
    .agg(
        LOWEST_PRICE=("PRICE_RAW",    "min"),
        LATEST_PRICE=("PRICE_RAW",    "last"),
        LATEST_RATING=("RATING_RAW",  "last"),
        FIRST_SEEN=("SNAPSHOT_DATE",  "min"),
        DATA_POINTS=("PRICE_RAW",     "count"),
    )
    .reset_index()
    .sort_values(["BRAND", "MODEL"])
)

# Format for display
display_summary = summary.copy()
display_summary["LOWEST_PRICE"]  = display_summary["LOWEST_PRICE"].apply(lambda x: f"${x:,.2f}")
display_summary["LATEST_PRICE"]  = display_summary["LATEST_PRICE"].apply(lambda x: f"${x:,.2f}")
display_summary["LATEST_RATING"] = display_summary["LATEST_RATING"].apply(lambda x: f"{x:.1f} ⭐")
display_summary["FIRST_SEEN"]    = display_summary["FIRST_SEEN"].dt.strftime("%Y-%m-%d")

display_summary = display_summary.rename(columns={
    "BRAND":         "Brand",
    "RETAILER":      "Retailer",
    "MODEL":         "Model",
    "TITLE":         "Title",
    "LOWEST_PRICE":  "Lowest Price",
    "LATEST_PRICE":  "Latest Price",
    "LATEST_RATING": "Latest Rating",
    "FIRST_SEEN":    "First Seen",
    "DATA_POINTS":   "Snapshots",
})

st.dataframe(
    display_summary[["Brand","Retailer","Model","Title","Lowest Price","Latest Price","Latest Rating","First Seen","Snapshots"]],
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
st.subheader("📈 Price Movement (by Model)")

# Build a pivot: date × model → avg price (handles duplicates per day)
price_pivot = (
    filtered.groupby(["SNAPSHOT_DATE", "MODEL"])["PRICE_RAW"]
    .mean()
    .unstack("MODEL")
    .sort_index()
)

if price_pivot.empty or price_pivot.shape[0] < 1:
    st.info("Not enough date points to draw a price trend chart.")
else:
    st.line_chart(
        price_pivot,
        use_container_width=True,
        height=350,
    )

st.divider()

st.subheader("⭐ Rating Movement (by Model)")

rating_pivot = (
    filtered.groupby(["SNAPSHOT_DATE", "MODEL"])["RATING_RAW"]
    .mean()
    .unstack("MODEL")
    .sort_index()
)

if rating_pivot.empty or rating_pivot.shape[0] < 1:
    st.info("Not enough date points to draw a rating trend chart.")
else:
    st.line_chart(
        rating_pivot,
        use_container_width=True,
        height=350,
    )

st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────
st.caption(
    f"Data source: `{FULL_TABLE}` · "
    f"{len(filtered):,} rows shown · "
    f"Refreshes every 5 minutes."
)
