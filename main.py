import os
import time
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

magic_key_actual = st.secrets.get("MAGIC_KEY", os.getenv("MAGIC_KEY"))

log_msgs = []

def log(msg):
    log_msgs.append(str(msg))
    
# Page configuration
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
    st.markdown(
        """
        <h1 style='text-align:center;'>📊 Welcome to Your Filing Superpower</h1>
        <p style='text-align:center;'>Behind every stock movement lies a story...the story begins with filings & earnings calls.</p>
        <p style='text-align:center;'>Whether you're a casual investor or a spreadsheet ninja — this app helps you decode the fine print.</p>
        """,
        unsafe_allow_html=True,
    )
    if st.button("✨ Let me in!"):
        st.session_state.page = "main"
        st.rerun()
    st.stop()

# Main application UI
# Theme selector
theme = st.sidebar.radio("🌗 Select Theme", ("Light", "Dark"))
st.markdown(apply_custom_styles(theme), unsafe_allow_html=True)

# Controls: update parameters
st.sidebar.header("Controls")
days = st.sidebar.number_input("Days to look back", min_value=1, max_value=365, value=10)

debug = True #st.sidebar.checkbox("Debug mode", value=False)
# Input for magic key (passcode)
magic_key_entered = st.sidebar.text_input("Enter Magic Key to Refresh", type="password")
refresh = st.sidebar.button("🔄 Refresh Filings Data")

# Status and progress placeholders
status_ph = st.sidebar.empty()
progress_ph = st.sidebar.progress(0)

# Check magic key before triggering refresh
refresh = False
if refresh_button:
    if magic_key_entered == magic_key_actual:
        refresh = True
        status_ph.success("✅ Magic key accepted. Refresh triggered.")
    else:
        status_ph.error("❌ Incorrect magic key. Refresh not allowed.")

if refresh:
    start_time = time.time()
    def status(msg): status_ph.text(msg)
    def progress(p): progress_ph.progress(p)

    new_count = update_filings_data(
        days=days,
        debug=debug,
        status_callback=status,
        progress_callback=progress,
        log_callback=log
    )


    elapsed = time.time() - start_time
    status_ph.text(f"Completed in {elapsed:.1f}s — {new_count} new filings added.")
    progress_ph.empty()

# display logs in Streamlit UI (not terminal)
if debug and log_msgs:
    st.subheader("🛠️ Debug Logs")
    for msg in log_msgs:
        st.text(msg)
        
# Date filters for viewing
st.sidebar.subheader("📅 Date Range Filter")
today = datetime.today().date()
start_date = st.sidebar.date_input(
    "From date", today - timedelta(days=30),
    min_value=today - timedelta(days=365), max_value=today
)
end_date = st.sidebar.date_input(
    "To date", today,
    min_value=start_date, max_value=today
)

# Load and filter data
df_all = load_filtered_data(start_date, end_date)
all_tickers = sorted(df_all["ticker_name"].dropna().unique()) if not df_all.empty else []
ticker_input = st.sidebar.selectbox("Enter ticker symbol:", ["ALL"] + all_tickers)

if ticker_input == "ALL":
    df = df_all
    df = df.sort_values(by="date_of_filing", ascending=False)
    st.success(f"Found {len(df)} filings across all tickers")

    # You can optionally show a unified table here too
    tab1, _, _, _, _ = st.tabs([
        "📑 Filings Table", "📈 Sentiment Trend",
        "💹 Price Chart", "📰 News", "💼 Deals & Metrics"
    ])
    with tab1:
        st.subheader("Filings Table: ALL Tickers")
        html = render_filing_table(df)
        st.markdown(html, unsafe_allow_html=True)

else:
    df = df_all[df_all["ticker_name"].str.upper() == ticker_input.upper()]
    st.success(f"Found {len(df)} filings for {ticker_input}")

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📑 Filings Table", "📈 Sentiment Trend",
        "💹 Price Chart", "📰 News", "💼 Deals & Metrics"
    ])

    with tab1:
        st.subheader(f"Filings Table: {ticker_input}")
        html = render_filing_table(df)
        st.markdown(html, unsafe_allow_html=True)

    with tab2:
        st.subheader(f"Sentiment Trend: {ticker_input}")
        plot_sentiment_chart(df, ticker_input)

    with tab3:
        st.subheader(f"Stock Price Chart: {ticker_input}")
        range_opt = st.radio(
            "Time Range:", ["1d", "5d", "1mo", "1y", "5y"], horizontal=True
        )
        plot_stock_price(ticker_input, range_opt)

    with tab4:
        st.subheader("📰 Related News")
        render_news_section(ticker_input)

    with tab5:
        st.subheader("💡 Valuation Metrics & Holdings")
        show_valuation_metrics(ticker_input)
        show_shareholding_pattern(ticker_input)
        st.subheader("🕵️ BSE Insider Trades")
        show_bse_insider_trades(ticker_input)
        st.subheader("💼 NSE Bulk/Block/Short Deals")
        show_nse_bulk_block_short_deals(ticker_input)
