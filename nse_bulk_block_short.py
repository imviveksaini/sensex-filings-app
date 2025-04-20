# nse_bulk_block_short.py
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta


def get_nse_session() -> requests.Session:
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Referer': 'https://www.nseindia.com'
    }
    session.get('https://www.nseindia.com', headers=headers, timeout=10)
    session.headers.update(headers)
    return session


def fetch_nse_deals(symbol: str, period_days: int = 90):
    """
    Returns three DataFrames: bulk deals, block deals, and short-selling data for the symbol.
    """
    session = get_nse_session()
    end = datetime.today()
    start = end - timedelta(days=period_days)
    params = {
        'from': start.strftime('%d-%m-%Y'),
        'to': end.strftime('%d-%m-%Y')
    }
    base = 'https://www.nseindia.com/api/historical'
    dfs = {}
    for key in ['bulk-deals', 'block-deals', 'short-selling']:
        url = f"{base}/{key}"
        try:
            res = session.get(url, params=params, timeout=10)
            res.raise_for_status()
            data = res.json().get('data', [])
            df = pd.DataFrame(data)
            if not df.empty:
                dfs[key] = df[df['symbol'].str.upper() == symbol.upper()]
            else:
                dfs[key] = df
        except Exception:
            dfs[key] = pd.DataFrame()
    return dfs.get('bulk-deals', pd.DataFrame()), dfs.get('block-deals', pd.DataFrame()), dfs.get('short-selling', pd.DataFrame())


def show_nse_bulk_block_short_deals(symbol: str):
    bulk, block, short = fetch_nse_deals(symbol)
    if not bulk.empty:
        st.subheader('Bulk Deals')
        st.dataframe(bulk)
    if not block.empty:
        st.subheader('Block Deals')
        st.dataframe(block)
    if not short.empty:
        st.subheader('Short Selling')
        st.dataframe(short)
    if bulk.empty and block.empty and short.empty:
        st.info('No NSE deals data found for ' + symbol)