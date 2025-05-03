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
import json

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
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT API call failed: {e}")
        return None

def update_filings_data(days=2, debug=False, status_callback=None, progress_callback=None, log_callback=None):
    """
    Scrape and GPT process filings; append only new filings to existing ticker CSVs.
    Returns total new records appended.
    """
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
    {"name": "ABFRL",           "bse_code": "535755"},  # Aditya Birla Fashion & Retail
    {"name": "SHK",             "bse_code": "539450"},  # S H Kelkar
    {"name": "BLS",             "bse_code": "540073"},
    {"name": "APOLLOTYRE",      "bse_code": "500877"},
    {"name": "OMINFRA",         "bse_code": "531092"},
    {"name": "TRITURBINE",      "bse_code": "533655"},
    {"name": "PRAJIND",         "bse_code": "522205"},
    {"name": "AHLUCONT",        "bse_code": "532811"},
    {"name": "INDHOTEL",        "bse_code": "500850"},
    {"name": "INDIGO",          "bse_code": "539448"},
    {"name": "M&MFIN",          "bse_code": "532720"},
    {"name": "PVRINOX",         "bse_code": "532689"},
    {"name": "VIPIND",          "bse_code": "507880"},
    {"name": "VGUARD",          "bse_code": "532953"},
    {"name": "WABAG",           "bse_code": "533269"},  # VA Tech Wabag
    {"name": "WONDERLA",        "bse_code": "538268"},
    {"name": "AXISBANK",        "bse_code": "532215"},
    {"name": "BATAINDIA",       "bse_code": "500033"},
    {"name": "FLUIDOMAT",       "bse_code": "522017"},        # didn’t find a clear match—can you confirm the exact name?
    {"name": "HDFCBANK",        "bse_code": "500180"},
    {"name": "ICICIBANK",       "bse_code": "532174"},
    {"name": "ITCHOTEL",        "bse_code": "500875"},  # ITC Hotels
    {"name": "ITC",             "bse_code": "500875"},
    {"name": "INFOSYS",         "bse_code": "500209"},
    {"name": "KEI",             "bse_code": "505700"},
    {"name": "LT",              "bse_code": "500510"},
    {"name": "LEMONTREE",       "bse_code": "540063"},
    {"name": "MANAPPURAM",      "bse_code": "531213"},
    {"name": "PNB",             "bse_code": "532461"},
    {"name": "SIEMENS",         "bse_code": "500650"},
    {"name": "SWSOLAR",         "bse_code": "543248"},
    {"name": "TATAMOTORS",      "bse_code": "500570"},
    {"name": "VEDANTFASHION",   "bse_code": "543389"},
    {"name": "VOLTAS",          "bse_code": "500575"},
    {"name": "ANGELONE",        "bse_code": "543235"},
    {"name": "BHEL",            "bse_code": "500103"},
    {"name": "MOLDTEK",         "bse_code": "540287"},
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
    if debug and log_callback:
        log_callback(f"{n} tickers to process from {start} to {end}")
    #print(n, start, end)

    for i, tk in enumerate(tickers, 1):
        if status_callback: status_callback(f"Processing {tk['name']} ({i}/{n})")
        if progress_callback: progress_callback((i-1)/n)

        csv_path = os.path.join(default_output_dir, f"{tk['name']}.csv")
        existing_urls = set()
        if os.path.isfile(csv_path):
            try:
                df_exist = pd.read_csv(csv_path)
                existing_urls = set(df_exist['url'].dropna().astype(str))
            except Exception:
                pass

        payload = {"pageno":1,"strCat":"-1","strPrevDate":prev,
                   "strScrip":tk['bse_code'],"strSearch":"P",
                   "strToDate":to,"strType":"C","subcategory":""}
        ann = []
        while True:
            try:
                r = requests.get(BSE_API, headers=HEADERS, params=payload, timeout=10)
                r.raise_for_status()
            except Exception as e:
                if debug and log_callback:
                    log_callback(f"Fetch error {tk['name']}: {e}")
                break
            data = r.json().get("Table", [])
            if not data: break
            ann.extend(data)
            payload["pageno"] += 1
        if debug and log_callback:
            log_callback(f"{tk['name']}: {len(ann)} announcements")

        new_records = []
        for item in ann:
            attach = item.get("ATTACHMENTNAME","").strip()
            if not attach: continue

            pdf = None; pdf_url = None
            for path in [f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attach}",
                         f"https://www.bseindia.com/xml-data/corpfiling/AttachHis/{attach}"]:
                try:
                    tmp = requests.get(path, headers=HEADERS, timeout=10)
                    tmp.raise_for_status(); pdf=tmp.content; pdf_url=path; break
                except: pass
            if not pdf: continue

            raw = item.get("DissemDT","")
            try: d = raw.split("T")[0]; date = datetime.fromisoformat(d).strftime("%Y-%m-%d")
            except: date = datetime.today().strftime("%Y-%m-%d")

            text = ""
            try:
                for p in PdfReader(BytesIO(pdf)).pages:
                    t = p.extract_text() or ""; text += t + "\n"
            except Exception as e:
                if debug and log_callback:
                    log_callback(f"Extract error: {e}")
                continue
            if not text.strip(): continue

            input_text = text[:4000]
            raw_input_text = f"Text:\n{input_text}"
            gpt_response = call_gpt(raw_input_text)
            #if debug and log_callback:
            #    log_callback(f"Input: {raw_input_text}\nGPT raw: {gpt_response}")
            
            if not gpt_response:
                continue
            
            try:
                # Parse the JSON string from GPT
                parsed = json.loads(gpt_response)
            
                summary = parsed.get('summary', '')
                sentiment = parsed.get('sentiment', '')
                category = parsed.get('category', '')
            
                if debug and log_callback:
                    log_callback(f"📝 Summary GPT: {summary}")
                    log_callback(f"📈 Sentiment GPT: {sentiment}")
                    log_callback(f"🏷️ Category GPT: {category}")
            
                new_records.append({
                    'ticker': tk['name'],
                    'code': tk['bse_code'],
                    'date': date,
                    'summary_gpt': summary,
                    'sentiment_gpt': sentiment,
                    'category_gpt': category,
                    'url': pdf_url
                })
            
            except (ValueError, json.JSONDecodeError) as e:
                if debug and log_callback:
                    log_callback(f"⚠️ JSON parse error: {e}")
                continue

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
    full = full.drop_duplicates()
    if start_date:
        full = full[full['date_of_filing'] >= pd.to_datetime(start_date)]
    if end_date:
        full = full[full['date_of_filing'] <= pd.to_datetime(end_date)]
    return full
