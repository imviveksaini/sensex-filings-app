# bse_insider_trades.py
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta


@st.cache_data
def fetch_bse_insider_trades(symbol: str, period_days: int = 90) -> pd.DataFrame:
    """
    Fetch insider trading disclosures from BSE for a given symbol over the past period_days.
    Returns a DataFrame with columns such as ClientName, DealDate, TransType, Quantity, Price.
    """
    end_date = datetime.today()
    start_date = end_date - timedelta(days=period_days)
    params = {
        'strFromDate': start_date.strftime('%d/%m/%Y'),
        'strToDate': end_date.strftime('%d/%m/%Y'),
        'strType': 'C',        # Company
        'ddlType': 'C',        # Company
        'txtSecurity': symbol,
        'ddlPeriod': '3M',
        'btnSubmit': 'Submit'
    }
    url = 'https://www.bseindia.com/corporates/Insider_Trading_new.aspx'
    headers = { 'User-Agent': 'Mozilla/5.0' }
    res = requests.post(url, data=params, headers=headers, timeout=15)
    res.raise_for_status()
    try:
        tables = pd.read_html(res.text)
        df = tables[0]
        df.columns = [c.strip() for c in df.columns]
        return df
    except ValueError:
        return pd.DataFrame()


def show_bse_insider_trades(symbol: str):
    df = fetch_bse_insider_trades(symbol)
    if df.empty:
        st.info('No insider trade data found for ' + symbol)
    else:
        st.dataframe(df)