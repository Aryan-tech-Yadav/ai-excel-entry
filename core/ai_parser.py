"""
ai_parser.py — raw text ko LLM ke through structured records (list of dict) mein badalta hai.

LangChain ki jagah seedha `openai` SDK use kiya hai:
  * halka hai (8 GB RAM par bhi sasta), kam dependency-jhanjhat
  * Groq, OpenAI aur Gemini teeno isi SDK se chalte hain (config.py mein provider badlo, bas)
"""
import json
import os
import re
from datetime import date

import config

log = config.get_logger("ai_parser")


class AIParseError(Exception):
    """User ko dikhane layak error message ke saath."""


def has_api_key() -> bool:
    return bool(os.getenv(config.PROVIDER["key_env"]))


def _get_client():
    key = os.getenv(config.PROVIDER["key_env"])
    if not key:
        raise AIParseError(
            f".env file mein {config.PROVIDER['key_env']} nahi mila. "
            f"Provider '{config.LLM_PROVIDER}' ki API key wahan daalo."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIParseError("openai library install nahi hai: pip install openai") from exc
    return OpenAI(api_key=key, base_url=config.PROVIDER["base_url"], max_retries=3, timeout=60)


def build_system_prompt() -> str:
    """Prompt FIELDS se apne-aap banta hai — naya field add karo, prompt khud update."""
    field_lines = "\n".join(
        f'- "{f.name}" ({f.type}{", required" if f.required else ""}): {f.description}'
        for f in config.FIELDS
    )
    shape = ", ".join(f'"{f.name}": ...' for f in config.FIELDS)
    return f"""You are a precise data-entry assistant. The user gives raw text from an invoice, \
receipt, chat message or voice note. It may be in English, Hindi or Hinglish, and may contain OCR noise.

Extract every distinct entry in the text into JSON with these fields:
{field_lines}

Rules:
- Reply with ONLY a JSON object: {{"records": [{{{shape}}}, ...]}}
- One object per distinct bill/transaction. If the text has just one, return a list with one object.
- Use null for anything that is not clearly present. NEVER guess or invent values.
- Amount must be a plain number (e.g. 5000 or 1499.50). Dates as DD-MM-YYYY.
- Today's date is {date.today().strftime('%d-%m-%Y')}. Resolve words like "aaj"/"today" to it; leave null if a relative date is ambiguous.
- Keep names exactly as written (do not translate).
"""


def _extract_records(content: str) -> list:
    """LLM ke reply se records nikalta hai — code fences ya extra text ho toh bhi."""
    content = (content or "").strip()
    content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}|\[.*\]", content, flags=re.DOTALL)
        if not match:
            raise AIParseError("AI ka reply JSON nahi tha. Dobara try karo.")
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError as exc:
            raise AIParseError("AI ka reply padha nahi ja saka. Dobara try karo.") from exc

    if isinstance(data, dict):
        data = data.get("records", [data])
    if not isinstance(data, list):
        raise AIParseError("AI ka reply expected format mein nahi tha.")
    return [r for r in data if isinstance(r, dict)]


def parse_text(text: str) -> list:
    """Raw text -> list of raw record dicts (abhi validate nahi hue)."""
    text = (text or "").strip()
    if not text:
        return []
    text = text[: config.MAX_INPUT_CHARS]

    client = _get_client()
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": text},
    ]
    kwargs = dict(model=config.LLM_MODEL, messages=messages, temperature=0)

    try:
        try:
            response = client.chat.completions.create(**kwargs, response_format={"type": "json_object"})
        except Exception as exc:  # kuch models JSON mode support nahi karte
            if exc.__class__.__name__ != "BadRequestError":
                raise
            log.info("JSON mode unsupported, plain mode try kar raha hu")
            response = client.chat.completions.create(**kwargs)
    except AIParseError:
        raise
    except Exception as exc:
        log.exception("LLM call fail")
        raise AIParseError(f"AI service error ({exc.__class__.__name__}): {exc}") from exc

    records = _extract_records(response.choices[0].message.content)
    log.info("AI ne %s record nikale (%s / %s)", len(records), config.LLM_PROVIDER, config.LLM_MODEL)
    return records
