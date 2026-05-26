import logging
import pandas as pd
from pandas_datareader import data as pdr

logger = logging.getLogger(__name__)

# ---------- Helper to fetch FRED series ----------
def fred_call(code: str, start_date: str, end_date: str) -> pd.Series:
    # Fetch data from FRED. On failure, returns an empty Series whose .attrs["fred_error"]
    # holds the exception message so callers can detect and surface the failure.
    # Inputs: code (str) - FRED series code, start_date (str) - start date desired, end_date (str) - end date desired
    try:
        s = pdr.DataReader(code, "fred", start=start_date, end=end_date)[code]
        s.name = code
        s.attrs["fred_error"] = None
        return s
    except Exception as e:
        msg = f"Could not fetch FRED series {code}: {e}"
        logger.warning(msg)
        empty = pd.Series(dtype=float, name=code)
        empty.attrs["fred_error"] = str(e)
        return empty
