# archive/learning/day1_retry_test.py
"""
Day 1, Lesson 6: test the retry logic with fake failures, no real API calls.

Run from src2/:
    python day1_retry_test.py
"""

import requests

import day1_first_call as api

api.BASE_WAIT = 0.2   # speed up the test; real waits are longer


class FakeResponse:
    def __init__(self, status, body=None):
        self.status_code = status
        self._body = body or {"error": {"code": status, "message": "fake", "details": []}}
        self.text = str(self._body)

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def fake_server(script):
    """Returns a fake `post` that replies with each item in `script` in order."""
    replies = iter(script)
    calls = {"n": 0}

    def post(url, headers, json, timeout):
        calls["n"] += 1
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return reply

    return post, calls


def run(name, script):
    print(f"\n===== {name} =====")
    post, calls = fake_server(script)
    try:
        api.post_with_retry("fake-url", {}, {}, post=post)
        print(f"-> SUCCEEDED after {calls['n']} attempt(s)")
    except Exception as e:
        print(f"-> FAILED after {calls['n']} attempt(s): {type(e).__name__}")


OK = FakeResponse(200, {"ok": True})

run("A. two 503s, then success", [FakeResponse(503), FakeResponse(503), OK])
run("B. a timeout, then success", [requests.Timeout(), OK])
run("C. bad API key (400)", [FakeResponse(400), OK])
run("D. server says wait 1s", [FakeResponse(429, {"error": {"code": 429, "details": [
    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "1s"}]}}), OK])
run("E. 429 forever", [FakeResponse(429)] * 10)