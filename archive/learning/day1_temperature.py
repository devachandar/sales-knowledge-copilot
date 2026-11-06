# archive/learning/day1_temperature.py
"""
Day 1, Lesson 2: measure how much answers change at different temperatures.

Run from src2/:
    python day1_temperature.py
"""

import time

from day1_first_call import call_model, user

RUNS = 5   # how many times we ask the same question per setting

SYSTEM = "You are a concise assistant for sales engineers at an invoicing software company."

QUESTIONS = {
    # a factual question: we WANT the same answer every time
    "factual": "In one sentence, what is the difference between voiding and deleting an invoice?",
    # a creative question: variety is fine here
    "creative": "Write a one-sentence tagline for an invoicing app.",
}

# None = the model's default. We test it against the plan's advice (0) and two higher values.
SETTINGS = [None, 0, 1.0, 2.0]


def get_text(data):
    candidate = data["candidates"][0]
    text = "".join(p.get("text", "") for p in candidate["content"]["parts"])
    return text.strip(), candidate.get("finishReason")


for name, question in QUESTIONS.items():
    print(f"\n################ {name.upper()} ################")
    print(question)

    for temp in SETTINGS:
        label = "default" if temp is None else f"temp={temp}"
        answers, finishes = [], []

        for _ in range(RUNS):
            data = call_model([user(question)], system=SYSTEM, temperature=temp, max_tokens=200)
            text, finish = get_text(data)
            answers.append(text)
            finishes.append(finish)
            time.sleep(0.5)   # be gentle with the rate limit

        unique = len(set(answers))
        print(f"\n--- {label}: {unique}/{RUNS} different answers | finish reasons: {set(finishes)}")
        for i, a in enumerate(answers, 1):
            print(f"  {i}. {a[:120]}")