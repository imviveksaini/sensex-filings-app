import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import streamlit as st

def plot_stock_price(ticker_symbol, range_option):
    try:
        yf_symbol = f"{ticker_symbol}.NS"
        interval_map = {
            "1d": "5m",
            "5d": "15m",
            "1mo": "30m",
            "1y": "1d",
            "5y": "1wk"
        }
        interval = interval_map.get(range_option, "1d")

        df = yf.download(tickers=yf_symbol, period=range_option, interval=interval, group_by="ticker")

        if df.empty:
            st.warning(f"No stock data available for {ticker_symbol}")
            return

        if isinstance(df.columns, pd.MultiIndex):
            st.write("✅ MultiIndex Detected")
            if (yf_symbol, "Close") not in df.columns:
                st.warning(f"❌ 'Close' column not found for {ticker_symbol}")
                return
            close_data = df[(yf_symbol, "Close")].dropna().copy()
            close_data.name = "Close"
        else:
            st.write("✅ Flat Index Detected")
            if "Close" not in df.columns:
                st.warning(f"❌ 'Close' column not found for {ticker_symbol}")
                return
            close_data = df["Close"].dropna().copy()
            close_data.name = "Close"

        st.write("🧪 Close data preview:")
        st.dataframe(close_data.head())

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=close_data.index,
            y=close_data,
            mode='lines',
            name='Price',
            line=dict(color='green')
        ))

        fig.update_layout(
            title=f"{ticker_symbol} Stock Price Trend ({range_option})",
            xaxis_title="Date/Time",
            yaxis_title="Price (INR)",
            xaxis_rangeslider_visible=True,
            hovermode="x unified",
            template="plotly_white",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading stock price chart: {e}")
