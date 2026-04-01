import google.generativeai as genai

# -----------------------------
# GEMINI MODEL FUNCTION
# -----------------------------
def get_fred_series_from_gemini(prompt, gemini_model):
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
        return e