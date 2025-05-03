import os
import csv
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime, timedelta
from PyPDF2 import PdfReader
import openai

# Suppress HF progress bars
os.environ["TRANSFORMERS_NO_TQDM"] = "1"

# --- Constants & Directories ---
default_output_dir = os.path.join(os.getcwd(), "data", "portfolio_stocks_gpt")
os.makedirs(default_output_dir, exist_ok=True)

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def call_gpt(prompt: str) -> dict:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a financial analyst AI assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"GPT API call failed: {e}")
        return None

def update_filings_data(days=10, debug=False, status_callback=None, progress_callback=None):
    """
    Scrape and GPT process filings; append only new filings to existing ticker CSVs.
    Returns total new records appended.
    """
    start = datetime.today() - timedelta(days=days)
    end = datetime.today()
    prev = start.strftime("%Y%m%d")
    to = end.strftime("%Y%m%d")

    total_new = 0
    n = len(tickers)
    for i, tk in enumerate(tickers, 1):
        if status_callback: status_callback(f"Processing {tk['name']} ({i}/{n})")
        if progress_callback: progress_callback((i-1)/n)

        # Load existing URLs
        csv_path = os.path.join(default_output_dir, f"{tk['name']}.csv")
        existing_urls = set()
        if os.path.isfile(csv_path):
            try:
                df_exist = pd.read_csv(csv_path)
                existing_urls = set(df_exist['url'].dropna().astype(str))
            except Exception:
                pass

        # Fetch announcements
        payload = {"pageno":1,"strCat":"-1","strPrevDate":prev,
                   "strScrip":tk['bse_code'],"strSearch":"P",
                   "strToDate":to,"strType":"C","subcategory":""}
        ann = []
        while True:
            r = requests.get(BSE_API, headers=HEADERS, params=payload, timeout=10)
            if not r.ok: break
            data = r.json().get('Table', [])
            if not data: break
            ann.extend(data)
            payload['pageno'] += 1

        new_records = []
        for item in ann:
            attach = (item.get('ATTACHMENTNAME') or '').strip()
            if not attach: continue
            pdf_url, content = None, None
            for base in ['AttachLive','AttachHis']:
                url = f"https://www.bseindia.com/xml-data/corpfiling/{base}/{attach}"
                resp = requests.get(url, headers=HEADERS, timeout=10)
                if resp.ok:
                    pdf_url = url
                    content = resp.content
                    break
            if not pdf_url or pdf_url in existing_urls:
                continue
            # Extract date
            raw = item.get('DissemDT','')
            try: date = raw.split('T')[0]
            except: date = end.strftime('%Y-%m-%d')
            # Extract text
            text = ''
            try:
                reader = PdfReader(BytesIO(content))
                for pg in reader.pages:
                    text += (pg.extract_text() or '') + '\n'
            except:
                continue
            if not text.strip(): continue
            
            # Call GPT-based analysis
            input_text = text[:4000]  # Truncate to avoid token overflow
            prompt = (
                f"Please analyze the following financial disclosure and provide:\n"
                f"1. A concise summary\n"
                f"2. The overall sentiment (Positive, Neutral, Negative)\n"
                f"3. Categorize the filing (e.g., financials, strategy, earnings)\n"
                f"Text:\n{input_text}"
            )
            gpt_response = call_gpt(prompt)
            if not gpt_response:
                continue

            # Split GPT response into summary, sentiment, and category
            try:
                summary, sentiment, category = gpt_response.split('\n')
            except ValueError:
                continue  # If splitting fails, skip this record

            new_records.append({
                'ticker': tk['name'],
                'code': tk['bse_code'],
                'date': date,
                'summary_gpt': summary,
                'sentiment_gpt': sentiment,
                'category_gpt': category,
                'url': pdf_url
            })

        if new_records:
            write_header = not os.path.isfile(csv_path)
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=new_records[0].keys())
                if write_header: writer.writeheader()
                writer.writerows(new_records)
            total_new += len(new_records)

    if progress_callback: progress_callback(1.0)
    if status_callback: status_callback(f"Done: {total_new} new filings.")
    return total_new
