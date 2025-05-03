import os
import csv
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime, timedelta
from PyPDF2 import PdfReader
import openai
from openai import OpenAI
import streamlit as st

# Suppress HF progress bars
os.environ["TRANSFORMERS_NO_TQDM"] = "1"

# --- Constants & Directories ---
default_output_dir = os.path.join(os.getcwd(), "data", "portfolio_stocks_gpt")
os.makedirs(default_output_dir, exist_ok=True)





def call_gpt(raw_input_text: str) -> dict:
    # Retrieve the API key
    my_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    try:
        client = OpenAI(api_key=my_api_key)
        user_prompt = f'''
        You're an expert in reading corporate filings on Indian stocks.
        
        Understand the following filing and analyze it carefully.
        
        Respond **only** in valid JSON format with exactly two keys:
        1. "summary": a brief summary of the filing in maximum two sentences.
        2. "sentiment": how bullish are you on its stock based on the information in the filing. 100= very bullish, -100= very bearish.
        3. "category": summarise this news between 1-3 words only.
        Filing text:
        {raw_input_text}
        '''
        
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            temperature=0,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"GPT API call failed: {e}")
        return None

def update_filings_data(days=2, debug=False, status_callback=None, progress_callback=None):
    """
    Scrape and GPT process filings; append only new filings to existing ticker CSVs.
    Returns total new records appended.
    """

    
    # Config
    tickers = [
        {"name": "NCC",             "bse_code": "500294"},
        {"name": "JYOTHYLABS",     "bse_code": "532926"},
        {"name": "SHEELAFOAM",     "bse_code": "540203"},
        {"name": "KEC",             "bse_code": "532714"},
        {"name": "KPIL",            "bse_code": "505283"},
        {"name": "HCC",             "bse_code": "500185"},
        {"name": "OLECTRA",         "bse_code": "532439"},
        {"name": "LTF",             "bse_code": "533519"},
        {"name": "MAYURUNIQUOTERS", "bse_code": "522249"},
        {"name": "DABUR",           "bse_code": "500096"},
        {"name": "HINDUNILVR",      "bse_code": "500696"},
        {"name": "JUBLFOOD",        "bse_code": "543225"},
        {"name": "KOTAKBANK",       "bse_code": "500247"},
        {"name": "RIL",             "bse_code": "500325"}
    ]
    BSE_API = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
    HEADERS = {"User-Agent":"Mozilla/5.0","Referer":"https://www.bseindia.com/"}

    start = datetime.today() - timedelta(days=days)
    end = datetime.today()
    prev = start.strftime("%Y%m%d")
    to = end.strftime("%Y%m%d")

    total_new = 0
    n = len(tickers)
    if debug: print(n, start, end)
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
            try:
                r = requests.get(BSE_API, headers=HEADERS, params=payload, timeout=10)
                r.raise_for_status()
            except Exception as e:
                if debug: print(f"Fetch error {tk['name']}: {e}")
                break
            data = r.json().get("Table", [])
            if not data: break
            ann.extend(data)
            payload["pageno"] += 1
        if debug: print(f"{tk['name']}: {len(ann)} announcements")
        if debug: st.write(f"{tk['name']}: {len(ann)} announcements")

        new_records = []
        # Process each announcement
        for item in ann:
            attach = item.get("ATTACHMENTNAME",""
                           ).strip()
            if not attach: continue
            # Download PDF
            pdf = None; pdf_url = None
            for path in [f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attach}",
                         f"https://www.bseindia.com/xml-data/corpfiling/AttachHis/{attach}"]:
                try:
                    tmp = requests.get(path, headers=HEADERS, timeout=10)
                    tmp.raise_for_status(); pdf=tmp.content; pdf_url=path; break
                except: pass
            if not pdf: continue
            # Date
            raw = item.get("DissemDT","")
            try: d = raw.split("T")[0]; date = datetime.fromisoformat(d).strftime("%Y-%m-%d")
            except: date = datetime.today().strftime("%Y-%m-%d")
            # Extract text
            text="";
            try:
                for p in PdfReader(BytesIO(pdf)).pages:
                    t=p.extract_text() or ""; text+=t+"\n"
            except Exception as e:
                if debug: print(f"Extract error: {e}")
                continue
            if not text.strip(): continue
            
            # Call GPT-based analysis
            input_text = text[:4000]  # Truncate to avoid token overflow
            raw_input_text = (
                f"Text:\n{input_text}"
            )
            gpt_response = call_gpt(raw_input_text)
            if not gpt_response:
                continue

            # Split GPT response into summary, sentiment, and category
            try:
                summary, sentiment, category = gpt_response.split('\n')
                # Debug output of summaries and categories
                if debug:
                    print("📝 Summary GPT:", summary)
                    print("📝 Sentiment GPT:", sentiment)
                    print("📝 Category GPT:", category)
                    
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

def load_filtered_data(start_date=None, end_date=None):
    """
    Reads all per-ticker CSVs, concatenates, and filters by date.
    Expects columns: ticker, code, date, sum_bart, sum_peg, sum_t5,
    vader, finbert, finbert_s, distil, distil_s, url
    Returns DataFrame with:
      - ticker_name, ticker_bse, date_of_filing,
        summary columns, sentiment columns, url
    """
    if not os.path.isdir(default_output_dir):
        return pd.DataFrame()

    dfs = []
    for fname in os.listdir(default_output_dir):
        if not fname.endswith('.csv'): continue
        path = os.path.join(default_output_dir, fname)
        try:
            df = pd.read_csv(path, parse_dates=['date'])
            df = df.rename(columns={
                'ticker':'ticker_name','code':'ticker_bse',
                'date':'date_of_filing',
                'summary_gpt':'summary_gpt','sentiment_gpt':'sentiment_gpt','category_gpt':'category_gpt',
                'url':'url'
            })
            dfs.append(df)
        except Exception:
            continue
    if not dfs:
        return pd.DataFrame()

    full = pd.concat(dfs, ignore_index=True)
    if start_date:
        full = full[full['date_of_filing'] >= pd.to_datetime(start_date)]
    if end_date:
        full = full[full['date_of_filing'] <= pd.to_datetime(end_date)]
    return full
