# data_loader.py
import os
import csv
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime, timedelta
from PyPDF2 import PdfReader
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Suppress HF progress bars
os.environ["TRANSFORMERS_NO_TQDM"] = "1"
from transformers import logging as hf_logging
hf_logging.set_verbosity_error()

# --- Constants & Directories ---
default_output_dir = os.path.join(os.getcwd(), "data", "portfolio_stocks_pegasus")
os.makedirs(default_output_dir, exist_ok=True)

# --- Load models once ---
summarizer_bart = pipeline("summarization", model="facebook/bart-large-cnn")
# Pegasus XSUM
pegasus_tok = AutoTokenizer.from_pretrained("google/pegasus-xsum", use_fast=False)
pegasus_mod = AutoModelForSeq2SeqLM.from_pretrained("google/pegasus-xsum")
summarizer_pegasus = pipeline("summarization", model=pegasus_mod, tokenizer=pegasus_tok)
# FLAN-T5
flan_tok = AutoTokenizer.from_pretrained("google/flan-t5-large", use_fast=False)
flan_mod = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-large")
summarizer_t5 = pipeline("summarization", model=flan_mod, tokenizer=flan_tok)

analyzer_vader = SentimentIntensityAnalyzer()
classifier_finbert = pipeline("sentiment-analysis", model="yiyanghkust/finbert-tone")
classifier_distilbert = pipeline(
    "sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english"
)

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


def update_filings_data(days=10, debug=False, status_callback=None, progress_callback=None):
    """
    Scrape and NLP process filings; append only new filings to existing ticker CSVs.
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
            # Summaries & sentiments
            sb = summarizer_bart(text[:1024], max_length=130, min_length=30)[0]['summary_text']
            sp = summarizer_pegasus(text[:4096], max_length=130, min_length=30)[0]['summary_text']
            st5 = summarizer_t5(text[:2048], max_length=130, min_length=30)[0]['summary_text']
            vd = int(analyzer_vader.polarity_scores(sb)['compound']*100)
            fb = classifier_finbert(sb)[0]
            db = classifier_distilbert(sb)[0]

            new_records.append({
                'ticker':tk['name'],'code':tk['bse_code'],'date':date,
                'sum_bart':sb,'sum_peg':sp,'sum_t5':st5,
                'vader':vd,
                'finbert':fb['label'],'finbert_s':round(fb['score'],3),
                'distil':db['label'],'distil_s':round(db['score'],3),
                'url':pdf_url
            })

        if new_records:
            write_header = not os.path.isfile(csv_path)
            with open(csv_path,'a',newline='',encoding='utf-8') as f:
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
                'sum_bart':'sum_bart','sum_peg':'sum_peg','sum_t5':'sum_t5',
                'vader':'vader','finbert_s':'finbert_s','distil_s':'distil_s',
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




def load_filtered_data(start_date=None, end_date=None):
    """
    Reads all <TICKER>.csv files from processed/ directory,
    standardizes columns (date & ticker), concatenates into a DataFrame,
    and filters by date range (if provided).

    CSVs can have either 'date' or 'date_of_filing' columns,
    and either 'ticker' or 'ticker_name' columns.

    Returns a pandas.DataFrame with columns 'ticker_name' and 'date_of_filing'.
    """
    folder = default_output_dir
    if not os.path.isdir(folder):
        return pd.DataFrame()

    dfs = []
    for fname in os.listdir(folder):
        if not fname.lower().endswith('.csv'):
            continue
        path = os.path.join(folder, fname)
        try:
            df = pd.read_csv(path)
        except Exception:
            continue

        # Standardize date column
        if 'date' in df.columns:
            df['date_of_filing'] = pd.to_datetime(df['date'], errors='coerce')
        elif 'date_of_filing' in df.columns:
            df['date_of_filing'] = pd.to_datetime(df['date_of_filing'], errors='coerce')
        else:
            continue  # cannot find a date column

        # Standardize ticker column
        if 'ticker' in df.columns:
            df['ticker_name'] = df['ticker']
        elif 'ticker_name' in df.columns:
            df['ticker_name'] = df['ticker_name']
        else:
            # fallback to filename (without extension)
            df['ticker_name'] = os.path.splitext(fname)[0]

        # Drop rows without valid date
        df = df.dropna(subset=['date_of_filing'])
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    full = pd.concat(dfs, ignore_index=True)

    # Apply date filters
    if start_date is not None:
        start_ts = pd.to_datetime(start_date)
        full = full[full['date_of_filing'] >= start_ts]
    if end_date is not None:
        end_ts = pd.to_datetime(end_date)
        full = full[full['date_of_filing'] <= end_ts]

    return full
