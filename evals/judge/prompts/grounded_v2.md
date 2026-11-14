You are checking one answer from a documentation assistant for GROUNDEDNESS.

Question: is every factual claim in the ANSWER supported by the EVIDENCE blocks?

Rules:
- Use only the evidence blocks. Do not use your own knowledge. A claim that is true in the real world but not in the evidence is NOT supported.
- Ignore the [id] citation markers. Here you only check whether support exists anywhere in the evidence, not which block was cited.
- Sentences with no citation still count. Every factual claim must be supported.
- Wording can differ ("7 days" = "one week"). The meaning must match, including numbers, plan names, versions, and yes/no.
- A claim that adds a condition, plan, version, or promise the evidence does not state is NOT supported.
- Text that only restates the question, or says something is not covered, is not a factual claim.
- Repeating what the USER said (for example "your notes say 30 days") is not a claim to check; it comes from the question, not the evidence.
- Pointing out that the user's material disagrees with the evidence is allowed, as long as the value the answer gives as correct is supported.

Method (quote first, then decide):
1. Split the answer into its factual claims.
2. For each claim, copy the exact sentence or table row from the evidence that supports it. If none exists, write NONE.
3. Verdict: "pass" if every claim has a quote; "fail" if any claim is NONE.
