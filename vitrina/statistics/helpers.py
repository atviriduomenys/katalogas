from datetime import datetime

import pandas as pd


def get_start_date_based_on_frequency(frequency, end_date):
    if frequency == 'Y':
        return datetime(2019, 1, 1)
    elif frequency == 'Q':
        return end_date - pd.DateOffset(years=2)  # last 2 years if quarterly
    elif frequency == 'M':
        return end_date - pd.DateOffset(years=1)  # last year if monthly
    elif frequency == 'W':
        return end_date - pd.DateOffset(months=6)  # last 6 months if weekly
    elif frequency == 'D':
        return end_date - pd.DateOffset(months=1)  # last month if daily
    else:
        # default to yearly
        return datetime(2019, 1, 1)