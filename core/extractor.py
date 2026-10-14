"""
extractor.py — kisi bhi input (image / PDF / text file / voice) ko plain text mein badalta hai.
AI is text ko baad mein padhta hai.
"""
import io
from pathlib import Path

import config

log = config.get_logger("extractor")

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


class ExtractionError(Exception):
    """User ko dikhane layak (Hinglish) error message ke saath."""


def extract_text(data: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXT:
        text = _ocr_image(data)
    elif ext == ".pdf":
        text = _pdf_text(data)
    elif ext == ".txt":
        text = data.decode("utf-8", errors="ignore")
    else:
        raise ExtractionError(f"'{ext}' file type supported nahi hai.")
    text = text.strip()
    if not text:
        raise ExtractionError("File se koi text nahi mila. Saaf photo / doosri file try karo.")
    log.info("Extracted %s chars from %s", len(text), filename)
    return text


def _ocr_image(data: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise ExtractionError("pytesseract / Pillow install nahi hai: pip install pytesseract pillow") from exc

    if config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)          # phone photo ki rotation theek karo
    img = ImageOps.autocontrast(img.convert("L"))  # grayscale + contrast = better OCR
    if img.width < 1000:                        # chhoti image ko bada karo
        img = img.resize((img.width * 2, img.height * 2))
    try:
        return pytesseract.image_to_string(img, lang=config.OCR_LANG)
    except pytesseract.TesseractNotFoundError as exc:
        raise ExtractionError(
            "Tesseract software install nahi mila. Install karke .env mein TESSERACT_CMD set karo "
            "(README ka Setup section dekho)."
        ) from exc
    except pytesseract.TesseractError as exc:
        raise ExtractionError(f"OCR fail hua (language pack check karo: OCR_LANG={config.OCR_LANG}).") from exc


def _pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ExtractionError("pypdf install nahi hai: pip install pypdf") from exc
    reader = PdfReader(io.BytesIO(data))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    if len(text.strip()) < 30:
        raise ExtractionError(
            "Ye scanned PDF lagta hai (andar text nahi hai). Uska screenshot / photo (JPG/PNG) upload karo."
        )
    return text


def transcribe_audio(wav_bytes: bytes) -> str:
    """Voice (WAV) -> text. Google ki free web speech service use hoti hai (internet chahiye)."""
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise ExtractionError("Voice ke liye: pip install SpeechRecognition") from exc

    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio, language=config.VOICE_LANG)
    except sr.UnknownValueError as exc:
        raise ExtractionError("Awaaz samajh nahi aayi. Thoda saaf aur dheere bolke dobara try karo.") from exc
    except sr.RequestError as exc:
        raise ExtractionError(f"Speech service se connect nahi hua: {exc}") from exc
