import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

def show_shareholding_pattern(ticker):
    try:
        url = f"https://www.screener.in/company/{ticker}/consolidated/"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        pattern = soup.find("section", string=lambda text: text and "Shareholding Pattern" in text)
        table = pattern.find_next("table") if pattern else None
        if not table:
            st.info("Shareholding pattern not available.")
            return
        rows = table.find_all("tr")
        st.subheader("🧾 Shareholding Pattern")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                st.markdown(f"**{cols[0].text.strip()}**: {cols[1].text.strip()}")
    except Exception as e:
        st.error(f"Could not load shareholding data: {e}")
