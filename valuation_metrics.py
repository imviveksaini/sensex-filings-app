import yfinance as yf
import streamlit as st

def show_valuation_metrics(ticker):
    try:
        info = yf.Ticker(f"{ticker}.NS").info
        st.subheader("📊 Valuation Metrics")
        st.markdown(f"""
        <div style='font-size:16px; line-height: 1.8;'>
            🏷️ <b>Market Cap:</b> ₹{round(info.get("marketCap", 0)/1e7, 2)} Cr<br>
            💰 <b>PE Ratio:</b> {info.get("trailingPE", 'N/A')}<br>
            📈 <b>EPS (TTM):</b> {info.get("trailingEps", 'N/A')}<br>
            📚 <b>Book Value:</b> {info.get("bookValue", 'N/A')}<br>
            🎯 <b>Dividend Yield:</b> {round(info.get("dividendYield", 0) * 100, 2)}%
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Could not fetch valuation metrics: {e}")
