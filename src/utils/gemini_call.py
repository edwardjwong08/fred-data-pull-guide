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