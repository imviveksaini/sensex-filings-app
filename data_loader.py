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
import base64
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlencode


# Suppress HF progress bars
os.environ["TRANSFORMERS_NO_TQDM"] = "1"

# --- Constants & Directories ---
#default_output_dir = os.path.join(os.getcwd(), "data", "portfolio_stocks_gpt")
#os.makedirs(default_output_dir, exist_ok=True)

tickers = [{"name": "BATAINDIA",       "bse_code": "500043"}]
# tickers = [
#     {"name": "NCC",             "bse_code": "500294"},
#     {"name": "JYOTHYLABS",     "bse_code": "532926"},
#     {"name": "SHEELAFOAM",     "bse_code": "540203"},
#     {"name": "KEC",             "bse_code": "532714"},
#     {"name": "KPIL",            "bse_code": "505283"},
#     {"name": "HCC",             "bse_code": "500185"},
#     {"name": "OLECTRA",         "bse_code": "532439"},
#     {"name": "LTF",             "bse_code": "533519"},
#     {"name": "MAYURUNIQUOTERS", "bse_code": "522249"},
#     {"name": "ABFRL",           "bse_code": "535755"},  # Aditya Birla Fashion & Retail
#     {"name": "SHK",             "bse_code": "539450"},  # S H Kelkar
#     {"name": "BLS",             "bse_code": "540073"},
#     {"name": "APOLLOTYRE",      "bse_code": "500877"},
#     {"name": "OMINFRA",         "bse_code": "531092"},
#     {"name": "TRITURBINE",      "bse_code": "533655"},
#     {"name": "PRAJIND",         "bse_code": "522205"},
#     {"name": "AHLUCONT",        "bse_code": "532811"},
#     {"name": "INDHOTEL",        "bse_code": "500850"},
#     {"name": "INDIGO",          "bse_code": "539448"},
#     {"name": "M&MFIN",          "bse_code": "532720"},
#     {"name": "PVRINOX",         "bse_code": "532689"},
#     {"name": "VIPIND",          "bse_code": "507880"},
#     {"name": "VGUARD",          "bse_code": "532953"},
#     {"name": "WABAG",           "bse_code": "533269"},  # VA Tech Wabag
#     {"name": "WONDERLA",        "bse_code": "538268"},
#     {"name": "AXISBANK",        "bse_code": "532215"},
#     {"name": "BATAINDIA",       "bse_code": "500043"},
#     {"name": "FLUIDOMAT",       "bse_code": "522017"},        
#     {"name": "HDFCBANK",        "bse_code": "500180"},
#     {"name": "ICICIBANK",       "bse_code": "532174"},
#     {"name": "ITCHOTEL",        "bse_code": "544325"},  # ITC Hotels
#     {"name": "ITC",             "bse_code": "500875"},
#     {"name": "INFOSYS",         "bse_code": "500209"},
#     {"name": "KEI",             "bse_code": "517569"},
#     {"name": "LT",              "bse_code": "500510"},
#     {"name": "LEMONTREE",       "bse_code": "540063"},
#     {"name": "MANAPPURAM",      "bse_code": "531213"},
#     {"name": "PNB",             "bse_code": "532461"},
#     {"name": "SIEMENS",         "bse_code": "500650"},
#     {"name": "SWSOLAR",         "bse_code": "543248"},
#     {"name": "TATAMOTORS",      "bse_code": "500570"},
#     {"name": "VEDANTFASHION",   "bse_code": "543389"},
#     {"name": "VOLTAS",          "bse_code": "500575"},
#     {"name": "ANGELONE",        "bse_code": "543235"},
#     {"name": "BHEL",            "bse_code": "500103"},
#     {"name": "MOLDTEK",         "bse_code": "540287"},
#     {"name": "DABUR",           "bse_code": "500096"},
#     {"name": "HINDUNILVR",      "bse_code": "500696"},
#     {"name": "JUBLFOOD",        "bse_code": "543225"},
#     {"name": "KOTAKBANK",       "bse_code": "500247"},
#     {"name": "RIL",             "bse_code": "500325"},
#     {"name": "VMM",             "bse_code": "544307"},
#     {"name": "ELECON",          "bse_code": "505700"}
# ]

def upload_to_github(filepath, repo, path_in_repo, branch="main_sensex"):
    token = st.secrets.get("GITHUB_TOKEN", os.getenv("GITHUB_TOKEN"))
    if not token:
        raise ValueError("GitHub token not found")

    with open(filepath, "rb") as f:
        content = f.read()
    content_b64 = base64.b64encode(content).decode()

    url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    get_resp = requests.get(url, headers=headers, params={"ref": branch})
    sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None

    data = {
        "message": f"Upload {path_in_repo}",
        "content": content_b64,
        "branch": branch
    }
    if sha:
        data["sha"] = sha

    put_resp = requests.put(url, headers=headers, json=data)
    if put_resp.status_code not in (200, 201):
        raise Exception(f"Upload failed: {put_resp.status_code} - {put_resp.text}")



def call_gpt(raw_input_text: str) -> dict:
    # Retrieve the API key
    my_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    try:
        client = OpenAI(api_key=my_api_key)
        user_prompt = f'''
        You're an expert in reading corporate filings on Indian stocks.
        
        Understand the following filing and analyze it carefully.
        
        Respond **only** in valid JSON format with exactly two keys:
        1. "summary": a brief summary of the filing in maximum 3 lines, bullet points. First word should be either "Important." or "Not important.", depending upon how impactful the filing is for stock prices of this company.
        2. "sentiment": how bullish are you on its stock based on the information in the filing. 100= very bullish, -100= very bearish.
        3. "category": Categoriese this news in a news category between 1-3 words only. But if the filing text contains "audio recording" or "transcript" in the first 300 words of the text, write "earnings_call_transcript" as category.
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


def update_filings_data_tmp(days=2, debug=False, status_callback=None, progress_callback=None, log_callback=None):
    # Configuration
    SCRIP_CODE = "533282"  # Gravita Industries BSE code

    
    # Date range: last 30 days
    end_date = datetime.today()
    start_date = end_date - timedelta(days=30)
    date_fmt = "%Y%m%d"
    params = {
        "pageno": 1,
        "strPrevDate": start_date.strftime(date_fmt),
        "strToDate": end_date.strftime(date_fmt),
        "strScrip": SCRIP_CODE,
        "strType": "C",      # corporate announcements
        "strCat": "-1",      # all categories
        "strSearch": "P",    # public announcements
        "subcategory": ""    # all subcategories
    }
    # headers = {
    #     "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/115.0 Safari/537.36",
    #     "Referer": "https://www.bseindia.com/"
    # }
    headers = {"User-Agent":"Mozilla/5.0","Referer":"https://www.bseindia.com/"}
    
    announcements = []  # to collect announcements
    
    # Loop through pages until no more data
    while True:
        resp = requests.get("https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w", 
                            params=params, headers=headers)
        
        if resp.status_code != 200:
            if debug and log_callback:
                log_callback(f"HTTP error: {resp.status_code} for SCRIP {SCRIP_CODE}")
            break
        
        try:
            data = resp.json()
        except ValueError:
            if debug and log_callback:
                log_callback(f"Non-JSON response for SCRIP {SCRIP_CODE}: {resp.text[:200]}")
            break
        
        # Stop if no data or on error
        if "Table" not in data or not data["Table"]:
            break
        announcements.extend(data["Table"])
        params["pageno"] += 1  # next page
    
    # Logging: print sample announcement for inspection
    if announcements:
        print("Sample Announcement:")
        print(announcements[0])
    
    # Process each announcement to download attachment if available
    for ann in announcements:
        title = ann.get("HEADLINE") or ann.get("NEWSSUB")
        datetime_str = ann.get("DissemDT", "")
        date_part = datetime_str.split("T")[0] if "T" in datetime_str else datetime_str
        
        # Build the attachment URL if a PDF is present
        attachment_name = ann.get("ATTACHMENTNAME")
        if attachment_name:
            file_url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment_name}"
            file_path = os.path.join(OUTPUT_DIR, attachment_name)
            
            # Log attachment name and URL for verification
            #print(f"Attachment: {attachment_name} -> URL: {file_url}")
            if debug and log_callback:
                        log_callback(f"Attachment: {attachment_name} -> URL: {file_url}")
            
            file_resp = requests.get(file_url, headers=headers)
            if file_resp.status_code == 200:
                with open(file_path, "wb") as f:
                    #f.write(file_resp.content)
                    #print(f"Downloaded: {title[:50]}... -> {file_path}")
                    if debug and log_callback:
                            log_callback(f"Downloaded: {title[:50]}... -> {file_path}")
            else:
                #print(f"Failed to download {attachment_name}: HTTP {file_resp.status_code}")
                if debug and log_callback:
                        log_callback(f"Failed to download {attachment_name}: HTTP {file_resp.status_code}")



import random
import requests
import time
from datetime import datetime, timedelta
import os
import pandas as pd
import csv
import json
from io import BytesIO
from PyPDF2 import PdfReader
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlencode

def get_free_proxies(max_proxies=50, timeout=10):
    """
    Fetch and validate free proxies from multiple sources.
    Returns a list of working proxy URLs (e.g., 'http://ip:port').
    """
    proxies = []
    sources = [
        # Geonode API
        {
            "url": "https://proxylist.geonode.com/api/proxy-list?limit=50&sort_by=lastChecked&sort_type=desc",
            "type": "api",
            "extract": lambda data: [(item["ip"], item["port"]) for item in data.get("data", []) if "http" in item.get("protocols", []) or "https" in item.get("protocols", [])]
        },
        # ProxyScrape API (India-based proxies)
        {
            "url": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=IN",
            "type": "text",
            "extract": lambda text: [(line.strip(), None) for line in text.splitlines()]
        },
        # Fallback static proxy (replace with fresh ones if needed)
        {
            "url": None,
            "type": "static",
            "extract": lambda _: [("138.68.60.8", "3128"), ("51.210.19.141", "80")]
        }
    ]

    for source in sources:
        if len(proxies) >= max_proxies:
            break
        try:
            if source["type"] == "api":
                response = requests.get(source["url"], timeout=timeout)
                response.raise_for_status()
                proxy_pairs = source["extract"](response.json())
            elif source["type"] == "text":
                response = requests.get(source["url"], timeout=timeout)
                response.raise_for_status()
                proxy_pairs = source["extract"](response.text)
            else:  # static
                proxy_pairs = source["extract"](None)

            for ip, port in proxy_pairs:
                proxy_url = f"http://{ip}:{port}" if port else f"http://{ip}"
                # Validate proxy with a simple URL to avoid BSE India's anti-bot
                try:
                    test_response = requests.get(
                        "https://httpbin.org/ip",  # Simpler test URL
                        proxies={"http": proxy_url, "https": proxy_url},
                        timeout=timeout,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0"}
                    )
                    if test_response.status_code == 200:
                        proxies.append(proxy_url)
                        if len(proxies) >= max_proxies:
                            break
                except Exception as e:
                    print(f"Proxy validation failed for {proxy_url}: {e}")
        except Exception as e:
            print(f"Failed to fetch proxies from {source.get('url', 'static')}: {e}")

    return proxies if proxies else ["http://138.68.60.8:3128"]  # Fallback proxy

def update_filings_data(days=2, debug=False, status_callback=None, progress_callback=None, log_callback=None, tickers=None):
    """
    Scrape and GPT process filings; append only new filings to existing ticker CSVs.
    Returns total new records appended.
    """
    if tickers is None:
        tickers = [...]  # Your default ticker list (replace with actual list)

    BSE_API = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ]
    HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.bseindia.com/",
        "Connection": "keep-alive"
    }

    start = datetime.today() - timedelta(days=days)
    end = datetime.today()
    prev = start.strftime("%Y%m%d")
    to = end.strftime("%Y%m%d")

    total_new = 0
    n = len(tickers)
    if debug and log_callback:
        log_callback(f"{n} tickers to process from {start} to {end}")

    # Fetch and validate free proxies
    proxies = get_free_proxies()
    if debug and log_callback:
        log_callback(f"Available proxies: {len(proxies)}")

    # Initialize session for persistent cookies
    session = requests.Session()
    session.headers.update(HEADERS)

    # Add retry strategy to session
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    # Fetch cookies
    proxy_index = 0
    max_proxy_tries = len(proxies) if proxies else 1
    for _ in range(max_proxy_tries):
        try:
            session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
            proxy_url = proxies[proxy_index % len(proxies)] if proxies else None
            if debug and log_callback:
                log_callback(f"Using proxy for cookies: {proxy_url or 'direct'}")
            main_page = session.get(
                "https://www.bseindia.com/",
                proxies={"http": proxy_url, "https": proxy_url} if proxy_url else None,
                timeout=30  # Increased timeout
            )
            main_page.raise_for_status()
            break
        except Exception as e:
            if debug and log_callback:
                log_callback(f"Cookie fetch error with proxy {proxy_url or 'direct'}: {e}")
            proxy_index += 1
            if proxy_index >= max_proxy_tries:
                if debug and log_callback:
                    log_callback("All proxies failed for cookies; continuing without cookies")
                break

    for i, tk in enumerate(tickers, 1):
        if status_callback: status_callback(f"Processing {tk['name']} ({i}/{n})")
        if progress_callback: progress_callback((i-1)/n)

        csv_path = f"data/portfolio_stocks_gpt/{tk['name']}.csv"
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
            time.sleep(random.uniform(1, 3))  # Reduced delay

            proxy_index = 0
            for _ in range(max_proxy_tries):
                try:
                    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
                    proxy_url = proxies[proxy_index % len(proxies)] if proxies else None
                    if debug and log_callback:
                        log_callback(f"Using proxy: {proxy_url or 'direct'}")
                    req = requests.Request('GET', BSE_API, params=payload)
                    prepared = req.prepare()
                    full_url = prepared.url
                    response = session.get(
                        full_url,
                        proxies={"http": proxy_url, "https": proxy_url} if proxy_url else None,
                        timeout=30  # Increased timeout
                    )
                    response.raise_for_status()
                    data = response.json().get("Table", [])
                    if not data: break
                    ann.extend(data)
                    payload["pageno"] += 1
                    break
                except Exception as e:
                    if debug and log_callback:
                        log_callback(f"Fetch error {tk['name']} with proxy {proxy_url or 'direct'}: {e}")
                        if 'response' in locals():
                            log_callback(f"Fetch response headers: {response.headers}")
                            log_callback(f"Fetch response content: {response.text[:500]}")
                    proxy_index += 1
                    if proxy_index >= max_proxy_tries:
                        if debug and log_callback:
                            log_callback(f"All proxies failed for {tk['name']}; skipping")
                        break
            else:
                break  # Exit pagination loop if all proxies fail
            if not data:
                break

        if debug and log_callback:
            log_callback(f"{tk['name']}: {len(ann)} announcements")

        new_records = []
        for item in ann:
            attach = item.get("ATTACHMENTNAME","").strip()
            if not attach: continue

            pdf = None; pdf_url = None
            for path in [
                f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attach}",
                f"https://www.bseindia.com/xml-data/corpfiling/AttachHis/{attach}"
            ]:
                if path in existing_urls:
                    if debug and log_callback:
                        log_callback(f"⏩ Skipping already processed URL: {path}")
                    pdf_url = None
                    break

                time.sleep(random.uniform(1, 3))  # Reduced delay

                proxy_index = 0
                for _ in range(max_proxy_tries):
                    try:
                        session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
                        proxy_url = proxies[proxy_index % len(proxies)] if proxies else None
                        if debug and log_callback:
                            log_callback(f"Using proxy: {proxy_url or 'direct'}")
                        tmp = session.get(
                            path,
                            proxies={"http": proxy_url, "https": proxy_url} if proxy_url else None,
                            timeout=30  # Increased timeout
                        )
                        tmp.raise_for_status()
                        pdf = tmp.content
                        pdf_url = path
                        break
                    except Exception as e:
                        if debug and log_callback:
                            log_callback(f"PDF fetch error for {path} with proxy {proxy_url or 'direct'}: {e}")
                        proxy_index += 1
                        if proxy_index >= max_proxy_tries:
                            if debug and log_callback:
                                log_callback(f"All proxies failed for PDF {path}; skipping")
                            break
                else:
                    break  # Exit PDF loop if all proxies fail
                if pdf_url:
                    break

            if not pdf_url:
                continue

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
            
            if not gpt_response:
                continue
            
            try:
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

        if new_records:
            write_header = not os.path.isfile(csv_path)
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=new_records[0].keys())
                if write_header: writer.writeheader()
                writer.writerows(new_records)
            total_new += len(new_records)

            try:
                upload_to_github(
                    filepath=csv_path,
                    repo="imviveksaini/sensex-filings-app",
                    path_in_repo=f"data/portfolio_stocks_gpt/{tk['name']}.csv",
                    branch="main_sensex"
                )
            except Exception as e:
                if debug and log_callback:
                    log_callback(f"GitHub upload failed for {tk['name']}: {e}")

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
    base_url = "https://raw.githubusercontent.com/imviveksaini/sensex-filings-app/main_sensex/data/portfolio_stocks_gpt"


    dfs = []
    for tk in tickers:
        ticker_name = tk["name"]
        url = f"{base_url}/{ticker_name}.csv"
        try:
            df = pd.read_csv(url, parse_dates=['date'])
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
