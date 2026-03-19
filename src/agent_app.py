import streamlit as st
import pandas as pd
import io

from utils.actuals_utils import build_actuals
from utils.sep_utils import pull_sep_wide

st.title("FRED Data Chatbot Agent")
st.markdown("Chat with FRED data, preview results, and build your custom report.")

# -----------------------------
# DATA LAYER
# -----------------------------

@st.cache_data
def build_combined():

    # -----------------------------
    # LOAD DATA
    # -----------------------------
    actuals = build_actuals()
    sep_wide = pull_sep_wide()

    # -----------------------------
    # ACTUALS CLEANING
    # -----------------------------
    actuals = actuals.copy()

    if "obs_date" not in actuals.columns:
        raise ValueError("actuals must contain 'obs_date' column")

    actuals["obs_date"] = pd.to_datetime(actuals["obs_date"], errors="coerce")

    # Drop bad dates early
    actuals = actuals.dropna(subset=["obs_date"])

    # Build series name
    actuals["series_name"] = (
        actuals["variable_group"].astype(str)
        + "." +
        actuals["measure"].astype(str)
        + "." +
        actuals["fred_code"].astype(str)
    )
    # Pivot to wide format
    actuals_wide = (
        actuals.pivot_table(
            index="obs_date",
            columns="series_name",
            values="value",
            aggfunc="last"
        )
        .sort_index()
    )

    # -----------------------------
    # SEP CLEANING
    # -----------------------------
    sep_wide = sep_wide.copy()

    # Ensure datetime index
    try:
        sep_wide.index = pd.to_datetime(sep_wide.index, errors="coerce")
    except Exception as e:
        raise ValueError(f"SEP index conversion failed: {e}")

    # Drop bad dates
    sep_wide = sep_wide[~sep_wide.index.isna()]
    sep_wide.index.name = "obs_date"

    # -----------------------------
    # ALIGN GRANULARITY FOT COMBINATION AS DATE TYPE
    # -----------------------------
    # If SEP is yearly, convert to Jan 1 of each year explicitly
    if sep_wide.index.inferred_type in ["integer", "mixed-integer"]:
        sep_wide.index = pd.to_datetime(sep_wide.index.astype(str), format="%Y")

    # -----------------------------
    # COMBINE
    # -----------------------------
    combined = pd.concat([actuals_wide, sep_wide], axis=1)

    # Ensure clean datetime index
    combined = combined[~combined.index.isna()]
    combined = combined.sort_index()

    # Clean column names
    combined.columns = combined.columns.map(str)

    return combined

combined_df = build_combined()

# -----------------------------
# STATE INITIALIZATION
# -----------------------------

if "query" not in st.session_state:
    st.session_state.query = None

if "matches" not in st.session_state:
    st.session_state.matches = []

if "selected_series" not in st.session_state:
    st.session_state.selected_series = None

if "selections" not in st.session_state:
    st.session_state.selections = {}

# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.header("Data preview")

with st.sidebar.expander("Available series"):
    st.write(list(combined_df.columns[:30]))

with st.sidebar.expander("Recent data"):
    st.dataframe(combined_df.tail(10))

# -----------------------------
# CHAT INPUT HANDLER
# -----------------------------

prompt = st.chat_input("Ask about indicators or type 'generate report'")

if prompt:

    st.session_state.query = prompt
    if "report" in prompt.lower():
        st.session_state.matches = []
    else:
        matches = [
            c for c in combined_df.columns
            if prompt.lower() in c.lower()
        ]
        st.session_state.matches = matches

# -----------------------------
# REPORT GENERATION
# -----------------------------

if st.session_state.query and "report" in st.session_state.query.lower():

    included = [
        s for s, include in st.session_state.selections.items()
        if include
    ]
    if not included:
        st.warning("No series selected.")
    else:

        df_report = combined_df[included]
        out = df_report.reset_index()
        csv = out.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            "fred_report.csv"
        )

# -----------------------------
# MATCH DISPLAY
# -----------------------------

matches = st.session_state.matches
if matches:

    if len(matches) > 1:
        choice = st.selectbox(
            "Pick a series",
            matches,
            key="series_picker"
        )
    
    else:
        choice = matches[0]
    st.session_state.selected_series = choice


# -----------------------------
# SERIES PREVIEW
# -----------------------------

series_name = st.session_state.selected_series

if series_name:
    st.subheader(series_name)
    series = combined_df[series_name].dropna()
    plot_df = pd.DataFrame({
        "date": series.index,
        "value": pd.to_numeric(series, errors="coerce")
    }).dropna()

    st.line_chart(plot_df, x="date", y="value")

    include = st.checkbox(
        f"Include {series_name}",
        value=st.session_state.selections.get(series_name, False),
        key=f"include_{series_name}"
    )

    st.session_state.selections[series_name] = include

    with st.expander("Underlying data"):
        st.dataframe(series.tail(20))

#to run : streamlit run agent_app.py