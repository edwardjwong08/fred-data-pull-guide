import streamlit as st
import pandas as pd
import io
import altair as alt
from fredapi import Fred

from utils.actuals_utils import build_actuals
from utils.sep_utils import pull_sep_wide

st.title("FRED Data Chatbot Agent")
st.markdown("Chat with FRED data, preview results, and build your custom report.")

fred_api_key = st.text_input("Input your FRED API Key here: ", type="password")
try:
    fred = Fred(api_key=fred_api_key)
    #test case to verify key works, if fails then invalid key
    gdp = fred.search('gross domestic product', sort_order='asc')
    st.success("FRED API key set successfully!")
except Exception as e:
    st.error(f"Error setting FRED API key: {e}")
    st.stop()

st.markdown(
    "Add dates for your data series that you want to include in your report "
    "(Use: YYYY-MM-DD). When you're ready, click 'Load Data' and then type "
    "'generate report' to download a CSV of the selected series."
)

# -----------------------------
# USER INPUTS
# -----------------------------
start_date_input = st.text_input("Start date (YYYY-MM-DD)", value="2020-01-01")
end_date_input = st.text_input("End date (YYYY-MM-DD)", value="2029-01-01")

# Normalize inputs (IMPORTANT for caching)
try:
    start_date = str(pd.to_datetime(start_date_input).date())
    end_date = str(pd.to_datetime(end_date_input).date())
except Exception:
    st.error("Invalid date format. Please use YYYY-MM-DD.")
    st.stop()

st.markdown(f"Start date: {start_date}, End date: {end_date}")

# -----------------------------
# DATA LAYER
# -----------------------------
@st.cache_data
def build_combined(start_date, end_date):

    # -----------------------------
    # LOAD DATA
    # -----------------------------
    actuals = build_actuals(start_date, end_date)
    sep_wide = pull_sep_wide(start_date, end_date)

    # -----------------------------
    # ACTUALS CLEANING
    # -----------------------------
    actuals = actuals.copy()

    if "obs_date" not in actuals.columns:
        raise ValueError("actuals must contain 'obs_date' column")

    actuals["obs_date"] = pd.to_datetime(actuals["obs_date"], errors="coerce")
    actuals = actuals.dropna(subset=["obs_date"])

    actuals["series_name"] = (
        actuals["variable_group"].astype(str)
        + "." +
        actuals["measure"].astype(str)
        + "." +
        actuals["fred_code"].astype(str)
    )

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

    sep_wide.index = pd.to_datetime(sep_wide.index, errors="coerce")
    sep_wide = sep_wide[~sep_wide.index.isna()]
    sep_wide.index.name = "obs_date"

    # Handle yearly index edge case
    if sep_wide.index.inferred_type in ["integer", "mixed-integer"]:
        sep_wide.index = pd.to_datetime(sep_wide.index.astype(str), format="%Y")

    # -----------------------------
    # COMBINE
    # -----------------------------
    combined = pd.concat([actuals_wide, sep_wide], axis=1)
    combined = combined[~combined.index.isna()].sort_index()
    combined.columns = combined.columns.map(str)

    return combined

# -----------------------------
# LOAD DATA BUTTON
# -----------------------------
if st.button("Load Data"):
    with st.spinner("Loading and combining data..."):
        st.session_state["combined_df"] = build_combined(start_date, end_date)

# -----------------------------
# ACCESS DATA
# -----------------------------
combined_df = st.session_state.get("combined_df")

if combined_df is not None:
    st.success("Data loaded successfully!")
    #st.dataframe(combined_df.head())
else:
    st.info("Click 'Load Data' to fetch data.")

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
    combined_df_temp = build_combined(start_date, end_date)
    name_list = []
    for col in combined_df_temp.columns[:30]:
        name = col.split(".")
        if len(name) >= 3:
            display_name = f"{name[0]} - {name[1]} (ID: {name[2]})"
            name_list.append(display_name)
        else:
            display_name = col
            name_list.append(display_name)
    
    st.write(name_list)

with st.sidebar.expander("Recent data"):
    st.dataframe(combined_df_temp.tail(10))

with st.sidebar.expander("Data Series You Have Selected"):
    selected = [
        s for s, include in st.session_state.selections.items()
        if include
    ]
    if selected:
        st.write(selected)
    else:
        st.write("No series selected yet.")

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
else:
    st.session_state.selected_series = None
    st.info("No matches found. Try a different query or check the sidebar for available series.")

# -----------------------------
# SERIES PREVIEW
# -----------------------------

series_name = st.session_state.selected_series

if series_name:
    series_name_string = series_name.split(".")
    if len(series_name_string) >= 3:
        title = f"{series_name_string[0]} - {series_name_string[1]} (ID: {series_name_string[2]})"
    else:
        title = series_name
    st.subheader(title)

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

#to run : cd src python -m streamlit run agent_app.py