# main.py
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# Core data and NLP loader
from data_loader import update_filings_data, load_filtered_data
# Rendering modules
from filing_table import render_filing_table
from sentiment_chart import plot_sentiment_chart
from price_chart import plot_stock_price
from news_fetcher import render_news_section
from ui_theme import apply_custom_styles
# Additional stock info
from valuation_metrics import show_valuation_metrics
from shareholding_pattern import show_shareholding_pattern
from bse_insider_trades import show_bse_insider_trades
from nse_bulk_block_short import show_nse_bulk_block_short_deals

# Page config
st.set_page_config(
    page_title="SENSEX Filings Viewer",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Landing page
if "page" not in st.session_state:
    st.session_state.page = "landing"
if st.session_state.page == "landing":
    st.markdown(apply_custom_styles("Light"), unsafe_allow_html=True)
    st.markdown("""
        <h1 style='text-align:center;'>📊 Welcome to Your Filing Superpower</h1>
        <p style='text-align:center;'>Behind every stock movement lies a story...the story begins with filings & earnings calls.</p>
        <p style='text-align:center;'>Whether you're a casual investor or a spreadsheet ninja — this app helps you decode the fine print.</p>
    """, unsafe_allow_html=True)
    if st.button("✨ Let me in!"):
        st.session_state.page = "main"
        st.rerun()
    st.stop()

# Main App
# Theme selector
theme = st.sidebar.radio("🌗 Select Theme", ("Light", "Dark"))
st.markdown(apply_custom_styles(theme), unsafe_allow_html=True)

# Refresh Data
if st.sidebar.button("🔄 Refresh Filings Data"):
    with st.spinner("Fetching latest filings..."):
        added = update_filings_data()
    if added:
        st.sidebar.success(f"Added {added} new filings")
    else:
        st.sidebar.info("No new filings found.")

# Date Filter
st.sidebar.subheader("📅 Date Range")
today = datetime.today().date()
start_date = st.sidebar.date_input(
    "Start date", today - timedelta(days=30),
    min_value=today - timedelta(days=365), max_value=today
)
end_date = st.sidebar.date_input(
    "End date", today,
    min_value=start_date, max_value=today
)

# Load and select ticker
df_all = load_filtered_data(start_date, end_date)
all_tickers = sorted(df_all["ticker_name"].dropna().unique()) if not df_all.empty else []
ticker_input = st.sidebar.selectbox(
    "Enter ticker symbol:", [""] + all_tickers
)

if ticker_input:
    # Filter data
    df = df_all[df_all["ticker_name"].str.upper() == ticker_input.upper()]
    st.success(f"Found {len(df)} filings for {ticker_input}")

    # Layout: Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📑 Filings Table", "📈 Sentiment Trend",
        "💹 Price Chart", "📰 News", "💼 Deals & Metrics"
    ])

    with tab1:
        st.subheader(f"Filings Table: {ticker_input}")
        # Summary & Sentiment selectors
        summary_option = st.selectbox(
            "Summary model:", ["PEGASUS", "BART", "T5"], index=0
        )
        sentiment_option = st.selectbox(
            "Sentiment model:", ["FinBERT", "VADER", "DistilBERT"], index=0
        )
        html = render_filing_table(df, summary_option, sentiment_option)
        st.markdown(html, unsafe_allow_html=True)

    with tab2:
        st.subheader(f"Sentiment Trend: {ticker_input}")
        plot_sentiment_chart(df, ticker_input)

    with tab3:
        st.subheader(f"Stock Price Chart: {ticker_input}")
        range_opt = st.radio("Time Range", ["1d","5d","1mo","1y","5y"], horizontal=True)
        plot_stock_price(ticker_input, range_opt)

    with tab4:
        st.subheader("Related News")
        render_news_section(ticker_input)

    with tab5:
        st.subheader("Valuation Metrics & Holdings")
        show_valuation_metrics(ticker_input)
        show_shareholding_pattern(ticker_input)
        st.subheader("BSE Insider Trades")
        show_bse_insider_trades(ticker_input)
        st.subheader("NSE Bulk/Block/Short Deals")
        show_nse_bulk_block_short_deals(ticker_input)

else:
    st.info("Please select a ticker from the sidebar.")
