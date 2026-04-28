import pandas as pd
from pandas_datareader import data as pdr

# ---------- Helper to fetch FRED series ----------
def fred_call(code: str, start_date: str, end_date: str) -> pd.Series:
    # Fetch data from FRED
    # Inputs: code (str) - FRED series code, start_date (str) - start date desired, end_date (str) - end date desired
    try:
        s = pdr.DataReader(code, "fred", start = start_date, end = end_date)[code] #select data during this period
        s.name = code
        return s
    except Exception as e:
        print(f"Warning: Could not fetch {code} ({e})")
        return pd.Series(dtype=float)
