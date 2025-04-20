
import os
import pandas as pd
from datetime import datetime

CSV_DIR = "/Users/viveksaini/Documents/scripts/processed/portfolio_stocks"

def load_filtered_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    all_data = []
    for file in os.listdir(CSV_DIR):
        if file.endswith(".csv"):
            df = pd.read_csv(os.path.join(CSV_DIR, file))
            all_data.append(df)
    
    if not all_data:
        return pd.DataFrame()

    df = pd.concat(all_data, ignore_index=True)
    df["date_of_filing"] = pd.to_datetime(df["date_of_filing"], errors="coerce")
    return df[(df["date_of_filing"] >= pd.to_datetime(start_date)) & (df["date_of_filing"] <= pd.to_datetime(end_date))]
