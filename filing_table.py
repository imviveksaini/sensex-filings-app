import pandas as pd
import streamlit as st

def render_filing_table(matches, summary_option="summary_gpt", sentiment_option="sentiment_gpt", category_filter=None):
    """
    Renders a HTML table of filings allowing dynamic selection of summary and sentiment model.
    - matches: DataFrame with columns including:
        ticker_name, code, date_of_filing,
        summary_gpt, sentiment_gpt, category_gpt,
        url
    """
    # Map summary and sentiment column names
    summary_map = {"summary_gpt": "summary_gpt"}
    sentiment_map = {"sentiment_gpt": "sentiment_gpt"}
    category_map = {"category_gpt": "category_gpt"}  # Added category map

    summary_col = summary_map.get(summary_option, "summary_gpt")
    sentiment_col = sentiment_map.get(sentiment_option, "sentiment_gpt")
    category_col = category_map.get("category_gpt", "category_gpt")  # Correct mapping

    # Convert ticker to HTML link
    df = matches.copy()

    # Filter rows by category if a filter is provided
    if category_filter:
        df = df[df[category_col].str.contains(category_filter, case=False, na=False)]

    # Convert ticker to HTML link
    df["ticker_name"] = df["ticker_name"].apply(
        lambda x: f'<a href="https://www.google.com/search?q={x}" target="_blank">{x}</a>'
    )

    # Build table rows
    rows = []
    for _, row in df.iterrows():
        sentiment = row.get(sentiment_col, 0)
        color = 'green' if sentiment > 0 else 'red' if sentiment < 0 else 'black'
        summary = row.get(summary_col, "")
        category = row.get(category_col, "")
        link = f"<a href='{row.get('url')}' target='_blank'>🧾</a>" if row.get('url') else ''
        date_str = ''
        if pd.notna(row.get('date_of_filing')):
            date_str = pd.to_datetime(row['date_of_filing']).strftime('%Y-%m-%d')
        rows.append(
            f"<tr>"
            f"<td>{row['ticker_name']}</td>"
            f"<td>{row.get('code','')}</td>"
            f"<td>{date_str}</td>"
            f"<td style='white-space:pre-wrap'>{summary}</td>"
            f"<td style='white-space:pre-wrap'>{category}</td>"
            f"<td style='color:{color}'>{sentiment}</td>"
            f"<td>{link}</td>"
            f"</tr>"
        )
    table_rows = ''.join(rows)

    # HTML
    html = f'''<div style='padding:10px;'>
    <table style='width:100%; font-family:Merriweather, serif; border-collapse:collapse;' border='1'>
        <thead>
            <tr>
                <th>Ticker</th><th>BSE Code</th><th>Date</th>
                <th>Summary ({summary_option})</th><th>Category</th><th>Sentiment ({sentiment_option})</th><th>Link</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>
</div>'''
    return html

# Example usage in a Streamlit app
category_filter = st.text_input("Filter by Category", "")  # Allow user to filter by category
df = pd.DataFrame()  # Replace with your actual DataFrame
html_table = render_filing_table(df, category_filter=category_filter)
st.markdown(html_table, unsafe_allow_html=True)
