# archive/one_off/add_expected_docs.py
"""One-time fix (K2): expected_docs lists every page that states the answer."""

import json
from pathlib import Path

ADD = {
    "c1-01": ["release-notes/v2.2.0"],
    "c1-05": ["release-notes/v2.1.0"],
    "c2-03": ["reports/custom-report-builder"],
    "c2-06": ["release-notes/v2.3.1", "support/known-issues"],
    "c3-01": ["account-billing/plans-and-limits", "getting-started/invite-users"],
    "c3-02": ["account-billing/plans-and-limits"],
    "c3-03": ["account-billing/plans-and-limits"],
    "c3-05": ["account-billing/plans-and-limits", "support/faq"],
    "c4-01": ["release-notes/v2.3.0"],
    "c4-02": ["invoicing/bulk-invoice-actions", "release-notes/v2.2.0"],
    "c4-03": ["release-notes/v2.3.0", "support/glossary"],
    "c4-04": ["release-notes/v2.2.0"],
    "c4-05": ["release-notes/v2.1.0", "support/known-issues"],
}

path = Path("seed_questions.json")
seeds = json.loads(path.read_text(encoding="utf-8"))
for s in seeds:
    for d in ADD.get(s["id"], []):
        if d not in s["expected_docs"]:
            s["expected_docs"].append(d)
path.write_text(json.dumps(seeds, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("total expected docs:", sum(len(s["expected_docs"]) for s in seeds))