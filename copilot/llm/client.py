# copilot/llm/client.py
"""
Day 1, Lesson 1: one model call with raw HTTP. No SDK.

Run from the project root:
    python -m copilot.llm.client
"""

import json
import os

import requests
from dotenv import load_dotenv
import random
import re
import time

# from asyncio import tools

# Load GOOGLE_API_KEY from the .env file in the project root
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

MODEL = "gemini-3.5-flash-lite"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 5
BASE_WAIT = 1.0     # seconds
MAX_WAIT = 30.0


def server_retry_delay(resp):
    """If Google tells us how long to wait (e.g. retryDelay "30s"), use that."""
    try:
        for detail in resp.json()["error"].get("details", []):
            if "retryDelay" in detail:
                return float(re.sub(r"[^\d.]", "", detail["retryDelay"]))
    except (ValueError, KeyError):
        pass
    return None


def backoff_wait(attempt):
    """Exponential backoff with full jitter: random between 0 and 1, 2, 4, 8... seconds."""
    return random.uniform(0, min(MAX_WAIT, BASE_WAIT * 2 ** attempt))


def post_with_retry(url, headers, body, post=requests.post):
    """Send a request. Retry only errors that might fix themselves.

    `post` is a parameter so we can swap in a fake for testing.
    """
    for attempt in range(MAX_ATTEMPTS):
        last = attempt == MAX_ATTEMPTS - 1
        try:
            resp = post(url, headers=headers, json=body, timeout=60)
        except (requests.Timeout, requests.ConnectionError) as e:
            if last:
                raise
            wait = backoff_wait(attempt)
            print(f"  [retry {attempt + 1}] network error ({type(e).__name__}), waiting {wait:.1f}s")
            time.sleep(wait)
            continue

        if resp.status_code == 200:
            return resp

        if resp.status_code in RETRYABLE_STATUS and not last:
            wait = server_retry_delay(resp) or backoff_wait(attempt)
            wait = min(wait, MAX_WAIT)
            print(f"  [retry {attempt + 1}] HTTP {resp.status_code}, waiting {wait:.1f}s")
            time.sleep(wait)
            continue

        # Not retryable (400, 403, 404...) or out of attempts: fail loudly, right now
        print(f"HTTP {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
        

def call_model(contents, system=None, temperature=None, max_tokens=300,
            api_key=API_KEY, extra_config=None,tools=None):
    """Send one request and return the raw JSON response as a dict."""

    # 1. Build the request body. This is exactly what the SDK builds for you.
    gen_config = {"maxOutputTokens": max_tokens}
    
    
    body = {"contents": contents, "generationConfig": gen_config}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if tools:
        body["tools"] = tools 
        
    
    if temperature is not None:
        gen_config["temperature"] = temperature
    if extra_config:
        gen_config.update(extra_config) 
        
    
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    # 2. Send it. The key goes in a header, not in the URL,
    #    so it doesn't end up in logs that record URLs.
    # print("DEBUG body keys:", list(body.keys()))
    resp = requests.post(
        URL,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json=body,
        timeout=60,  # never wait forever on a network call
    )

    # 3. If it failed, show the status code and the error body, then stop.
    if resp.status_code != 200:
        print(f"HTTP {resp.status_code}")
        print(resp.text)
        resp.raise_for_status()

    return resp.json()


def show(data):
    """Pull out the three things you check on every response."""
    candidate = data["candidates"][0]
    text = "".join(p.get("text", "") for p in candidate["content"]["parts"])
    usage = data.get("usageMetadata", {})

    print("TEXT:         ", text)
    print("FINISH REASON:", candidate.get("finishReason"))
    print("TOKENS:        prompt =", usage.get("promptTokenCount"),
          "| output =", usage.get("candidatesTokenCount"),
          "| thinking =", usage.get("thoughtsTokenCount", 0),
          "| total =", usage.get("totalTokenCount"))
    return text


def user(text):
    return {"role": "user", "parts": [{"text": text}]}


def model(text):
    return {"role": "model", "parts": [{"text": text}]}


SYSTEM = "You are a concise assistant for sales engineers at an invoicing software company."
QUESTION = "What is bank reconciliation, in two sentences?"


if __name__ == "__main__":
    # --- The basic call ------------------------------------------------------
    print("\n===== BASIC CALL: full raw response =====")
    data = call_model([user(QUESTION)], system=SYSTEM)
    print(json.dumps(data, indent=2))      # look at the whole thing once
    print("\n----- the parts you care about -----")
    answer = show(data)

    # --- Experiment A: answer gets cut off -----------------------------------
    print("\n===== A: maxOutputTokens = 10 =====")
    show(call_model([user(QUESTION)], system=SYSTEM, max_tokens=10))

    # --- Experiment B: wrong API key -----------------------------------------
    print("\n===== B: wrong API key =====")
    try:
        call_model([user(QUESTION)], system=SYSTEM, api_key="not-a-real-key")
    except requests.HTTPError:
        print("(the call failed, as expected)")

    # --- Experiment C: the model has no memory -------------------------------
    follow_up = "Explain that more simply."

    print("\n===== C1: follow-up WITH the earlier turns =====")
    show(call_model([user(QUESTION), model(answer), user(follow_up)], system=SYSTEM))

    print("\n===== C2: same follow-up WITHOUT the earlier turns =====")
    show(call_model([user(follow_up)], system=SYSTEM))