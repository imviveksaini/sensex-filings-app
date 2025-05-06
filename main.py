import os
import time
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

from data_loader import update_filings_data
from data_loader import load_filtered_data
from filing_table import render_filing_table
from sentiment_chart import plot_sentiment_chart
from price_chart import plot_stock_price
from news_fetcher import render_news_section
from ui_theme import apply_custom_styles
from valuation_metrics import show_valuation_metrics
from shareholding_pattern import show_shareholding_pattern
from bse_insider_trades import show_bse_insider_trades
from nse_bulk_block_short import show_nse_bulk_block_short_deals
from bonus_summary import summarize_filing_from_url

magic_key_actual = st.secrets.get("MAGIC_KEY", os.getenv("MAGIC_KEY"))
log_msgs = []

def log(msg):
    log_msgs.append(str(msg))

st.set_page_config(page_title="SENSEX Filings Viewer", layout="wide", initial_sidebar_state="expanded")

# Page State
if "page" not in st.session_state:
    st.session_state.page = "landing"

# Theme Selection
theme = st.sidebar.radio("🌗 Select Theme", ("Light", "Dark"))
st.markdown(apply_custom_styles(theme), unsafe_allow_html=True)

# Landing Page
if st.session_state.page == "landing":
    st.markdown("""
        <h1 style='text-align:center;'>📊 Welcome to Your Filing Superpower</h1>
        <p style='text-align:center;'>Behind every stock movement lies a story...the story begins with filings & earnings calls.</p>
        <p style='text-align:center;'>Whether you're a casual investor or a spreadsheet ninja — this app helps you decode the fine print.</p>
    """, unsafe_allow_html=True)

    if st.button("✨ Let me in!"):
        st.session_state.page = "main"
        st.rerun()

    st.markdown("---")
    st.subheader("🎁 Bonus: Filing Summary from URL")
    with st.form("bonus_form"):
        pdf_url_input = st.text_input("Paste the PDF URL here:")
        bonus_magic_key = st.text_input("Enter Magic Key", type="password")
        doc_type = st.selectbox("Select document type:", options=[
            "general", "news_story", "earnings_call_transcript", "research_report", "corporate_filing"
        ], index=0)
        submit_summary = st.form_submit_button("Generate Summary")

    if submit_summary:
        if bonus_magic_key == magic_key_actual:
            with st.spinner("Processing summary..."):
                summary_result, extracted_text = summarize_filing_from_url(pdf_url_input, doc_type)
                st.session_state["summary_result"] = summary_result
                st.session_state["extracted_text"] = extracted_text
                st.session_state["scroll_to_summary_form"] = True
                st.rerun()
        else:
            st.error("❌ Incorrect Magic Key. Access denied.")

    if "summary_result" in st.session_state and "extracted_text" in st.session_state:
        show_extracted_text = st.checkbox("🔍 Show Extracted Text Instead of Summary")
        if show_extracted_text:
            st.code(st.session_state["extracted_text"], language="markdown")
        else:
            st.code(st.session_state["summary_result"], language="json")

    st.stop()

# Sidebar controls
st.sidebar.header("Controls")
days = st.sidebar.number_input("Days to look back", min_value=1, max_value=365, value=10)
debug = True
magic_key_entered = st.sidebar.text_input("Enter Magic Key to Refresh", type="password")
refresh_button = st.sidebar.button("🔄 Refresh Filings Data")

status_ph = st.sidebar.empty()
progress_ph = st.sidebar.progress(0)

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
    from data_loader import load_filtered_data as raw_loader  # use uncached version to refresh
    new_count = update_filings_data(days=days, debug=debug, status_callback=status, progress_callback=progress, log_callback=log)
    elapsed = time.time() - start_time
    status_ph.text(f"Completed in {elapsed:.1f}s — {new_count} new filings added.")
    progress_ph.empty()
else:
    from streamlit.runtime.caching import cache_data

    # @st.cache_data(show_spinner=False)
    # def load_filtered_data(start_date, end_date):
    #     from data_loader import load_filtered_data as actual_loader
    #     return actual_loader(start_date, end_date)

    # At the top of main.py
    from data_loader import load_filtered_data as actual_loader
    
    @st.cache_data(show_spinner=False)
    def cached_load_filtered_data(start_date, end_date):
        return actual_loader(start_date, end_date)

if debug and log_msgs:
    st.subheader("🛠️ Debug Logs")
    for msg in log_msgs:
        st.text(msg)

# Date filter
st.sidebar.subheader("📅 Date Range Filter")
today = datetime.today().date()
start_date = st.sidebar.date_input("From date", today - timedelta(days=30), min_value=today - timedelta(days=365), max_value=today)
end_date = st.sidebar.date_input("To date", today, min_value=start_date, max_value=today)

df_all = load_filtered_data(start_date, end_date)
all_tickers = sorted(df_all["ticker_name"].dropna().unique()) if not df_all.empty else []
ticker_input = st.sidebar.selectbox("Enter ticker symbol:", ["ALL"] + all_tickers)

# Ticker-specific or all
if ticker_input == "ALL":
    df = df_all.sort_values(by="date_of_filing", ascending=False)
    st.success(f"Found {len(df)} filings across all tickers")
    tab1, _, _, _, _ = st.tabs(["📑 Filings Table", "📈 Sentiment Trend", "💹 Price Chart", "📰 News", "💼 Deals & Metrics"])
    with tab1:
        st.subheader("Filings Table: ALL Tickers")
        html = render_filing_table(df)
        st.markdown(html, unsafe_allow_html=True)
else:
    df = df_all[df_all["ticker_name"].str.upper() == ticker_input.upper()].sort_values(by="date_of_filing", ascending=False)
    st.success(f"Found {len(df)} filings for {ticker_input}")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📑 Filings Table", "📈 Sentiment Trend", "💹 Price Chart", "📰 News", "💼 Deals & Metrics"])

    with tab1:
        st.subheader(f"Filings Table: {ticker_input}")
        html = render_filing_table(df)
        st.markdown(html, unsafe_allow_html=True)
    with tab2:
        st.subheader(f"Sentiment Trend: {ticker_input}")
        plot_sentiment_chart(df, ticker_input)
    with tab3:
        st.subheader(f"Stock Price Chart: {ticker_input}")
        range_opt = st.radio("Time Range:", ["1d", "5d", "1mo", "1y", "5y"], horizontal=True)
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

# 🚀 Detailed Summary Form — always at bottom
st.markdown('<div id="summary_form_scroll"></div>', unsafe_allow_html=True)
st.markdown("---")
st.subheader("📄 Detailed Filing Summary Form")

with st.form("summary_form_from_table"):
    pdf_url_input = st.text_input("PDF URL", value=st.session_state.get("summary_url_from_table", ""))
    doc_type = st.selectbox("Select document type:", [
        "general", "news_story", "earnings_call_transcript", "research_report", "corporate_filing"
    ])
    magic_key_input = st.text_input("Magic Key", type="password")
    submit_summary = st.form_submit_button("Generate Summary")

if submit_summary:
    if magic_key_input == magic_key_actual:
        with st.spinner("Generating summary..."):
            summary_result, extracted_text = summarize_filing_from_url(pdf_url_input, doc_type)
            st.session_state["summary_result"] = summary_result
            st.session_state["extracted_text"] = extracted_text
            st.session_state["scroll_to_summary_form"] = True
            st.rerun()
    else:
        st.error("❌ Incorrect Magic Key")

if st.session_state.get("summary_result"):
    show_extracted_text = st.checkbox("🔍 Show Extracted Text Instead of Summary", key="checkbox_detail")
    if show_extracted_text:
        st.code(st.session_state["extracted_text"], language="markdown")
    else:
        st.code(st.session_state["summary_result"], language="json")

# 🔽 Auto-scroll to summary form
if st.session_state.get("scroll_to_summary_form"):
    st.session_state["scroll_to_summary_form"] = False
    st.markdown("""
        <script>
        const el = document.getElementById("summary_form_scroll");
        if (el) {
            el.scrollIntoView({ behavior: 'smooth' });
        }
        </script>
    """, unsafe_allow_html=True)

st.stop()
