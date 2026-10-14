"""
validator.py — AI ka output seedha Excel mein nahi jata.
Pehle yahan clean + check hota hai (amount number ho, date sahi format mein ho, zaroori field khali na ho).
"""
import hashlib
import re
from datetime import date, datetime

import config

_DATE_FORMATS = [
    "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d",
    "%d-%m-%y", "%d/%m/%y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
]


def parse_amount(value):
    """'Rs. 5,000/-' -> 5000.0 | '₹1,23,456.50' -> 123456.5 | galat input -> None"""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = str(value).replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return round(float(match.group()), 2) if match else None


def parse_date(value):
    """Kai formats samajhta hai; nahi samjha toh None."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def validate_record(raw: dict):
    """
    Ek raw record ko clean karta hai.
    Returns: (clean_record, issues)  — issues khali ho toh record save karne layak hai.
    """
    clean, issues = {}, []
    for field in config.FIELDS:
        value = raw.get(field.name)
        if isinstance(value, str):
            value = value.strip() or None
        had_issue = False

        if value is not None:
            if field.type == "number":
                number = parse_amount(value)
                if number is None:
                    issues.append(f"{field.name}: '{value}' number nahi hai")
                    had_issue = True
                value = number
            elif field.type == "date":
                parsed = parse_date(value)
                if parsed is None:
                    issues.append(f"{field.name}: '{value}' date samajh nahi aayi (DD-MM-YYYY likho)")
                    had_issue = True
                else:
                    value = parsed.strftime(config.DATE_FORMAT)
            else:
                value = str(value)

        if field.required and value is None and not had_issue:
            issues.append(f"{field.name}: zaroori field khali hai")
        clean[field.name] = value
    return clean, issues


def make_entry_id(clean: dict) -> str:
    """Duplicate pakadne ke liye fingerprint (DEDUPE_KEYS ke basis par)."""
    parts = [str(clean.get(key) if clean.get(key) is not None else "").strip().lower()
             for key in config.DEDUPE_KEYS]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
