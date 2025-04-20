import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import streamlit as st
from datetime import datetime

from data_loader import load_filtered_data
from filing_table import render_filing_table
from sentiment_chart import plot_sentiment_chart
from price_chart import plot_stock_price
from news_fetcher import render_news_section
from ui_theme import apply_custom_styles

from valuation_metrics import show_valuation_metrics
from shareholding_pattern import show_shareholding_pattern
#from insider_transactions import show_insider_transactions
from bse_insider_trades import show_bse_insider_trades
from nse_bulk_block_short import show_nse_bulk_block_short_deals

st.set_page_config(page_title="SENSEX Filings Viewer", layout="wide")

# LANDING PAGE
if "page" not in st.session_state:
    st.session_state.page = "landing"

if st.session_state.page == "landing":
    st.markdown(apply_custom_styles("Light"), unsafe_allow_html=True)
    st.markdown("""
    <h1 style='text-align: center;'>📊 Welcome to Your Filing Superpower</h1>
    <p style='text-align: center; font-size: 18px;'>
        Behind every stock movement lies a story...<br>
        and the story begins with <strong>company filings</strong> and <strong>earnings calls</strong>.
    </p>
    <p style='text-align: center; font-size: 16px;'>
        📁 Filings reveal the fine print.<br>
        📞 Earnings calls reveal the tone.<br>
        🕵️‍♂️ We decode both — so you don't have to squint at PDFs all day.
    </p>
    <p style='text-align: center; font-size: 16px;'>
        Whether you're a casual investor or a spreadsheet ninja 🧠 — this app helps you read between the (filing) lines.
    </p>
    """, unsafe_allow_html=True)

    if st.button("✨ Let me in!"):
        st.session_state.page = "main"
        st.rerun()

# MAIN APP
if st.session_state.page == "main":
    theme = st.sidebar.radio("🌗 Select Theme", ("Light", "Dark"))
    st.markdown(apply_custom_styles(theme), unsafe_allow_html=True)

    with st.sidebar:
        st.subheader("📅 Date Filter")
        start_date = st.date_input("Start date", value=datetime.today().replace(day=1))
        end_date = st.date_input("End date", value=datetime.today())

    df = load_filtered_data(start_date, end_date)
    all_tickers = sorted(df["ticker_name"].dropna().unique().tolist()) if not df.empty else []
    ticker_input = st.selectbox("Enter ticker symbol:", options=[""] + all_tickers, index=0)

    if ticker_input:
        matches = df[df["ticker_name"].str.upper() == ticker_input.upper()]

        if not matches.empty:
            st.success(f"Found {len(matches)} filings for {ticker_input}")

            # Filing Table
            html_table = render_filing_table(matches)
            st.markdown(html_table, unsafe_allow_html=True)

            # Sentiment Chart
            plot_sentiment_chart(matches, ticker_input)

            # Stock Price Chart
            range_option = st.radio("📈 Time Range", ["1d", "5d", "1mo", "1y", "5y"], horizontal=True)
            plot_stock_price(ticker_input, range_option)

            # News Section
            render_news_section(ticker_input)

            # In your app logic (inside if ticker_input)
            show_valuation_metrics(ticker_input)
            show_shareholding_pattern(ticker_input)
            #show_insider_transactions(ticker_input)
            show_bse_insider_trades(ticker_input)
            # Inside your logic for a valid ticker
            show_nse_bulk_block_short_deals(ticker_input)

        else:
            st.warning("No match found.")
    else:
        st.info("Please enter a ticker symbol above.")
