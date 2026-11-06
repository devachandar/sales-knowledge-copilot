# copilot/config.py
"""
Every path and shared setting in one place.

Paths are built from where this file lives, so the code works no matter which
folder you run it from. Change a location here, and every script follows.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # the project root
PACKAGE_DIR = ROOT / "copilot"

# ---- data (generated corpus, processed files, results) ----
DATA_DIR = ROOT / "data" / "invoicepilot"
DATA_PACKAGE_DIR = DATA_DIR / "data_package"            # the CSVs for the SQL tables
CORPUS_DIR = DATA_DIR / "corpus"
HELP_CENTER_DIR = CORPUS_DIR / "help_center"
RELEASE_NOTES_DIR = CORPUS_DIR / "release_notes"
TICKETS_DIR = CORPUS_DIR / "support_tickets"
ENGINEERING_DIR = CORPUS_DIR / "engineering"
SALES_DIR = CORPUS_DIR / "sales"
ANSWER_KEY_DIR = DATA_DIR / "answer_key"                # NEVER ingest
PROCESSED_DIR = DATA_DIR / "processed"
DOCUMENTS_FILE = PROCESSED_DIR / "documents.jsonl"
RESULTS_DIR = DATA_DIR / "results"

# ---- code assets ----
PROMPTS_DIR = PACKAGE_DIR / "generation" / "prompts"
SCHEMA_SQL = PACKAGE_DIR / "db" / "schema.sql"

# ---- evaluation ----
QUESTIONS_DIR = ROOT / "evals" / "questions"


def chunks_file(strategy):
    """processed/chunks_<strategy>.jsonl"""
    return PROCESSED_DIR / f"chunks_{strategy}.jsonl"
