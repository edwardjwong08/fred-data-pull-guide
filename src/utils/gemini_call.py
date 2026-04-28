import ast
import google.generativeai as genai
from fredapi import Fred

# -----------------------------
# GEMINI MODEL FUNCTION
# -----------------------------
def get_fred_series_from_gemini(prompt, gemini_model, available_series, fred_api_key):
    """
    Try to match the user request to:
    1) existing local available series
    2) likely FRED series IDs if no local match exists

    Returns:
        list[str] -> FRED series IDs or ['']
    """

    # If Gemini isn't available, fall back directly to FRED search
    if not gemini_model:
        return search_fred_for_series(prompt, fred_api_key)

    try:
        formatted_series = []

        for col in available_series:
            parts = str(col).split(".")
            if len(parts) >= 3:
                formatted_series.append({
                    "topic": parts[0],
                    "measure": parts[1],
                    "fred_id": parts[2]
                })
            else:
                formatted_series.append({
                    "topic": str(col),
                    "measure": "",
                    "fred_id": ""
                })

        response = gemini_model.generate_content(f"""
        The user is searching for an economic data series.

        Available local data:
        {formatted_series}

        Each local series has:
        - topic
        - measure
        - fred_id

        Your job:
        1. If the user request matches the available local data, return the best matching fred_id(s)
        2. If there is no local match, infer the most likely FRED series ID(s) the user wants
        3. If you cannot infer any useful FRED ID, return ['']

        Rules:
        - Return ONLY a valid Python list of strings
        - No explanation
        - No markdown
        - No code fences
        - If one match, return a one-item list
        - If multiple matches, return all relevant IDs
        - If nothing useful can be inferred, return ['']

        Example (Exact match):
        Input: GDP actuals year end
        Output: ['GDPC1']
        
        Example (Multiple matches):
        Input: macroeconomic uncertainty
        Output: ['JLNUM12M', 'JLNUM3M', 'JLNUM1M']

        Example (No match):
        Input: average height of presidents
        Output: ['']

        User input: {prompt}
        Output:
""")

        raw_text = response.text.strip() if response.text else "['']"
        raw_text = raw_text.replace("```python", "").replace("```", "").strip()

        series_ids = ast.literal_eval(raw_text)

        if isinstance(series_ids, str):
            series_ids = [series_ids]
        elif not isinstance(series_ids, list):
            series_ids = ['']

        cleaned = [str(x).strip().upper() for x in series_ids if str(x).strip()]

        if cleaned and cleaned != ['']:
            return cleaned

        return search_fred_for_series(prompt, fred_api_key)

    except Exception as e:
        print("Gemini parsing error, falling back to FRED search:", e)
        return search_fred_for_series(prompt, fred_api_key)


def get_fred_series_info(fred_id, fred_api_key):
    """
    Fetch metadata for a FRED series ID and return a structured dict with:
    title, frequency, units, seasonal_adjustment, and notes.
 
    Args:
        fred_id (str): The FRED series ID (e.g. 'CPIAUCSL')
        fred_api_key (str): FRED API key
 
    Returns:
        dict with keys: fred_id, title, frequency, units, seasonal_adjustment, notes
        Returns a dict with empty strings on failure.
    """
    empty = {
        "fred_id": fred_id.upper(),
        "title": "",
        "frequency": "",
        "units": "",
        "seasonal_adjustment": "",
        "notes": "",
    }
 
    try:
        fred = Fred(api_key=fred_api_key)
        info = fred.get_series_info(fred_id)
 
        return {
            "fred_id":             fred_id.upper(),
            "title":               str(info.get("title", "")),
            "frequency":           str(info.get("frequency", "")),
            "units":               str(info.get("units", "")),
            "seasonal_adjustment": str(info.get("seasonal_adjustment", "")),
            "notes":               str(info.get("notes", "")).strip(),
        }
 
    except Exception as e:
        print(f"get_fred_series_info failed for {fred_id}: {e}")
        return empty
 
 
def search_fred_for_series(prompt, fred_api_key):
    """
    Fallback FRED search if Gemini doesn't find or parse a result.
    Returns top 5 matching FRED IDs.
    """
    try:
        fred = Fred(api_key=fred_api_key)
        results = fred.search(prompt)

        if results.empty:
            return ['']

        return results["id"].head(5).astype(str).tolist()

    except Exception as e:
        print("FRED search error, please try again:", e)
        return ['']
    
# -----------------------------
# SERIES LABEL ENRICHMENT
# -----------------------------
def get_enriched_column_name(fred_id, fred_api_key, gemini_model):
    """
    Given a FRED series ID, fetch its metadata and use Gemini to produce
    a structured column name in the format: topic.measure.FREDID

    Falls back to 'external.user_query.FREDID' if anything fails.

    Args:
        fred_id (str): The FRED series ID (e.g. 'CPIAUCSL')
        fred_api_key (str): FRED API key
        gemini_model: Configured Gemini GenerativeModel instance, or None

    Returns:
        str: Column name in topic.measure.FREDID format
    """
    fallback = f"other_topic.measure.{fred_id.upper()}"

    try:
        fred = Fred(api_key=fred_api_key)
        info = fred.get_series_info(fred_id)

        title      = info.get("title", "")
        units      = info.get("units_short", info.get("units", ""))
        frequency  = info.get("frequency_short", info.get("frequency", ""))
        notes      = str(info.get("notes", ""))[:300]   # trim long notes

        if not title:
            return fallback

        # If no Gemini, do a simple heuristic split
        if not gemini_model:
            parts = title.split(":")
            topic   = parts[0].strip().replace(" ", "_").lower() if len(parts) >= 2 else "economic_data"
            measure = parts[1].strip().replace(" ", "_").lower() if len(parts) >= 2 else title.strip().replace(" ", "_").lower()
            return f"{topic}.{measure}.{fred_id.upper()}"

        response = gemini_model.generate_content(f"""
            You are labelling an economic data series for use as a dataframe column name.

            Given the FRED series metadata below, produce a column name in the exact format:
            topic.measure.{fred_id.upper()}

            Rules:
            - topic: a short snake_case economic category (e.g. inflation, gdp, macoreconomic_uncertaintly, interest_rates, gold, pce, unemployment)
            - measure: a short snake_case descriptor of what is measured for projections or actuals and a timeframe(e.g. actuals_q4, actuals_daily, actuals_year_end, projection_q1, projection_year_end, projection_monthly)
            - Use only lowercase letters, digits, and underscores in topic and measure
            - No spaces, no hyphens, no special characters
            - Return ONLY the column name string, nothing else

            Series metadata:
            Title: {title}
            Units: {units}
            Frequency: {frequency}
            Notes: {notes}

            Output:
            """)

        raw = response.text.strip() if response.text else ""
        raw = raw.replace("```", "").strip()

        # Validate it has the right structure: two dots, ends with fred_id
        parts = raw.split(".")
        if (
            len(parts) == 3
            and parts[2].upper() == fred_id.upper()
            and all(p.replace("_", "").replace("-", "").isalnum() for p in parts[:2])
        ):
            return f"{parts[0].lower()}.{parts[1].lower()}.{fred_id.upper()}"

        return fallback

    except Exception as e:
        print(f"Label enrichment failed for {fred_id}: {e}")
        return fallback