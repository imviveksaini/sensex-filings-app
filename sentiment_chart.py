
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import streamlit as st

def plot_sentiment_chart(matches, ticker_name):
    """
    Plots the average sentiment (Vader) over time for a given ticker.
    Expects matches DataFrame with columns:
      - date_of_filing (datetime)
      - vader (numeric sentiment score)
    """
    if matches.empty:
        st.info("No sentiment data to display.")
        return

    # Prepare data
    df = matches.copy()
    df['date_of_filing'] = pd.to_datetime(df['date_of_filing'], errors='coerce')
    df = df.dropna(subset=['date_of_filing', 'vader'])

    # Compute daily average Vader sentiment
    sentiment_avg = (
        df.groupby('date_of_filing')['vader']
          .mean()
          .reset_index()
          .sort_values('date_of_filing')
    )

    # Rename for display
    sentiment_avg = sentiment_avg.rename(columns={'vader': 'Average Vader Sentiment'})
    sentiment_avg = sentiment_avg.set_index('date_of_filing')

    # Plot
    st.line_chart(sentiment_avg, height=300, use_container_width=True)
    st.caption(f"Sentiment trend for {ticker_name} (Vader)")
