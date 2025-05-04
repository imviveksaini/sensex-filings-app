# bonus_summary.py

import requests
from io import BytesIO
from PyPDF2 import PdfReader
from openai import OpenAI
import os
import streamlit as st

HEADERS = {"User-Agent": "Mozilla/5.0"}

def download_pdf(pdf_url: str) -> bytes | None:
    try:
        response = requests.get(pdf_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Failed to fetch PDF from {pdf_url}: {e}")
        return None

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text.strip()
    except Exception as e:
        print(f"Text extraction error: {e}")
        return ""

def call_gpt_for_summary(raw_input_text: str) -> dict | None:
    try:
        my_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        client = OpenAI(api_key=my_api_key)
        user_prompt = f'''
You're an expert in reading news stories, research reports, and other financial texts on Indian stocks.

Understand the following filing and analyze it carefully.

Respond **only** in valid JSON format with exactly the following keys:
1. "summary": a brief summary of the text in maximum two sentences.
2. "sentiment": how bullish are you on its stock based on the information in the text. 100 = very bullish, -100 = very bearish.
3. "headwinds": if you found any business headwinds, write here. Maximum 3 lines, bullet points.
4. "tailwinds": if you found any business tailwinds, write here. Maximum 3 lines, bullet points.
5. "key_forward_looking_statements": Write here if you found any forward-looking statements. Maximum 3 lines, bullet points.

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

def summarize_filing_from_url(pdf_url: str) -> str | None:
    pdf = download_pdf(pdf_url)
    if not pdf:
        return "❌ Failed to download PDF."

    text = extract_text_from_pdf(pdf)    
    if not text:
        return "❌ No text could be extracted from the PDF."

    text =text[:4000]
    gpt_response = call_gpt_for_summary(text)
    if not gpt_response:
        return "❌ Failed to get GPT summary."

    return gpt_response
