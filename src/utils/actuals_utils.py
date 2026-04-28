import pandas as pd
#from config import start_date, end_date
from utils.fred_utils import fred_call

#edits will be made here if you want to add on more macroeconomic data
def build_actuals(start_date, end_date) -> pd.DataFrame:
    """Build actuals for GDP, Unemployment, Fed Funds, PCE, Core PCE, and additional added on data."""

    # Helper function to finalize the DataFrame
    def finalize(series, variable_group, measure, fred_code, month_day=None):
        #inputs: series (series) - the data series to finalize, variable_group (str) - the variable group name, measure (str) - the measurment name, fred_code (str) - the FRED code from source
        # month_day (str) - optional month and day string to append to the year for obs_date, if None will default to the index in series
        df = series.to_frame("value")
        # normalize index to integer years
        if isinstance(df.index, pd.PeriodIndex):
            years = df.index.year
        elif isinstance(df.index, pd.DatetimeIndex):
            years = df.index.year
        else:
            years = df.index.astype(int)

        df.index = years
        df.index.name = "year"

        # construct obs_date safely
        if month_day is not None:
            df["obs_date"] = pd.to_datetime(df.index.map(str) + month_day)
        else:
            df["obs_date"] = pd.to_datetime(df.index.map(str))

        # metadata
        df["variable_group"] = variable_group
        df["measure"] = measure
        df["fred_code"] = fred_code
        df["type"] = "actual"
        df["source"] = "actuals"
        return df

    # --- Beginning of Actuals: You can make adjustments here and add additional data here ---

    # --- GDP: real GDP (GDPC1), Q4/Q4 % ---
    gdp = fred_call("GDPC1", start_date, end_date) #real gross domestic product, done as part of q4 ending percentage, seasonally adjusted
    gdp_q4 = gdp.resample("QE").last().to_period("Q") #pull Q4 data
    gdp_q4 = gdp_q4[gdp_q4.index.quarter == 4]
    gdp_q4q4 = (gdp_q4 / gdp_q4.shift(1) - 1) * 100 #make is percent
    gdp_q4q4.index = gdp_q4q4.index.year
    gdp_final = finalize(gdp_q4q4, "gdp", "actual_q4q4", "GDPC1", month_day='-12-31') #month_day input forces to end of month in this case

    # --- Unemployment: UNRATE, Q4 average ---
    u = fred_call("UNRATE", start_date, end_date) # unemployment rate at the end of q4 for a given year, raw data taken monthly, seasonally adjusted
    u_q = u.resample("QE").mean()
    u_q4 = u_q[u_q.index.quarter == 4]
    u_q4.index = u_q4.index.year
    u_final = finalize(u_q4, "unemployment", "actual_q4_avg", "UNRATE", month_day='-12-31')

    # --- Fed Funds: FEDFUNDS, year-end value ---
    f = fred_call("FEDFUNDS", start_date, end_date) #fed funds interest rate at year end, values taken at end of the day daily from raw data, not seasonally adjusted
    f_m = f.resample("ME").last()
    f_yend = f_m[f_m.index.month == 12]
    f_yend.index = f_yend.index.year
    f_final = finalize(f_yend, "fed_funds", "actual_yearend", "FEDFUNDS", month_day='-12-31')

    # --- PCE: PCECTPI, Q4/Q4 % ---
    pce = fred_call("PCECTPI", start_date, end_date) #PCE price index of inflation in chain type, done as part of q4 ending percentage, seasonally adjusted
    pce_q4 = pce.resample("QE").last().to_period("Q")
    pce_q4 = pce_q4[pce_q4.index.quarter == 4]
    pce_q4q4 = (pce_q4 / pce_q4.shift(1) - 1) * 100
    pce_q4q4.index = pce_q4q4.index.year
    pce_final = finalize(pce_q4q4, "pce", "actual_q4q4", "PCECTPI", month_day='-12-31')

    # --- Core PCE: PCEPILFE, Q4/Q4 % ---
    core = fred_call("PCEPILFE", start_date, end_date) #PCE price index less food and energy, done as part of q4 ending percentage, seasonally adjusted
    core_q4 = core.resample("QE").last().to_period("Q")
    core_q4 = core_q4[core_q4.index.quarter == 4]
    core_q4q4 = (core_q4 / core_q4.shift(1) - 1) * 100
    core_q4q4.index = core_q4q4.index.year
    core_final = finalize(core_q4q4, "core_pce", "actual_q4q4", "PCEPILFE", month_day='-12-31')

    # --- Additional Historical Data Additions that may be relevant Beyond SEP Data ---

    # --- Actuals: NBER recession indicator ---
    #see here on information on NBER recession indicators: https://www.nber.org/research/business-cycle-dating/business-cycle-dating-procedure-frequently-asked-questions
    rec = fred_call("USRECQ", start_date, end_date) #original data is calculated quarterly at end of the quarter with no seasonal adjustments, 1 if recession, 0 if not
    rec_q = rec.resample("QE").max() #pulling quarterly info
    rec_q.index.name = "obs_date"
    rec_q = rec_q.to_frame("value")
    rec_q["variable_group"] = "recession"
    rec_q["measure"] = "nber_recession"
    rec_q["fred_code"] = "USRECQ"
    rec_q["type"] = "actual"
    rec_q["source"] = "actuals"
    rec_final = rec_q.reset_index()

    # --- Actuals: Sticky Price Consumer Price Index (CPI) ---
    cpi = fred_call("STICKCPIM157SFRBATL", start_date, end_date) #original data is calculated monthly at end of the month while also accounting for seasonal adjustments, percent change
    cpi_q = cpi.resample("QE").last() #gets at the end of quarter
    cpi_q.index.name = "obs_date"
    cpi_q = cpi_q.to_frame("value")
    cpi_q["variable_group"] = "inflation_sticky"
    cpi_q["measure"] = "sticky_price_cpi"
    cpi_q["fred_code"] = "STICKCPIM157SFRBATL"
    cpi_q["type"] = "actual"
    cpi_q["source"] = "actuals"
    cpi_final = cpi_q.reset_index()

    # --- Actuals: Median Consumer Price Index (CPI) ---
    cpi_median = fred_call("MEDCPIM158SFRBCLE", start_date, end_date) #original data is calculated monthly at end of the month while also accounting for seasonal adjustments, annual percent change
    cpi_median_q = cpi_median.resample("QE").last() #gets at the end of quarter
    cpi_median_q.index.name = "obs_date"
    cpi_median_q = cpi_median_q.to_frame("value")
    cpi_median_q["variable_group"] = "inflation_median"
    cpi_median_q["measure"] = "median_price_cpi"
    cpi_median_q["fred_code"] = "MEDCPIM158SFRBCLE"
    cpi_median_q["type"] = "actual"
    cpi_median_q["source"] = "actuals"
    cpi_median_final = cpi_median_q.reset_index()

    # --- Actuals: Auto Diesel Fuel Costs in US Urban Metros (PPG) ---
    auto_diesel = fred_call("APU000074717", start_date, end_date) #original data is calculated monthly at end of the month with no seasonal adjustments, us dollars per gallon
    auto_diesel_q = auto_diesel.resample("QE").last() #gets at the end of quarter
    auto_diesel_q.index.name = "obs_date"
    auto_diesel_q = auto_diesel_q.to_frame("value")
    auto_diesel_q["variable_group"] = "fuel_price"
    auto_diesel_q["measure"] = "auto_diesel_price"
    auto_diesel_q["fred_code"] = "APU000074717"
    auto_diesel_q["type"] = "actual"
    auto_diesel_q["source"] = "actuals"
    auto_diesel_final = auto_diesel_q.reset_index()

    # --- Actuals: Consumer Price Index for Fuel Oil and Other Fuels in US Urban Metros (indexed from 1982-1984=100) ---
    fuel_oil = fred_call("CUSR0000SEHE", start_date, end_date) #original data is calculated monthly at end of the month while also accounting for seasonal adjustments, index at 100 for average in 1982-1984
    fuel_oil_q = fuel_oil.resample("QE").last() #gets at the end of quarter
    fuel_oil_q.index.name = "obs_date"
    fuel_oil_q = fuel_oil_q.to_frame("value")
    fuel_oil_q["variable_group"] = "inflation_fuel"
    fuel_oil_q["measure"] = "fuel_oil_cpi"
    fuel_oil_q["fred_code"] = "CUSR0000SEHE"
    fuel_oil_q["type"] = "actual"
    fuel_oil_q["source"] = "actuals"
    fuel_oil_final = fuel_oil_q.reset_index()

    # --- Look Aheads: X-Month Macroeconomic Uncertainty ---
    #these next 3 values may assist in trustability in our other macroeconomic projections
    #see: http://dx.doi.org/10.1257/aer.20131193 for reference on this info (Jurado, ludvigson, Ng (2015) Measuring Uncertainty)
    #3 month
    look_ahead3m = fred_call("JLNUM3M", start_date, end_date) #original data is calculated monthly at end of the month while scaled from a 3 month look ahead
    look_ahead3m_q = look_ahead3m.resample("QE").last() #gets at the end of quarter
    look_ahead3m_q.index.name = "obs_date"
    look_ahead3m_q = look_ahead3m_q.to_frame("value")
    look_ahead3m_q["variable_group"] = "macroeconomic_uncertainty"
    look_ahead3m_q["measure"] = "3_month_look_ahead"
    look_ahead3m_q["fred_code"] = "JLNUM3M"
    look_ahead3m_q["type"] = "actual"
    look_ahead3m_q["source"] = "actuals"
    look_ahead_final_3m = look_ahead3m_q.reset_index()

    #1 month
    look_ahead1m = fred_call("JLNUM1M", start_date, end_date) #original data is calculated monthly at end of the month while scaled from a 1 month look ahead
    look_ahead1m_q = look_ahead1m.resample("QE").last() #gets at the end of quarter
    look_ahead1m_q.index.name = "obs_date"
    look_ahead1m_q = look_ahead1m_q.to_frame("value")
    look_ahead1m_q["variable_group"] = "macroeconomic_uncertainty"
    look_ahead1m_q["measure"] = "1_month_look_ahead"
    look_ahead1m_q["fred_code"] = "JLNUM1M"
    look_ahead1m_q["type"] = "actual"
    look_ahead1m_q["source"] = "actuals"
    look_ahead_final_1m = look_ahead1m_q.reset_index()

    #1 year
    look_ahead1y = fred_call("JLNUM12M", start_date, end_date) #original data is calculated monthly at end of the month while scaled from a 12 month look ahead
    look_ahead1y_q = look_ahead1y.resample("QE").last() #gets at the end of quarter
    look_ahead1y_q.index.name = "obs_date"
    look_ahead1y_q = look_ahead1y_q.to_frame("value")
    look_ahead1y_q["variable_group"] = "macroeconomic_uncertainty"
    look_ahead1y_q["measure"] = "1_year_look_ahead"
    look_ahead1y_q["fred_code"] = "JLNUM12M"
    look_ahead1y_q["type"] = "actual"
    look_ahead1y_q["source"] = "actuals"
    look_ahead_final_1y = look_ahead1y_q.reset_index()

    # Combine all data for final output
    actuals = pd.concat([gdp_final, u_final, f_final, pce_final, core_final, rec_final, cpi_final, cpi_median_final, auto_diesel_final, fuel_oil_final, look_ahead_final_3m, look_ahead_final_1m, look_ahead_final_1y])
    actuals.index.name = "year"
    actuals.reset_index(inplace=True)
    return actuals