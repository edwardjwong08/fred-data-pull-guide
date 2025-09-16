# ---------- SEP projection series (verified FRED IDs) ----------
SEP_SERIES = {
    "gdp": { #gdp projections, all not seasonally adjusted
        "median": "GDPC1MD", #only 3 years out
        "central_tendency_midpoint": "GDPC1CTM", #only 3 years out
        "range_midpoint": "GDPC1RM", #only 3 years out
        "longer_run_central_tendency_midpoint": "GDPC1CTMLR", #at this time includes projections from historical time
    },
    "unemployment": { #unemployment projections, all not seasonally adjusted
        "median": "UNRATEMD", #only 3 years out
        "central_tendency_midpoint": "UNRATECTM", #only 3 years out
        "range_midpoint": "UNRATERM", #only 3 years out
        "longer_run_central_tendency_midpoint": "UNRATECTMLR", #at this time includes projections from historical time
    },
    "fed_funds": { #fed funds interest rate projections, all not seasonally adjusted
        "median": "FEDTARMD", #only 3 years out
        "central_tendency_midpoint": "FEDTARCTM", #only 3 years out
        "range_midpoint": "FEDTARRM", #only 3 years out
        "longer_run_central_tendency_midpoint": "FEDTARCTMLR", #at this time includes projections from historical time
    },
    "pce": { #pce inflation projections, all not seasonally adjusted, no longer run CTM
        "median": "PCECTPIMD", #only 3 years out
        "central_tendency_midpoint": "PCECTPICTM", #only 3 years out
        "range_midpoint": "PCECTPIRM" #only 3 years out
    },
    "core_pce": { #core pce inflation projections, all not seasonally adjusted, no longer run CTM
        "median": "JCXFEMD", #only 3 years out
        "central_tendency_midpoint": "JCXFECTM", #only 3 years out
        "range_midpoint": "JCXFERM" #only 3 years out
    }
}

# ---------- Start and End Dates for Data Pull ----------
# change these to your desired timeframe, format YYYY-MM-DD
start_date = "2020-01-01"
end_date = "2029-01-01"