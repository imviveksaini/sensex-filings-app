import os
import pandas as pd
import openai
from time import sleep

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
            temperature=0.3,
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"GPT API call failed: {e}")
        return None

def enrich_and_save_gpt(df: pd.DataFrame, ticker: str):
    """
    Enrich the DataFrame with GPT-based summary, sentiment, and category fields,
    and save the enriched file without overwriting existing files.
    """
    output_dir = "data/portfolio_stocks_gpt"
    os.makedirs(output_dir, exist_ok=True)

    for idx, row in df.iterrows():
        if 'input_gpt' not in row or not isinstance(row['input_gpt'], str):
            continue

        if all(k in row and pd.notna(row[k]) for k in ['summary_gpt', 'sentiment_gpt', 'category_gpt']):
            continue

        input_text = row['input_gpt'][:4000]  # Truncate to avoid token overflow
        prompt = (
            f"Please analyze the following financial disclosure and provide:\n"
            f"1. A concise summary\n"
            f"2. The overall sentiment (Positive, Neutral, Negative)\n"
            f"3. A suitable category (e.g., Revenue, Risk, Expansion, etc.)\n\n"
            f"Text:\n{input_text}"
        )

        result = call_gpt(prompt)
        if result:
            try:
                # Very basic parsing, better with structured output parsing if needed
                lines = result.split('\n')
                summary = next((line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("1. summary")), "")
                sentiment = next((line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("2. sentiment")), "")
                category = next((line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("3. category")), "")
            except Exception as e:
                print(f"Failed to parse GPT output for row {idx}: {e}")
                continue

            df.at[idx, 'summary_gpt'] = summary
            df.at[idx, 'sentiment_gpt'] = sentiment
            df.at[idx, 'category_gpt'] = category

            sleep(1)  # To avoid hitting rate limits

    output_path = os.path.join(output_dir, f"{ticker}.parquet")
    if not os.path.exists(output_path):
        df.to_parquet(output_path, index=False)
