import pandas as pd
from config import SEP_SERIES#, start_date, end_date
from utils.fred_utils import fred_call

# ---------- Build SEP (wide & long) ----------
def pull_sep_wide(start_date, end_date) -> pd.DataFrame:
    frames = []
    for group, codes in SEP_SERIES.items():
        for label, code in codes.items():
            s = fred_call(code, start_date, end_date).to_frame()
            s.columns = [f"{group}.{label}.{code}"]
            frames.append(s)
    wide = pd.concat(frames, axis=1).sort_index()
    return wide

def sep_wide_to_long(wide: pd.DataFrame) -> pd.DataFrame:
    long = (
        wide.reset_index()
            .rename(columns={"DATE": "obs_date"})
            .melt(id_vars=["obs_date"], var_name="series", value_name="value")
            #.dropna(subset=["value"])
    )
    parts = long["series"].str.split(r"\.", n=2, expand=True)
    long["variable_group"] = parts[0]
    long["measure"] = parts[1]
    long["fred_code"] = parts[2]
    # SEP obs_date is annual (Jan 1 as year marker). Extract projection year.
    long["year"] = pd.to_datetime(long["obs_date"]).dt.year
    long["type"] = "projection"
    return long[["year","variable_group","measure","fred_code","type","value","obs_date"]]
