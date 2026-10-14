"""
config.py — poore project ki settings ek hi jagah.

Naya column chahiye?  Sirf neeche FIELDS list mein ek line add karo.
Prompt, UI table, validation aur Excel header — sab apne-aap update ho jayenge.
"""
import logging
import os
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------- Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"
LOG_DIR = BASE_DIR / "logs"

EXCEL_PATH = Path(os.getenv("EXCEL_PATH", DATA_DIR / "DataEntry.xlsx"))
SHEET_NAME = "Entries"
MAX_BACKUPS = 20  # isse purane backups apne-aap delete ho jate hain


# ---------------------------------------------------------------- Excel schema
@dataclass(frozen=True)
class Field:
    name: str          # Excel column ka header
    type: str          # "text" | "number" | "date"
    description: str   # AI ko batane ke liye — ye field kya hai
    required: bool = False


FIELDS = [
    Field("Name", "text", "Customer / party name", required=True),
    Field("Amount", "number",
          "Total bill amount as a plain number (no currency symbol, no commas)",
          required=True),
    Field("Date", "date", "Bill / transaction date"),
    Field("Invoice_No", "text", "Invoice, bill or receipt number, if present"),
    Field("Notes", "text", "Short extra detail (items, purpose, etc.), if present"),
]

DATE_FORMAT = "%d-%m-%Y"  # Excel mein date isi format mein dikhegi

# In fields ka combination same ho toh entry "duplicate" maani jayegi
DEDUPE_KEYS = ["Name", "Amount", "Date", "Invoice_No"]


# ---------------------------------------------------------------- LLM provider
# Teeno OpenAI-compatible API hain, isliye ek hi code se chalte hain.
# Model naam badalte rehte hain — .env mein LLM_MODEL likh kar override kar sakte ho.
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-120b",
        "key_env": "GROQ_API_KEY",
    },
    "openai": {
        "base_url": None,
        "model": "gpt-4o-mini",
        "key_env": "OPENAI_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash",
        "key_env": "GEMINI_API_KEY",
    },
}

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
if LLM_PROVIDER not in PROVIDERS:
    raise ValueError(
        f"LLM_PROVIDER '{LLM_PROVIDER}' galat hai. Options: {', '.join(PROVIDERS)}"
    )
PROVIDER = PROVIDERS[LLM_PROVIDER]
LLM_MODEL = os.getenv("LLM_MODEL", PROVIDER["model"])
MAX_INPUT_CHARS = 12000  # itna text hi AI ko bhejenge (cost + speed control)


# ---------------------------------------------------------------- OCR / Voice
TESSERACT_CMD = os.getenv("TESSERACT_CMD")   # Windows par path dena padta hai
OCR_LANG = os.getenv("OCR_LANG", "eng")      # Hindi bhi chahiye toh: eng+hin
VOICE_LANG = os.getenv("VOICE_LANG", "hi-IN")


# ---------------------------------------------------------------- Logging
def get_logger(name: str) -> logging.Logger:
    """Har module ke liye logger; logs/app.log mein save hota hai."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    LOG_DIR.mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=500_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
