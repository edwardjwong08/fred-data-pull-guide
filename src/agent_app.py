import streamlit as st
import pandas as pd
import io
import altair as alt
from fredapi import Fred
import google.generativeai as genai

from utils.actuals_utils import build_actuals
from utils.sep_utils import pull_sep_wide

st.title("FRED Data Chatbot Agent")
st.markdown("Chat with FRED data, preview results, and build your custom report.")

gemini_api_key = st.text_input("Input your Gemini API Key:", type="password")

if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    gemini_model = genai.GenerativeModel("gemini-2.5-flash")
else:
    gemini_model = None

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
# GEMINI MODEL FUNCTION
# -----------------------------
def get_fred_series_from_gemini(prompt):
    if not gemini_model:
        return None
    
    try:
        response = gemini_model.generate_content(f"""
        The user is searching for an economic data series.

        Convert the request into a FRED series ID.
        Only return the series ID, nothing else.

        Example:
        Input: inflation CPI
        Output: CPIAUCSL

        Input: {prompt}
        Output:
        """)

        series_id = response.text.strip().replace("\n", "")
        return series_id

    except Exception as e:
        st.error(f"Gemini error: {e}")
        return None

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
if "messages" not in st.session_state:
    st.session_state.messages = []

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
    for col in combined_df_temp.columns:
        name = col.split(".")
        if len(name) >= 3:
            display_name = f"{name[0]} - {name[1]} (ID: {name[2]})"
            name_list.append((display_name, col))
        else:
            display_name = col
            name_list.append((display_name, col))
    
    # Initialize selections dict if missing
    if "selections" not in st.session_state:
        st.session_state.selections = {}

    # Initialize widget states for each checkbox
    for _, col in name_list:
        checkbox_key = f"sidebar_{col}"
        if checkbox_key not in st.session_state:
            st.session_state[checkbox_key] = st.session_state.selections.get(col, False)

    # Determine if all are currently selected
    current_all_selected = all(st.session_state[f"sidebar_{col}"] for _, col in name_list)

    # Select All checkbox
    select_all = st.checkbox("Select All", value=current_all_selected, key="select_all_sidebar")

    # If Select All changes, update all individual checkboxes
    for _, col in name_list:
        checkbox_key = f"sidebar_{col}"
        st.session_state[checkbox_key] = select_all

    # Render individual checkboxes
    for display_name, col in name_list:
        checkbox_key = f"sidebar_{col}"
        include = st.checkbox(display_name, key=checkbox_key)
        st.session_state.selections[col] = include


with st.sidebar.expander("Recent data"):
    st.dataframe(combined_df_temp.tail(10))

with st.sidebar.expander("Data Series You Have Selected"):
    selected = [
        s for s, include in st.session_state.selections.items()
        if include
    ]

    if selected:
        for s in selected:
            name = s.split(".")
            if len(name) >= 3:  
                display_name = f"{name[0]} - {name[1]} (ID: {name[2]})"
                st.write(display_name)
            else:
                st.write(s)
    # if selected: # remove when above display name logic is added and correct
    #     st.write(selected)
    else:
        st.write("No series selected yet.")

# -----------------------------
# CHAT HISTORY DISPLAY
# -----------------------------
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["type"] == "text":
            st.write(msg["content"])

        elif msg["type"] == "matches":
            st.write(msg["content"])
            for display_name in msg["display_names"]:
                st.write(f"**{display_name}**")

        elif msg["type"] == "series_preview":
            series_name = msg["series_name"]
            if combined_df is not None and series_name in combined_df.columns:
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
                    key=f"history_include_{i}_{series_name}"
                )
                st.session_state.selections[series_name] = include

                with st.expander("Underlying data"):
                    st.dataframe(series.tail(20))

        elif msg["type"] == "report":
            st.write(msg["content"])
            included = [
                s for s, include in st.session_state.selections.items()
                if include
            ]
            if included and combined_df is not None:
                df_report = combined_df[included]
                out = df_report.reset_index()
                csv = out.to_csv(index=False)

                st.download_button(
                    "Download CSV",
                    csv,
                    "fred_report.csv",
                    key=f"download_{i}"
                )


# -----------------------------
# CHAT INPUT HANDLER
# -----------------------------

prompt = st.chat_input("Ask about indicators or type 'generate report'")

if prompt:
    st.session_state.query = prompt

    st.session_state.messages.append({
        "role": "user",
        "type": "text",
        "content": prompt
    })

    if combined_df is None:
        st.session_state.messages.append({
            "role": "assistant",
            "type": "text",
            "content": "Please click 'Load Data' first before searching."
        })

    elif "report" in prompt.lower():
        st.session_state.matches = []

        st.session_state.messages.append({
            "role": "assistant",
            "type": "report",
            "content": "Generating report from selected series."
        })

    else:
        matches = [
            c for c in combined_df.columns
            if prompt.lower() in c.lower()
        ]
        st.session_state.matches = matches

        # -----------------------------
        # GEMINI FALLBACK
        # -----------------------------
        if not matches:
            st.session_state.messages.append({
                "role": "assistant",
                "type": "text",
                "content": "No local matches found. Asking Gemini..."
            })

            series_id = get_fred_series_from_gemini(prompt)

            if series_id:
                try:
                    new_series = fred.get_series(series_id)
                    new_series.index = pd.to_datetime(new_series.index)

                    col_name = f"external.user_query.{series_id}"

                    combined_df[col_name] = new_series
                    st.session_state["combined_df"] = combined_df

                    matches = [col_name]
                    st.session_state.matches = matches

                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "text",
                        "content": f"Added new series from FRED: {series_id}"
                    })

                except Exception as e:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "text",
                        "content": f"Could not fetch FRED series: {e}"
                    })

        # -----------------------------
        # SAVE MATCH RESULTS
        # -----------------------------
        if matches:
            display_matches = []
            display_names = []

            for match in matches:
                name = match.split(".")
                if len(name) >= 3:
                    display_name = f"{name[0]} - {name[1]} (ID: {name[2]})"
                else:
                    display_name = match

                display_matches.append((display_name, match))
                display_names.append(display_name)

            if len(matches) > 1:
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "matches",
                    "content": "Multiple matches found. They are listed below:",
                    "matches": matches,
                    "display_names": display_names
                })

            # Auto-preview first match
            choice = matches[0]
            st.session_state.selected_series = choice

            st.session_state.messages.append({
                "role": "assistant",
                "type": "series_preview",
                "series_name": choice
            })

        else:
            st.session_state.messages.append({
                "role": "assistant",
                "type": "text",
                "content": "No matches found. Try a different query or check the sidebar for available series."
            })

else:
    st.info("Type something in the chat input below to search for data series or generate a report.")

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
        st.write("Multiple matches found. They are listed below:")

        display_matches = []

        for match in matches:
            name = match.split(".")
            if len(name) >= 3:
                display_name = f"{name[0]} - {name[1]} (ID: {name[2]})"
                display_matches.append((display_name, match))
            else:
                display_matches.append((match, match))

        for display_name, raw_match in display_matches:
            st.write(f"**{display_name}**")

        choice = st.selectbox(
            "Pick a series",
            display_matches,
            format_func=lambda x: x[0],
            key="series_picker"
        )

        # If you want just the raw series name:
        choice = choice[1]
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

#to run : .venv\Scripts\Activate cd src python -m streamlit run test.py