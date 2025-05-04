# bonus_summary.py

import requests
from io import BytesIO
from PyPDF2 import PdfReader
from openai import OpenAI
import os
import streamlit as st
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}

def download_url(url: str) -> tuple[str, bytes | None]:
    """
    Downloads content from the URL and returns (content_type, content_bytes)
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.headers.get("Content-Type", ""), response.content
    except Exception as e:
        print(f"Failed to fetch content from {url}: {e}")
        return "", None

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text.strip()
    except Exception as e:
        print(f"Text extraction error (PDF): {e}")
        return ""

def extract_text_from_html(html_bytes: bytes) -> str:
    try:
        soup = BeautifulSoup(html_bytes, "html.parser")
        # Remove scripts and styles
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"Text extraction error (HTML): {e}")
        return ""

def call_gpt_for_summary(raw_input_text: str) -> dict | None:
    try:
        my_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        client = OpenAI(api_key=my_api_key)
        user_prompt = f'''
You're an expert in reading news stories, research reports, and other financial texts on Indian stocks.

Understand the following text and analyze it carefully.

Respond **only** in valid JSON format with exactly the following keys:
1. "date": extract the date on which the text has been reported, in yyyy-mm-dd format.
2. "summary": a brief summary of the financial information in the text. Maximum 2 lines, bullet points.
3. "bullishness_indicator (-100 to 100)": how bullish are you on its stock based on the information in the text. 100 = very bullish, -100 = very bearish.
4. "headwinds": if you found any business headwinds, write here. Maximum 3 lines, bullet points.
5. "tailwinds": if you found any business tailwinds, write here. Maximum 3 lines, bullet points.
6. "key_forward_looking_statements": Write here if you found any forward-looking statements. Maximum 3 lines, bullet points.
7. "management_guidance": Write here if company management provided any revenue growth, margin or eps growth guidance. Maximum 3 lines, bullet points.
8. "potential_upside": If available, give analyst target price and potential upside in %.


Filing text:
{raw_input_text}
'''
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            temperature=0,
            messages=[{"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT API call failed: {e}")
        return None

def summarize_filing_from_url(url: str) -> str | None:
    content_type, content = download_url(url)
    if not content:
        return "❌ Failed to download content."

    # Determine parser
    if url.lower().endswith(".pdf") or "application/pdf" in content_type:
        text = extract_text_from_pdf(content)
    elif "text/html" in content_type or url.lower().endswith(".html"):
        text = extract_text_from_html(content)
    else:
        return "❌ Unsupported file format or could not determine file type."

    if not text.strip():
        return "❌ No text could be extracted from the document."

    text = text[:4000]  # truncate to stay within token limits
    gpt_response = call_gpt_for_summary(text)
    if not gpt_response:
        return "❌ Failed to get GPT summary."

    return gpt_response
