import pandas as pd
import streamlit as st

def render_filing_table(matches, summary_option="summary_gpt", sentiment_option="sentiment_gpt"):
    summary_map = {"summary_gpt": "summary_gpt"}
    sentiment_map = {"sentiment_gpt": "sentiment_gpt"}
    category_map = {"category_gpt": "category_gpt"}

    summary_col = summary_map.get(summary_option, "summary_gpt")
    sentiment_col = sentiment_map.get(sentiment_option, "sentiment_gpt")
    category_col = category_map.get("category_gpt", "category_gpt")

    df = matches.copy()
    df["ticker_name_link"] = df["ticker_name"].apply(
        lambda x: f'<a href="https://www.google.com/search?q={x}" target="_blank">{x}</a>'
    )

    unique_categories = df[category_col].dropna().unique()
    selected_categories = st.multiselect(
        "Filter by Category", options=unique_categories, default=unique_categories
    )
    df_filtered = df[df[category_col].isin(selected_categories)]

    st.markdown("### 🧾 Filtered Filings")
    for idx, row in df_filtered.iterrows():
        ticker_link = row["ticker_name_link"]
        code = row.get("code", "")
        date_str = ''
        if pd.notna(row.get("date_of_filing")):
            date_str = pd.to_datetime(row['date_of_filing']).strftime('%Y-%m-%d')
        summary = row.get(summary_col, "")
        category = row.get(category_col, "")
        sentiment = row.get(sentiment_col, 0)
        color = 'green' if sentiment > 0 else 'red' if sentiment < 0 else 'black'
        pdf_url = row.get("url", "")

        with st.container():
            st.markdown(f"""
            <div style="border:1px solid #ddd; padding:10px; border-radius:10px; margin-bottom:10px">
                <b>Ticker:</b> {ticker_link} | <b>Code:</b> {code} | <b>Date:</b> {date_str}  
                <br><b>Category:</b> {category} | <b>Sentiment:</b> <span style='color:{color}'>{sentiment}</span>  
                <br><b>Summary:</b> {summary}
                <br><a href="{pdf_url}" target="_blank">🔗 Filing Link</a>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Generate Detailed Summary", key=f"gen_summary_{idx}"):
                st.session_state["summary_url_from_table"] = pdf_url
                #st.session_state["scroll_to_summary_form"] = True  # Optional extra flag
                st.session_state["scroll_to_bonus_form"] = True
                st.rerun()
