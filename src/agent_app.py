import streamlit as st
import pandas as pd
import io
import altair as alt
from fredapi import Fred
import google.generativeai as genai
from sentence_transformers import SentenceTransformer, util

from utils.actuals_utils import build_actuals
from utils.sep_utils import pull_sep_wide
from utils.gemini_call import get_fred_series_from_gemini

# -----------------------------
# PAGE SETUP
# -----------------------------
st.set_page_config(page_title="FRED Data Research Assistant", layout="wide")

st.title("FRED Data Research Assistant")
st.markdown(
    "Search your preloaded economic data, explore related FRED series, preview charts, "
    "and build a custom report."
)

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def format_series_label(series_name: str) -> str:
    parts = str(series_name).split(".")
    if len(parts) >= 3:
        return f"{parts[0]} - {parts[1]} (ID: {parts[2]})"
    return str(series_name)


def add_message(role, msg_type, content=None, **kwargs):
    payload = {"role": role, "type": msg_type}
    if content is not None:
        payload["content"] = content
    payload.update(kwargs)
    st.session_state.messages.append(payload)


def get_selected_series():
    return [s for s, include in st.session_state.selections.items() if include]


def ensure_selection_key(series_name):
    if series_name not in st.session_state.selections:
        st.session_state.selections[series_name] = False


@st.cache_resource
def load_embedding_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


def get_column_embeddings(model, combined_df):
    if combined_df is None:
        return [], None
    column_names = combined_df.columns.tolist()
    embedding_inputs = []
    for col in column_names:
        parts = str(col).split(".")
        if len(parts) >= 3:
            embedding_inputs.append(" ".join(parts))
        else:
            embedding_inputs.append(str(col))
    embeddings = model.encode(embedding_inputs, convert_to_tensor=True)
    return column_names, embeddings


def search_local_series(prompt, model, combined_df, threshold=0.25, top_k=10):
    column_names, column_embeddings = get_column_embeddings(model, combined_df)
    if not column_names or column_embeddings is None:
        return []
    prompt_embedding = model.encode(prompt, convert_to_tensor=True)
    hits = util.semantic_search(prompt_embedding, column_embeddings, top_k=top_k)[0]
    hits = [hit for hit in hits if hit["score"] >= threshold]
    return [column_names[hit["corpus_id"]] for hit in hits]


def add_fred_series_to_dataframe(series_ids, fred, combined_df):
    added = []
    for sid in series_ids:
        sid = str(sid).strip().upper()
        if not sid:
            continue
        try:
            new_series = fred.get_series(sid)
            if new_series is None or new_series.empty:
                continue
            new_series.index = pd.to_datetime(new_series.index)
            col_name = f"external.user_query.{sid}"
            combined_df[col_name] = new_series
            added.append(col_name)
            ensure_selection_key(col_name)
        except Exception:
            continue
    return combined_df, added


# -----------------------------
# API KEYS
# -----------------------------
gemini_api_key = st.text_input("Input your Gemini API Key [here](https://aistudio.google.com/app/apikey): ", type="password")

if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        gemini_model = genai.GenerativeModel("gemini-2.5-flash")
        st.success("Gemini API key set successfully!")
    except Exception as e:
        gemini_model = None
        st.error(f"Error setting Gemini API key: {e}")
else:
    gemini_model = None

fred_api_key = st.text_input("Input your FRED API Key [here](https://fredaccount.stlouisfed.org/apikeys): ", type="password")

if fred_api_key:
    try:
        fred = Fred(api_key=fred_api_key)
        fred.search("gross domestic product", sort_order="asc")
        st.success("FRED API key set successfully!")
    except Exception as e:
        st.error(f"Error setting FRED API key: {e}")
        st.stop()
else:
    st.info("Enter your FRED API key to continue.")
    st.stop()

# -----------------------------
# DATE INPUTS
# -----------------------------
st.markdown(
    "Add dates for your data series that you want to include in your report "
    "(Use: YYYY-MM-DD). When you're ready, click **Load Data** and then type "
    "**generate report** to download a CSV of the selected series."
)

start_date_input = st.text_input("Start date (YYYY-MM-DD)", value="2020-01-01")
end_date_input = st.text_input("End date (YYYY-MM-DD)", value="2029-01-01")

try:
    start_date = str(pd.to_datetime(start_date_input).date())
    end_date = str(pd.to_datetime(end_date_input).date())
except Exception:
    st.error("Invalid date format. Please use YYYY-MM-DD.")
    st.stop()

st.markdown(f"**Start date:** {start_date} | **End date:** {end_date}")

# -----------------------------
# DATA LAYER
# -----------------------------
@st.cache_data
def build_combined(start_date, end_date):
    actuals = build_actuals(start_date, end_date)
    sep_wide = pull_sep_wide(start_date, end_date)

    actuals = actuals.copy()
    if "obs_date" not in actuals.columns:
        raise ValueError("actuals must contain 'obs_date' column")

    actuals["obs_date"] = pd.to_datetime(actuals["obs_date"], errors="coerce")
    actuals = actuals.dropna(subset=["obs_date"])
    actuals["series_name"] = (
        actuals["variable_group"].astype(str)
        + "."
        + actuals["measure"].astype(str)
        + "."
        + actuals["fred_code"].astype(str)
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

    sep_wide = sep_wide.copy()
    if sep_wide.index.inferred_type in ["integer", "mixed-integer"]:
        sep_wide.index = pd.to_datetime(sep_wide.index.astype(str), format="%Y", errors="coerce")
    else:
        sep_wide.index = pd.to_datetime(sep_wide.index, errors="coerce")

    sep_wide = sep_wide[~sep_wide.index.isna()]
    sep_wide.index.name = "obs_date"

    combined = pd.concat([actuals_wide, sep_wide], axis=1)
    combined = combined[~combined.index.isna()].sort_index()
    combined.columns = combined.columns.map(str)
    return combined

# -----------------------------
# SESSION STATE
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

if "combined_df" not in st.session_state:
    st.session_state["combined_df"] = None

# -----------------------------
# LOAD DATA BUTTON
# -----------------------------
if st.button("Load Data"):
    with st.spinner("Loading and combining data..."):
        st.session_state["combined_df"] = build_combined(start_date, end_date)
        st.success("Data loaded successfully!")

combined_df = st.session_state.get("combined_df")

if combined_df is None:
    st.info("Click **Load Data** to fetch data.")

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.header("Data Preview")

with st.sidebar.expander("Available series", expanded=False):
    if combined_df is not None:
        name_list = [(format_series_label(col), col) for col in combined_df.columns]

        # Buttons live inside the expander
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("Select All", key="select_all_btn"):
                for _, col in name_list:
                    st.session_state.selections[col] = True
                    st.session_state[f"sidebar_{col}"] = True
        with btn_col2:
            if st.button("Deselect All", key="deselect_all_btn"):
                for _, col in name_list:
                    st.session_state.selections[col] = False
                    st.session_state[f"sidebar_{col}"] = False

        for display_name, col in name_list:
            checkbox_key = f"sidebar_{col}"
            # Initialize only if not yet set
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = st.session_state.selections.get(col, False)

            include = st.checkbox(display_name, key=checkbox_key)
            # Keep selections dict in sync with the checkbox widget value
            st.session_state.selections[col] = include
    else:
        st.write("Load data first to preview available series.")

with st.sidebar.expander("Recent data", expanded=False):
    if combined_df is not None:
        st.dataframe(combined_df.tail(10))
    else:
        st.write("Load data first to preview recent data.")

with st.sidebar.expander("Data Series You Have Selected", expanded=False):
    selected = get_selected_series()
    if selected:
        for s in selected:
            st.write(format_series_label(s))
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
            for display_name in msg.get("display_names", []):
                st.write(f"**{display_name}**")

        elif msg["type"] == "multi_series_preview":
            all_names = msg["series_names"]
            valid = [s for s in all_names if combined_df is not None and s in combined_df.columns]
            if valid:
                options = {format_series_label(s): s for s in valid}
                chosen_label = st.selectbox(
                    "Select series to preview",
                    list(options.keys()),
                    key=f"preview_select_{i}"
                )
                series_name = options[chosen_label]
                series = combined_df[series_name].dropna()
                plot_df = pd.DataFrame({
                    "date": series.index,
                    "value": pd.to_numeric(series, errors="coerce")
                }).dropna()
                st.line_chart(plot_df, x="date", y="value")

                current_val = st.session_state.selections.get(series_name, False)
                include = st.checkbox(
                    f"Include {series_name}",
                    value=current_val,
                    key=f"history_include_{i}_{series_name}"
                )
                st.session_state.selections[series_name] = include

                with st.expander("Underlying data"):
                    st.dataframe(series.tail(20))

        elif msg["type"] == "report":
            st.write(msg["content"])
            included = get_selected_series()
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
prompt = st.chat_input(
    "Ask for a series (e.g. 'inflation', 'GDP', 'labor market') or type 'generate report'"
)

model = load_embedding_model()

if prompt:
    st.session_state.query = prompt
    add_message("user", "text", prompt)

    if combined_df is None:
        add_message(
            "assistant", "text",
            "Please click **Load Data** first so I can search your available series."
        )

    elif "report" in prompt.lower():
        st.session_state.matches = []
        add_message(
            "assistant", "report",
            "I've prepared your report from the series you selected."
        )

    else:
        matches = search_local_series(prompt, model, combined_df)
        st.session_state.matches = matches

        if matches:
            if len(matches) == 1:
                add_message("assistant", "text", f"I found a strong match for **{prompt}**.")
            else:
                display_names = [format_series_label(m) for m in matches]
                add_message(
                    "assistant", "matches",
                    f"I found a few relevant series for **{prompt}**. Here are the best matches:",
                    display_names=display_names,
                    matches=matches
                )

            add_message("assistant", "multi_series_preview", series_names=matches)

        else:
            add_message(
                "assistant", "text",
                f"I could not find a close match in your preloaded dataset for **{prompt}**. I will check FRED API Search for additional series."
            )

            try:
                series_ids = get_fred_series_from_gemini(
                    prompt, gemini_model,
                    combined_df.columns.tolist(),
                    fred_api_key
                )
            except Exception as e:
                series_ids = ['']
                add_message("assistant", "text", f"I ran into an issue while checking Gemini: {e}")

            valid_series_ids = [sid for sid in series_ids if str(sid).strip()]

            if valid_series_ids:
                combined_df, added_matches = add_fred_series_to_dataframe(series_ids, fred, combined_df)
                st.session_state["combined_df"] = combined_df
                st.session_state.matches = added_matches

                if added_matches:
                    labels = [format_series_label(m) for m in added_matches]
                    add_message(
                        "assistant", "matches",
                        f"I found new FRED series related to **{prompt}** and added them to your workspace:",
                        display_names=labels,
                        matches=added_matches
                    )

                    add_message("assistant", "multi_series_preview", series_names=added_matches)
                else:
                    add_message(
                        "assistant", "text",
                        "I searched FRED but could not pull in a usable series for that request."
                    )
            else:
                add_message(
                    "assistant", "text",
                    "I could not find a good match in either your local dataset or FRED. Try a more specific economic term like **core CPI**, **real GDP**, or **unemployment rate**."
                )

    st.rerun()

# the chat handler (above) are reflected in the report and bottom preview panel to get new added data if searched from outside via FRED
combined_df = st.session_state.get("combined_df")

# -----------------------------
# REPORT GENERATION
# -----------------------------
if st.session_state.query and "report" in st.session_state.query.lower():
    included = get_selected_series()
    if not included:
        st.warning("No series selected.")
    elif combined_df is not None:
        df_report = combined_df[included]
        out = df_report.reset_index()
        csv = out.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            "fred_report.csv",
            key="download_bottom"
        )

#to run : .venv\Scripts\Activate cd src python -m streamlit run agent_app.py