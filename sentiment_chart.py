# sentiment_chart.py

import streamlit as st
import pandas as pd


def plot_sentiment_chart(matches: pd.DataFrame, ticker_name: str):
    """
    Plots the average Vader sentiment over time for a given ticker using Streamlit's built-in chart.

    Expects:
      - matches: DataFrame with columns 'date_of_filing' and 'vader'
      - ticker_name: the ticker symbol (string)
    """
    if matches.empty:
        st.info("No sentiment data to display.")
        return

    # Ensure date_of_filing is datetime
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

    # Rename column for display
    sentiment_avg = sentiment_avg.rename(columns={'vader': 'Average Vader Sentiment'})
    sentiment_avg = sentiment_avg.set_index('date_of_filing')

    # Plot using Streamlit's line_chart
    st.line_chart(sentiment_avg, height=300, use_container_width=True)
    st.caption(f"Sentiment trend for {ticker_name} (Vader)")
