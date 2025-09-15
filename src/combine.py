import numpy as np
from utils.sep_utils import pull_sep_wide, sep_wide_to_long
from utils.actuals_utils import build_actuals

# ---------- Merge projections + actuals ----------
def build_combined() -> pd.DataFrame:
    sep_wide = pull_sep_wide()
    sep_long = sep_wide_to_long(sep_wide)
    actuals = build_actuals()
    combined = pd.concat([sep_long, actuals], ignore_index=True)
    combined = combined.sort_values(["variable_group","year","type","measure"]).reset_index(drop=True)
    combined["value"] = combined["value"].fillna(np.nan)  # or leave as NaN
    return combined, sep_wide

if __name__ == "__main__":
    combined, sep_wide = build_combined()
    combined.to_csv("sep_with_actuals_tidy.csv", index=False)
    sep_wide.to_csv("sep_only_wide.csv", index=True)
    print("Wrote:")
    print("  - sep_with_actuals_tidy.csv  (projections + actuals, tidy/long)")
    print("  - sep_only_wide.csv          (SEP projections only, wide)")
    print("\nPreview:")
    print(combined.head(20).to_string(index=False))