"""
app.py — Streamlit web interface.

Chalane ke liye:   streamlit run app.py

Flow:  Input (text / image / PDF / voice)  ->  raw text (edit kar sakte ho)
       ->  AI se fields  ->  REVIEW table (edit kar sakte ho)  ->  Excel mein save
"""
import pandas as pd
import streamlit as st

import config
from core import ai_parser, excel_store, extractor, validator

st.set_page_config(page_title="AI Excel Data Entry", page_icon="📊", layout="wide")

FIELD_NAMES = [f.name for f in config.FIELDS]
MODE_TEXT, MODE_FILE, MODE_VOICE = "✍️ Text paste", "🖼️ Image / PDF", "🎤 Voice"

# ---------------------------------------------------------------- session state
for key, default in {"raw_text": "", "draft": None, "draft_version": 0, "source": "text"}.items():
    st.session_state.setdefault(key, default)


def _blank(value):
    return value is None or (not isinstance(value, str) and pd.isna(value)) or value == ""


def review(df: pd.DataFrame):
    """Editor ki table ko validate karta hai. Returns (valid_records, problems, duplicate_rows)."""
    known_ids = excel_store.existing_ids()
    records, problems, duplicates, seen = [], [], [], set()

    for i, row in df.reset_index(drop=True).iterrows():
        raw = {name: (None if _blank(row.get(name)) else row.get(name)) for name in FIELD_NAMES}
        if all(v is None for v in raw.values()):
            continue  # poori khali row ignore
        clean, issues = validator.validate_record(raw)
        if issues:
            problems.extend(f"Row {i + 1} — {msg}" for msg in issues)
            continue
        entry_id = validator.make_entry_id(clean)
        if entry_id in known_ids or entry_id in seen:
            duplicates.append(i + 1)
        seen.add(entry_id)
        records.append(clean)
    return records, problems, duplicates


def save_draft(records: list):
    """Callback: button dabate hi chalta hai (isliye yahan widget state safely reset ho sakti hai)."""
    try:
        result = excel_store.append_records(records, source=st.session_state.source)
    except excel_store.ExcelLockedError as exc:
        st.session_state.flash = ("error", str(exc))
        return
    msg = f"✅ {result['added']} entry Excel mein save ho gayi."
    if result["duplicates"]:
        msg += f" ({result['duplicates']} duplicate skip hui)"
    st.session_state.flash = ("success", msg)
    st.session_state.draft = None
    st.session_state.raw_text = ""


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Status")
    st.write(f"**AI:** {config.LLM_PROVIDER} · `{config.LLM_MODEL}`")
    st.write(f"**Excel:** `{config.EXCEL_PATH.name}`")
    if not ai_parser.has_api_key():
        st.error(f".env mein {config.PROVIDER['key_env']} daalo.")
    summary = excel_store.stats()
    col1, col2 = st.columns(2)
    col1.metric("Entries", summary["count"])
    col2.metric(summary["total_label"], f"{summary['total']:,.2f}")
    if config.EXCEL_PATH.exists():
        st.download_button(
            "⬇️ Excel download karo",
            data=config.EXCEL_PATH.read_bytes(),
            file_name=config.EXCEL_PATH.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ---------------------------------------------------------------- main
st.title("📊 AI Excel Data Entry")
tab_new, tab_records = st.tabs(["➕ Nayi Entry", "📋 Records"])

with tab_new:
    flash = st.session_state.pop("flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])

    # ---- Step 1: input
    mode = st.radio("Data kaise doge?", [MODE_TEXT, MODE_FILE, MODE_VOICE], horizontal=True)

    if mode == MODE_TEXT:
        st.session_state.source = "text"
        st.caption("Neeche box mein text paste karo ya likho — jaise: "
                   "“Ramesh ne aaj 5000 rupaye diye, invoice INV-101”")

    elif mode == MODE_FILE:
        upload = st.file_uploader("Invoice / receipt upload karo",
                                  type=["png", "jpg", "jpeg", "webp", "pdf", "txt"])
        if upload and st.button("📖 Text padho"):
            try:
                with st.spinner("File padh raha hu..."):
                    st.session_state.raw_text = extractor.extract_text(upload.getvalue(), upload.name)
                st.session_state.source = f"file:{upload.name}"
            except extractor.ExtractionError as exc:
                st.error(str(exc))

    else:
        audio = st.audio_input("Mic dabao aur bolo (Hindi / English)")
        if audio and st.button("📝 Transcribe karo"):
            try:
                with st.spinner("Sun raha hu..."):
                    st.session_state.raw_text = extractor.transcribe_audio(audio.getvalue())
                st.session_state.source = "voice"
            except extractor.ExtractionError as exc:
                st.error(str(exc))

    # ---- Step 2: raw text (edit kar sakte ho) -> AI
    st.text_area("Raw text (OCR / voice ki galti ho toh yahin theek kar do)",
                 key="raw_text", height=180)

    if st.button("🤖 AI se fields nikalo", type="primary",
                 disabled=not st.session_state.raw_text.strip()):
        try:
            with st.spinner("AI soch raha hai..."):
                raw_records = ai_parser.parse_text(st.session_state.raw_text)
        except ai_parser.AIParseError as exc:
            st.error(str(exc))
        else:
            if not raw_records:
                st.warning("Text mein koi entry nahi mili.")
            else:
                rows = [validator.validate_record(r)[0] for r in raw_records]
                draft = pd.DataFrame(rows, columns=FIELD_NAMES)
                for f in config.FIELDS:
                    if f.type == "number":  # number column ka dtype sahi rahe, warna editor atak sakta hai
                        draft[f.name] = pd.to_numeric(draft[f.name], errors="coerce")
                st.session_state.draft = draft
                st.session_state.draft_version += 1

    # ---- Step 3: review + save
    if st.session_state.draft is not None:
        st.subheader("✅ Check karo, phir save karo")
        st.caption("Table mein kuch bhi seedha edit kar sakte ho; nayi row bhi jod sakte ho.")
        number_cols = {
            f.name: st.column_config.NumberColumn(f.name, format="%.2f")
            for f in config.FIELDS if f.type == "number"
        }
        edited = st.data_editor(
            st.session_state.draft,
            num_rows="dynamic",
            column_config=number_cols,
            key=f"editor_{st.session_state.draft_version}",
        )
        records, problems, duplicates = review(edited)

        for msg in problems:
            st.warning(msg)
        if duplicates:
            st.info(f"Row {', '.join(map(str, duplicates))} pehle se Excel mein hai — save par skip ho jayegi.")

        st.button(
            f"💾 Excel mein save karo ({len(records)})",
            type="primary",
            disabled=bool(problems) or not records,
            on_click=save_draft,
            args=(records,),
        )

with tab_records:
    df = excel_store.read_all()
    query = st.text_input("🔎 Search")
    if query:
        mask = df.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
        df = df[mask]
    st.dataframe(df.iloc[::-1])  # sabse nayi entry sabse upar
