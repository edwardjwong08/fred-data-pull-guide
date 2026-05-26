# FRED Research Agent (For All)

[Visit the FRED Agent Here](https://connect.posit.cloud/ejwong08/content/019e1d68-dd4a-dfe5-8b6a-7d95dcc0154c)

This is an custom AI Agent which will help users pull historic economic data reports published by the Frederal Reserve of St. Louis including projections of the SEP (Summary of Economic Projections) Series and other measurements of interest. This agent pulls data within the desired timeframe and allows for customized data to be added that a user may want or is interested in researching in. If you are interested for a more techincal guide to manually pull the data, view the guide below.

##  FRED Data Pull Guide (For Analysts)

This is a quick guide to pull historic economic data published by the Frederal Reserve of St. Louis along with projections of the SEP (Summary of Economic Projections) Series. This guide walks through how to pull the data and adding to a customized data pull for various economic data that a user may want.

The goal for this project is to show how to pull data generally off of the Federal Reserve's Database called FRED. While this project primarily focuses on pulling the SEP Projection Series, which is a general economic series of data projections for economic variables like GDP growth, interest rates, unemployment, and personal consumption expenditure (inflation), I have also included some additional data pulls for economic indicators that may be of assistance.

## Important Notes Before You Get Started


1. Some of these features may be re-named, codes adjusted, or depreciated at any given time for which you may want to check on the Fed Reserve of St. Louis' website.


2. Be careful in the data that you collect to make sure that it is properly labeled in your output to see if it is future projections, historical projections, percentages, indices, historical actuals, the value's scale, seasonally adjusted, etc. If you do not you may get misleading results.


3. Some variables may need to be lagged and adjusted depending on end date or the lookback period. They may also be measures at the beginning of the month, end of the month, quarter, and so on. Make sure to adjust with your given use case using the documentation online at the St. Louis Fed's website and have discussion with others on how to add these to your feature store.

4. There is an ipynb file which completes the same steps as the instructions below which may be helpful. It also includes simple plotting which may be of use.

## Instructions to Run for Output

1. Go to https://fred.stlouisfed.org/docs/api/api_key.html to register and request an api key. Insert it in the below cell. Do not share it or feed it to an LLM as it will cause potential negative ramifications.

2. In the file `src/config.py` adjust the start date `start_date` and end date `end_date` for the overall period you want to measure. There is no guarantee that there will be available data for a given timeframe but you can measure it accordingly or leave certain timeframes blank.

3. Go to the summary of economic projections under sources https://fred.stlouisfed.org/release?rid=326 to confirm that your SEP_SERIES is up to date. Currently there are 5 categories and 7 tendency measurements in the SEP Series Projections, this is subject to change. This will be done in `src/config.py`

4. Go to the function `actuals_utils` in the section 'Beginning of Actuals' (Line 39) and check to see if the current data ids included are still active in each of the `fred_call()` function. Feel free to add or remove those if desired, it must be changed in the section you did it at along with the final output in `actuals` (Line 182). Confirm the values you want to label them as to ensure consistency in the final output before appending them to `actuals` (Line 182).

> Note: `src/agent_app.py` is a parallel Streamlit front door that consumes the same `actuals_utils.py` / `sep_utils.py` modules. Any data you add or remove there will also appear in the agent app's preloaded series. Launch it with `python -m streamlit run src/agent_app.py` from the project root (after activating `.venv`).

5. Navigate and run the code and observe the 2 output files which are explained in the next step. To run the code follow the one of the steps below depending on what file manager you are using.

If using the UV Package Manager (recommended): To get all of the output data run the command in your UV terminal `python makefile.py all` or `python makefile.py run`, to preview the data run `python makefile.py preview`, and to purge previous outputted files run `python makefile.py clean`.

If using anything else: To get all of the output data run the command in your UV terminal `make all` or `make run`, to preview the data run `make preview`, and to purge previous outputted files run `make clean`.

6. Check if both csv files are in the folder `output_data`. `sep_with_actuals.csv` contains the sep series projections along with the other economic variables that you have added. `sep_only_wide.csv` only contains the SEP Series Projections for your given timeframe.

## Instructions to Edit and Obtain Historical Data/Projections

1. Navigate to `config.py` and underneath the `SEP_SERIES` dictionary check that each entry for each key exists which is given by the value. For example in the key `gdp` the entry `median` has a key value `GDP1MD` which correspondes to the median projected GDP value code in the FRED database. Confirm you want all of this data and you can comment out portions you do not want.

2. Check the `start_date` and `end_date` are the dates you want. For each projection and historical data these dates may change or not be available.

3. Check that the actual codes still exists in `actuals_utils.py` and that those are wanted. If not comment out these values in `actuals` (Line 182). If you want to add more values follow navigate to `src/utils/Adding Data.md` and then continue to the last step.

4. Run and check the outputs as descibed in the previous section (Step 5 in "Instructions to Run for Output").

## Repo Organization

```
├── README.md # Start here for guide
├── Makefile # Makefile for non-UV package users
├── .gitignore
├── fred_macro_data_guide.ipynb # Notebook version of guide
├── makefile.py # Makefile for UV package users
├── requirements.txt
├── output_data # Generated CSV outputs land here
└── src
    ├── agent_app.py # Streamlit chat-style FRED data research assistant
    ├── combine.py
    ├── config.py
    └── utils
        ├── Adding Data.md # Adding data to report user guide
        ├── actuals_utils.py
        ├── fred_research.ipynb # Notebook used for FRED Data research and lookup
        ├── fred_utils.py
        ├── gemini_call.py # Gemini-assisted FRED series lookup helpers
        └── sep_utils.py
```