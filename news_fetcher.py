import feedparser
import streamlit as st

def render_news_section(ticker_symbol):
    st.subheader(f"📰 Latest News about {ticker_symbol}")
    try:
        query = f"{ticker_symbol} stock site:moneycontrol.com OR site:economictimes.indiatimes.com"
        feed_url = f"https://news.google.com/rss/search?q={query.replace(' ', '%20')}&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(feed_url)
        if feed.entries:
            for entry in feed.entries[:5]:
                st.markdown(f"<p style='font-size: 16px; margin-bottom: 5px;'>🔗 <a href='{entry.link}' target='_blank'>{entry.title}</a></p>", unsafe_allow_html=True)
        else:
            st.info("No recent news found.")
    except Exception as e:
        st.error(f"Unable to fetch news: {e}")
