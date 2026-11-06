# src2/day1_streaming.py
"""
Day 1, Lesson 7: streaming. Compare time-to-first-token with total time.

Run from src2/:
    python day1_streaming.py
"""

import json
import time

import requests

from day1_first_call import API_KEY, MODEL, call_model, user

STREAM_URL = (f"https://generativelanguage.googleapis.com/v1beta/models/"
              f"{MODEL}:streamGenerateContent?alt=sse")

QUESTION = ("Explain how bank reconciliation works in an invoicing app, "
            "in about 150 words, for a new sales engineer.")


def stream(question):
    body = {"contents": [user(question)],
            "generationConfig": {"maxOutputTokens": 600}}
    start = time.perf_counter()
    first_token_at = None
    finish, usage, pieces = None, None, 0

    with requests.post(STREAM_URL, headers={"x-goog-api-key": API_KEY},
                       json=body, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue                      # skip blank lines between events
            chunk = json.loads(line[len("data: "):])
            pieces += 1
            cand = chunk["candidates"][0]
            for part in cand.get("content", {}).get("parts", []):
                text = part.get("text", "")
                if text:
                    if first_token_at is None:
                        first_token_at = time.perf_counter() - start
                    print(text, end="", flush=True)   # show it right away
            finish = cand.get("finishReason", finish)
            usage = chunk.get("usageMetadata", usage)

    total = time.perf_counter() - start
    return first_token_at, total, finish, usage, pieces


if __name__ == "__main__":
    print("===== WITHOUT streaming (you wait, then see everything) =====")
    start = time.perf_counter()
    data = call_model([user(QUESTION)], max_tokens=600)
    total = time.perf_counter() - start
    print("".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]))
    print(f"\n-> first text after {total:.2f}s | total {total:.2f}s")

    print("\n===== WITH streaming (text appears as it's written) =====")
    ttft, total, finish, usage, pieces = stream(QUESTION)
    print(f"\n\n-> first text after {ttft:.2f}s | total {total:.2f}s | "
          f"{pieces} pieces | finish: {finish}")
    print("   tokens:", usage)