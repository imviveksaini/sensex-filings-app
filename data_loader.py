# data_loader.py
import os
import pandas as pd
from datetime import datetime

# Directory where per-ticker CSVs are stored
# Adjust this path to where your CSVs actually reside
default_output_dir = os.path.expanduser("~/Documents/scripts/processed/portfolio_stocks_pegasus")


def update_filings_data():
    """
    Dummy placeholder: implement your scraping+NLP pipeline here,
    returning the count of new filings added.
    """
    # For now, just return 0 new filings
    return 0


def load_filtered_data(start_date=None, end_date=None):
    """
    Reads all <TICKER>.csv files from processed/ directory,
    standardizes columns (date & ticker), concatenates into a DataFrame,
    and filters by date range (if provided).

    CSVs can have either 'date' or 'date_of_filing' columns,
    and either 'ticker' or 'ticker_name' columns.

    Returns a pandas.DataFrame with columns 'ticker_name' and 'date_of_filing'.
    """
    folder = default_output_dir
    if not os.path.isdir(folder):
        return pd.DataFrame()

    dfs = []
    for fname in os.listdir(folder):
        if not fname.lower().endswith('.csv'):
            continue
        path = os.path.join(folder, fname)
        try:
            df = pd.read_csv(path)
        except Exception:
            continue

        # Standardize date column
        if 'date' in df.columns:
            df['date_of_filing'] = pd.to_datetime(df['date'], errors='coerce')
        elif 'date_of_filing' in df.columns:
            df['date_of_filing'] = pd.to_datetime(df['date_of_filing'], errors='coerce')
        else:
            continue  # cannot find a date column

        # Standardize ticker column
        if 'ticker' in df.columns:
            df['ticker_name'] = df['ticker']
        elif 'ticker_name' in df.columns:
            df['ticker_name'] = df['ticker_name']
        else:
            # fallback to filename (without extension)
            df['ticker_name'] = os.path.splitext(fname)[0]

        # Drop rows without valid date
        df = df.dropna(subset=['date_of_filing'])
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    full = pd.concat(dfs, ignore_index=True)

    # Apply date filters
    if start_date is not None:
        start_ts = pd.to_datetime(start_date)
        full = full[full['date_of_filing'] >= start_ts]
    if end_date is not None:
        end_ts = pd.to_datetime(end_date)
        full = full[full['date_of_filing'] <= end_ts]

    return full
