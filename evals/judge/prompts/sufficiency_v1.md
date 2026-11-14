You are checking a RETRIEVAL step, not an answer. A search system returned some CHUNKS for a QUESTION. A human wrote the GOLDEN ANSWER.

Question: do these chunks contain enough information to write the golden answer?

Rules:
- Judge only the chunks. Do not use your own knowledge.
- The same fact can be written in different places and words ("300 (Professional)" in one chunk = "| Professional | 300 |" in a table). Any chunk that states the fact counts.
- Every fact in MUST_INCLUDE, and every part of the question that the golden answer covers, must be stated in at least one chunk. Facts may come from different chunks.
- Extra golden detail that does not answer the question (background, nice-to-know) is not required.
- For a conflict question, both sides of the disagreement must be in the chunks.
- For a question that contains injected or false text, only the true answer must be in the chunks.

Method (quote first, then decide):
1. List the facts needed to write the golden answer.
2. For each fact, give the chunk id and copy the exact text that states it. If no chunk states it, write NONE for both.
3. Verdict: "pass" if every needed fact has a quote; "fail" if any is NONE.
