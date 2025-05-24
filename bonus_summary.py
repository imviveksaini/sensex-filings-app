# bonus_summary.py

import requests
from io import BytesIO
from PyPDF2 import PdfReader
from openai import OpenAI
import os
import streamlit as st
from bs4 import BeautifulSoup
import tempfile
import whisper
import traceback

from pydub import AudioSegment
from pydub.utils import make_chunks
import concurrent.futures # For parallel API calls


@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")  # or "small", etc.

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

def call_gpt_for_summary_corp_filing(raw_input_text: str, gpt_model: str) -> dict | None:
    try:
        my_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        client = OpenAI(api_key=my_api_key)
        user_prompt = f'''
You're an expert in reading corporate filings on Indian stocks.

Understand the following text and analyze it carefully.

Respond **only** in valid JSON format with exactly the following keys:
1. "date": extract the date on which the text has been reported, in yyyy-mm-dd format.
2. "event": Write which key event is being talked about in 1-4 words.
3. "relevance": Carefully analyse and tell me if the information is material for stock prices. Just write "important" or "not important".
4. "filing_summary": a brief summary of the financial information in the text. Maximum 6 lines, bullet points.
5. "bullishness_indicator (-100 to 100)": how bullish are you on its stock based on the information in the text. 100 = very bullish, -100 = very bearish.



Filing text:
{raw_input_text}
'''
        response = client.chat.completions.create(
            model=gpt_model,
            temperature=0,
            messages=[{"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT API call failed: {e}")
        return None


def call_gpt_for_summary_earnings_call(raw_input_text: str, gpt_model: str) -> dict | None:
    try:
        my_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        client = OpenAI(api_key=my_api_key)
        user_prompt = f'''
You're an expert in reading earnings conference call transcripts on Indian stocks.

Understand the following text and analyze it carefully.

Respond **only** in valid JSON format with exactly the following keys:
1. "date": extract the date on which the text has been reported, in yyyy-mm-dd format.
2. "business model": What's the business model of this company, what are the key revenue drivers, what are the key cost drivers? Answer based on the earnings call text provided. Maximum 5 lines, bullet points.
3. "summary_management_discussion": a brief summary of the financial information in the text reported by the CFO. Maximum 5 lines, bullet points.
4. "summary_Q&A": a brief summary of the answers given by management asked by analysts. Focus on key risks and opportunities for the next 1-2 quarters. Maximum 5 lines, bullet points.
5. "the good things reported by management": a brief summary of the good things in the business financials from the answers given by management asked by analysts. Maximum 5 lines, bullet points.
6. "tailwinds": if management talked about any business tailwinds that could boost growth in future, write here. Maximum 3 lines, bullet points. Write only when you're very sure.
7. "the bad things reported by management": a brief summary of the bad things/red flags in the business financials from the answers given by management asked by analysts. Maximum 5 lines, bullet points.
8. "headwinds": if management talked about any business headwinds that could deter growth in future, write here. Maximum 3 lines, bullet points. Write only when you're very sure.
9. "management_guidance": Write here if company management provided any revenue growth, margin or eps growth guidance or any other forward looking statements on company prospects. Maximum 3 lines, bullet points.
10. "bullishness_indicator (-100 to 100)": how bullish are you on this stock for the next 1-3 quarters based on the text output you generated above. 100 = very bullish, -100 = very bearish.


Filing text:
{raw_input_text}
'''
        response = client.chat.completions.create(
            model=gpt_model,
            temperature=0,
            messages=[{"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT API call failed: {e}")
        return None


def call_gpt_for_summary_research_report(raw_input_text: str, gpt_model: str) -> dict | None:
    try:
        my_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        client = OpenAI(api_key=my_api_key)
        user_prompt = f'''
You're an expert in reading research reports on Indian stocks.

Understand the following text and analyze it carefully.

Respond **only** in valid JSON format with exactly the following keys:
1. "date": extract the date on which the research report has been published, in yyyy-mm-dd format.
2. "report_summary": a brief summary of the financial information in the text. Maximum 5 lines, bullet points.
3. "bullishness_indicator (-100 to 100)": how bullish are you on its stock based on the information in the text. 100 = very bullish, -100 = very bearish.
4. "headwinds": if analyst wrote about any business headwinds, write here. Maximum 3 lines, bullet points.
5. "tailwinds": iif analyst wrote about any business tailwinds, write here. Maximum 3 lines, bullet points.
6. "key_analyst_projections": Write here if analyst made any future projections on revenue growth, eps growth or margins. Maximum 3 lines, bullet points.
7. "potential_upside": If available, give analyst target price and potential upside in %.


Filing text:
{raw_input_text}
'''
        response = client.chat.completions.create(
            model=gpt_model,
            temperature=0,
            messages=[{"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT API call failed: {e}")
        return None

def call_gpt_for_summary_news(raw_input_text: str, gpt_model: str) -> dict | None:
    try:
        my_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        client = OpenAI(api_key=my_api_key)
        user_prompt = f'''
You're an expert in reading news stories on Indian stocks.

Understand the following text and analyze it carefully.

Respond **only** in valid JSON format with exactly the following keys:
1. "date": extract the date on which the news story has been published, in yyyy-mm-dd format.
2. "news_summary": a brief summary of the financial information in the text. Maximum 5 lines, bullet points.
3. "bullishness_indicator (-100 to 100)": how bullish are you on its stock based on the information in the text. 100 = very bullish, -100 = very bearish.
4. "stocks_discussed": List the stocks discussed in this article.
5. "potential_upside": If available, give analyst target price and potential upside in % for each of the stocks discussed.


Filing text:
{raw_input_text}
'''
        response = client.chat.completions.create(
            model=gpt_model,
            temperature=0,
            messages=[{"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT API call failed: {e}")
        return None


def call_gpt_for_summary_general(raw_input_text: str, gpt_model: str) -> dict | None:
    try:
        my_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        client = OpenAI(api_key=my_api_key)
        user_prompt = f'''
You're an expert in reading text on Indian stocks and economy.

Understand the following text and analyze it carefully.

Respond **only** in valid JSON format with exactly the following keys:
1. "date": extract the date on which the article has been published, in yyyy-mm-dd format.
2. "summary": a brief summary of the information in the text. Maximum 5 lines, bullet points.



Filing text:
{raw_input_text}
'''
        response = client.chat.completions.create(
            model=gpt_model,
            temperature=0,
            messages=[{"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT API call failed: {e}")
        return None


def answer_a_question(raw_input_text: str, question: str, gpt_model: str) -> dict | None:
    try:
        my_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        client = OpenAI(api_key=my_api_key)
        user_prompt = f'''
You're an expert in reading text on Indian stocks and economy.

Answer the following question after reading the entire text:
Question:
{question}

Respond **only** in valid JSON format with exactly the following keys:
1. "answer": Give an answer within 200-500 characters.

Text input:
{raw_input_text}
'''
        response = client.chat.completions.create(
            model=gpt_model,
            temperature=0,
            messages=[{"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT API call failed: {e}")
        return None



# def transcribe_audio_from_url_local(mp3_url: str) -> str | None:
#     """
#     Downloads and transcribes an MP3 audio file using a local Whisper model.
    
#     Parameters:
#     - mp3_url (str): Direct URL to the MP3 file.

#     Returns:
#     - Transcript (str) or None on failure.
#     """
#     try:
#         response = requests.get(mp3_url, stream=True)
#         response.raise_for_status()

#         with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp_file:
#             for chunk in response.iter_content(chunk_size=8192):
#                 tmp_file.write(chunk)
#             tmp_file.flush()

#             model = whisper.load_model("base")  # you can change to "small", "medium", or "large"
#             result = model.transcribe(tmp_file.name)
#             return result["text"]
#     except Exception as e:
#         print("❌ Transcription failed:")
#         traceback.print_exc()
#         return None



def transcribe_audio_from_url_local(mp3_url: str) -> str | None:
    try:
        response = requests.get(mp3_url, stream=True)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_file.flush()

            model = load_whisper_model()
            result = model.transcribe(tmp_file.name)
            return result["text"]
    except Exception as e:
        print("❌ Transcription failed:")
        traceback.print_exc()
        return None


def transcribe_audio_whisper1(mp3_path: str) -> str | None:
    """
    Transcribes an MP3 audio file using OpenAI Whisper and returns the transcript.
    
    Parameters:
    - mp3_path (str): Path to the .mp3 file

    Returns:
    - Transcript (str) or None on failure
    """
    my_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    try:
        client = OpenAI(api_key=my_api_key)

        with open(mp3_path, "rb") as audio_file:
            transcript_response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript_response
    except Exception as e:
        print(f"Transcription failed: {e}")
        return None

# --- NEW FUNCTION FOR CHUNKING AND PARALLEL TRANSCRIPTION ---
def transcribe_large_audio_whisper1(mp3_url: str, chunk_length_min: int = 5) -> str | None:
    """
    Downloads large audio, chunks it, transcribes chunks in parallel using Whisper-1 API,
    and returns the concatenated transcript.
    """
    st.info(f"Downloading audio from {mp3_url}...")
    content_type, audio_bytes = download_url(mp3_url)
    if not audio_bytes:
        return None

    # Save the whole file to a temporary location for pydub to process
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_full_audio_file:
        tmp_full_audio_file.write(audio_bytes)
        full_audio_path = tmp_full_audio_file.name

    try:
        st.info("Loading audio for chunking...")
        audio = AudioSegment.from_file(full_audio_path)
        chunk_length_ms = chunk_length_min * 60 * 1000 # Convert minutes to milliseconds
        chunks = make_chunks(audio, chunk_length_ms)

        transcripts = [None] * len(chunks)
        temp_chunk_paths = []

        st.info(f"Splitting audio into {len(chunks)} chunks and transcribing in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor: # Adjust max_workers as needed
            future_to_chunk = {}
            for i, chunk in enumerate(chunks):
                # Save each chunk to a temp file
                with tempfile.NamedTemporaryFile(suffix=f"_{i}.mp3", delete=False) as tmp_chunk_file:
                    chunk.export(tmp_chunk_file.name, format="mp3")
                    chunk_path = tmp_chunk_file.name
                    temp_chunk_paths.append(chunk_path) # Keep track for cleanup
                    future_to_chunk[executor.submit(transcribe_audio_whisper1, chunk_path)] = i

            # --- FIX STARTS HERE ---
            total_chunks = len(chunks)
            completed_chunks = 0
            
            # Initialize the progress bar outside the loop
            progress_bar = st.progress(0, text=f"Transcribing {total_chunks} chunks...")
    
            for future in concurrent.futures.as_completed(future_to_chunk):
                completed_chunks += 1
                # Calculate the progress percentage (0.0 to 1.0)
                current_progress = completed_chunks / total_chunks
                
                # Update the progress bar
                progress_bar.progress(current_progress, text=f"Transcribing chunk {completed_chunks}/{total_chunks}...")
    
                i = future_to_chunk[future]
                try:
                    transcripts[i] = future.result()
                    if transcripts[i] is None:
                        st.error(f"Failed to transcribe chunk {i+1}. Result will be incomplete.")
                except Exception as exc:
                    st.error(f"Chunk {i+1} generated an exception: {exc}")
                    transcripts[i] = "" # Assign empty string to maintain order
    
            # Ensure the progress bar reaches 100% at the end
            progress_bar.progress(1.0, text="All chunks transcribed!")

            # --- FIX ENDS HERE ---


        # Clean up temporary chunk files
        for path in temp_chunk_paths:
            os.remove(path)

        # Concatenate transcripts
        final_transcript = " ".join([t for t in transcripts if t is not None])

        # --- COST CALCULATION & DISPLAY ---
        WHISPER_API_COST_PER_MINUTE = 0.006 # As of my last update, check OpenAI for current pricing       
        # Convert total duration from milliseconds to minutes
        total_audio_duration_minutes = total_audio_duration_ms / (1000 * 60)       
        estimated_cost = total_audio_duration_minutes * WHISPER_API_COST_PER_MINUTE        
        st.success(f"Estimated cost: **${estimated_cost:.4f}** (based on {total_audio_duration_minutes:.2f} minutes of audio @ ${WHISPER_API_COST_PER_MINUTE}/min).")
        
        return final_transcript.strip()

    except Exception as e:
        st.error(f"Error during large audio transcription: {e}")
        traceback.print_exc()
        return None
    finally:
        # Clean up the full audio file
        if os.path.exists(full_audio_path):
            os.remove(full_audio_path)


def summarize_filing(
    url: str | None = None,
    file: bytes | None = None,
    doc_type: str = "general",
    gpt_model: str = "gpt-4.1-nano"
) -> tuple[str, str] | None:
    """
    Summarizes a financial document (PDF, HTML, or MP3) from a URL or uploaded file using GPT.

    Parameters:
    - url: URL to the document (PDF, HTML, or MP3)
    - file: Uploaded PDF file content (as bytes)
    - doc_type: Type of document for specialized GPT summary

    Returns:
    - Tuple of (summary, extracted_text) or (None, error_message)
    """
    
    if file:
        text = extract_text_from_pdf(file)
        source_description = "uploaded file"
    
    elif url:
        if url.lower().endswith(".mp3"):
            #text = transcribe_audio_from_url_local(url)
            text = transcribe_large_audio_whisper1(url, 5)
            if not text:
                return None, "❌ Transcription failed."
            source_description = "transcribed audio file"
        else:
            content_type, content = download_url(url)
            if not content:
                return None, "❌ Failed to download content."

            if url.lower().endswith(".pdf") or "application/pdf" in content_type:
                text = extract_text_from_pdf(content)
            elif "text/html" in content_type or url.lower().endswith(".html"):
                text = extract_text_from_html(content)
            else:
                return None, "❌ Unsupported file format or could not determine file type."

            source_description = url
    else:
        return None, "❌ No source provided. Provide either a URL or a PDF/MP3 file."

    if not text or not text.strip():
        return None, f"❌ No text could be extracted from the {source_description}."

    text = text[:80000]  # truncate to stay within GPT token limits

    summarizers = {
        "earnings_call_transcript": call_gpt_for_summary_earnings_call,
        "research_report": call_gpt_for_summary_research_report,
        "news_story": call_gpt_for_summary_news,
        "corporate_filing": call_gpt_for_summary_corp_filing,
        "general": call_gpt_for_summary_general
    }

    summarizer = summarizers.get(doc_type, call_gpt_for_summary_general)
    gpt_response = summarizer(text, gpt_model)

    if not gpt_response:
        return None, "❌ Failed to get GPT summary."

    return gpt_response, text
