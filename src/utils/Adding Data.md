# Adding Data to Outputs

This guide will dicuss how to add data to your output reports.

## Instructions

1. Read `notebook research code` and use it to find additional data and the official code to pull historical data. You may want to adjust the `start_date` and `end_date` depending on the timeframe of the data you want.

2. Once you get the data code. Add the following code the below Line 179 in `actuals_utils.py`. Make sure to instantiate the names to something reasonable:

Pull the code using the `fred()` function using the FRED Data Idenifier key, start date, and end date. In the example of GDP Projected Median that code would be `GDPC1MD`.

Use the `resample()` function to get the proper date and save that. For example a quarterly reported data should have the value at quarter end.

Set up the observation date `obs_date`, variable group (data type cateogry like fuel price, economic uncertanty, and cpi) `variable_group`, measurement type (1-month, quarterly, look ahead) `measure`, projection/actual `type`, sourcing type `source`, and fred id code `fred_code` as part of the dataframe and reset the index.

3. Concat the data into the `acutals` dataframe as part of the final output it should be in the 4th to last line in the `actual_utils.py` file.