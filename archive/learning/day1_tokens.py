# archive/learning/day1_tokens.py
"""
Day 1, Lesson 3: tokens, context windows, and cost.

Run from src2/:
    python day1_tokens.py
"""

import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = "gemini-3.5-flash-lite"
BASE = "https://generativelanguage.googleapis.com/v1beta"
HEADERS = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}

# Paid-tier prices, USD per 1M tokens (from the pricing page; check it yourself)
PRICE_IN = 0.30
PRICE_OUT = 2.50   # includes thinking tokens


# --- 1. Ask the API about the model itself --------------------------------
def model_info():
    resp = requests.get(f"{BASE}/models/{MODEL}", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


# --- 2. Count tokens without generating anything (this call is free) -------
def count_tokens(text):
    body = {"contents": [{"role": "user", "parts": [{"text": text}]}]}
    resp = requests.post(f"{BASE}/models/{MODEL}:countTokens",
                         headers=HEADERS, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()["totalTokens"]


# --- 3. Cost of one call -----------------------------------------------------
def cost(input_tokens, output_tokens):
    return input_tokens / 1e6 * PRICE_IN + output_tokens / 1e6 * PRICE_OUT


if __name__ == "__main__":
    print("\n===== 1. What the model says about itself =====")
    info = model_info()
    print("name:              ", info.get("name"))
    print("input token limit: ", info.get("inputTokenLimit"))
    print("output token limit:", info.get("outputTokenLimit"))

    print("\n===== 2. Tokens for different kinds of text =====")
    samples = {
        "plain English": "Bank reconciliation matches your bank transactions with your invoices.",
        "bug ID":        "BUG-2310-01",
        "API header":    "X-RateLimit-Remaining",
        "API path":      "GET /v2/customers/{customer_id}/statements?date_from=2026-01-01",
        "JSON":          '{"bug_id": "BUG-2310-01", "severity": "Critical", "status": "Open"}',
        "numbers":       "Invoice total: $10,400.00 for 260 seats at $40 each.",
        "Spanish":       "La conciliación bancaria compara sus transacciones con sus facturas.",
    }
    print(f"{'kind':15s} {'chars':>6s} {'words':>6s} {'tokens':>7s} {'chars/token':>12s}")
    for kind, text in samples.items():
        t = count_tokens(text)
        print(f"{kind:15s} {len(text):6d} {len(text.split()):6d} {t:7d} {len(text) / t:12.1f}")

    print("\n===== 3. Raw HTML vs cleaned text =====")
    page = Path("../data/invoicepilot/corpus/help_center/bank-reconciliation/auto-match.html")
    raw = page.read_text(encoding="utf-8")
    article = re.search(r"<article>(.*?)</article>", raw, re.S).group(1)
    clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", article)).strip()
    raw_t, clean_t = count_tokens(raw), count_tokens(clean)
    print(f"raw HTML page:  {raw_t:5d} tokens")
    print(f"article text:   {clean_t:5d} tokens")
    print(f"wasted on boilerplate and tags: {raw_t - clean_t} tokens ({(raw_t - clean_t) / raw_t:.0%})")

    print("\n===== 4. Cost estimates =====")
    print(f"price per 1k input tokens:  ${PRICE_IN / 1000:.6f}")
    print(f"price per 1k output tokens: ${PRICE_OUT / 1000:.6f}")
    one = cost(2330, 200)
    print(f"one copilot question (2,330 in / 200 out): ${one:.5f}")
    print(f"1,000 questions:                            ${one * 1000:.2f}")
    print(f"same question with a 600-token answer:      ${cost(2330, 600):.5f}")