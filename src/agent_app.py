import streamlit as st
import pandas as pd
import io

from utils.actuals_utils import build_actuals
from utils.sep_utils import pull_sep_wide

st.title("FRED Data Chatbot Agent")
st.markdown("Chat with FRED data, preview results, and build your custom report.")


# Helper: build a combined wide DataFrame (years x series)
@st.cache_data
def build_combined():
    # Actuals: long -> wide
    actuals = build_actuals()
    # Ensure year column exists
    if "year" not in actuals.columns:
        # try to infer from obs_date
        if "obs_date" in actuals.columns:
            actuals["year"] = pd.to_datetime(actuals["obs_date"]).dt.year
        else:
            actuals["year"] = actuals.index

    # create a descriptive column name
    actuals["series_name"] = (
        actuals["variable_group"].astype(str)
        + "."
        + actuals["measure"].astype(str)
        + "."
        + actuals["fred_code"].astype(str)
    )
    actuals_wide = (
        actuals.pivot_table(index="year", columns="series_name", values="value", aggfunc="last")
        .sort_index()
    )

    # SEP wide: date-indexed wide -> convert index to year and align
    sep_wide = pull_sep_wide()
    # convert index to datetime years
    try:
        sep_wide = sep_wide.copy()
        sep_wide.index = pd.to_datetime(sep_wide.index).year
        sep_wide.index.name = "year"
        # if multiple rows per year, keep the last
        sep_by_year = sep_wide.groupby(sep_wide.index).last()
    except Exception:
        # fallback: if index already years
        sep_by_year = sep_wide.copy()
        sep_by_year.index.name = "year"

    # combine both sources
    combined = pd.concat([actuals_wide, sep_by_year], axis=1)
    # ensure column names are strings
    combined.columns = [str(c) for c in combined.columns]
    combined = combined.sort_index()
    return combined


# Initialize session selections
if "selections" not in st.session_state:
    st.session_state.selections = {}


# Sidebar: quick preview of combined data and chosen series
st.sidebar.header("Data preview & selections")
combined_df = build_combined()
st.sidebar.write("Available series:")
with st.sidebar.expander("Browse available series (first 30)", expanded=False):
    st.write(list(combined_df.columns[:30]))

with st.sidebar.expander("Recent data (combined)"):
    st.dataframe(combined_df.tail(10))


# Chat input (main interaction)
prompt = st.chat_input("Ask me about economic indicators, or type 'generate report'.")

if prompt:
    if "report" in prompt.lower():
        # Generate report CSV from selected series
        included = [s for s, include in st.session_state.selections.items() if include]
        if not included:
            st.warning("No series selected for the report. Preview series and toggle 'Include' to add them.")
        else:
            df_report = combined_df.loc[:, included]
            # include year column for clarity
            out = df_report.reset_index().rename(columns={"index": "year"})
            csv_buf = io.BytesIO()
            out.to_csv(csv_buf, index=False)
            st.download_button("Download Report CSV", csv_buf.getvalue(), "fred_report.csv")
            st.success("Report generated and ready to download.")
    else:
        # Show series that match the prompt
        query = prompt.strip()
        matching = [c for c in combined_df.columns if query.lower() in c.lower()]
        if not matching:
            st.write("I couldn't find that series. Try keywords like 'gdp', 'pce', 'fed_funds', or 'unemployment'.")
        else:
            # if multiple matches, let user pick
            if len(matching) > 1:
                choice = st.selectbox("Multiple matches — pick a series to preview", matching)
            else:
                choice = matching[0]

            st.write(f"### Preview: {choice}")
            series = combined_df[choice].dropna()
            if series.empty:
                st.write("No data available for this series.")
            else:
                st.line_chart(series)

            key = f"include::{choice}"
            current = st.session_state.selections.get(choice, False)
            include = st.checkbox(f"Include {choice} in report?", value=current, key=key)
            st.session_state.selections[choice] = include

            # allow quick view of the underlying table for the chosen series
            with st.expander("Show underlying data for this series"):
                st.dataframe(series.tail(20))
