import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

def show_bse_insider_trades(ticker_symbol):
    try:
        end_date = datetime.today()
        start_date = end_date - timedelta(days=90)

        from_date = start_date.strftime('%d/%m/%Y')
        to_date = end_date.strftime('%d/%m/%Y')

        url = 'https://www.bseindia.com/corporates/Insider_Trading_new.aspx'

        params = {
            'strFromDate': from_date,
            'strToDate': to_date,
            'strType': 'C',
            'strCompany': '',
            'strRegClause': '-1',
            'ddlType': 'C',
            'ddlClause': '-1',
            'txtSecurity': ticker_symbol,
            'ddlPeriod': '3M',
            'btnSubmit': 'Submit'
        }

        response = requests.post(url, data=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)

        if response.status_code != 200:
            st.warning("Could not fetch insider trades from BSE.")
            return

        tables = pd.read_html(response.text)
        if not tables:
            st.info("No insider trade data found.")
            return

        df = tables[0]
        if df.empty:
            st.info(f"No insider trades for {ticker_symbol} in the past 3 months.")
        else:
            st.subheader(f"🕵️ Insider Trades for {ticker_symbol} (Last 3 Months - BSE)")
            st.dataframe(df)
    except Exception as e:
        st.error(f"Error loading insider trades: {e}")
