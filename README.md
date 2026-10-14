# 📊 AI Excel Data Entry

Text, image, PDF ya voice se data padhkar apne-aap Excel (`.xlsx`) mein entry karne wala system.
**Python + Streamlit + Cloud LLM API + openpyxl** — 8 GB RAM / RTX 2050 laptop par bhi smoothly chalta hai, kyunki AI ka bhaari kaam cloud par hota hai.

---

## 1. Original plan se kya-kya smart banaya

| Pehle | Ab | Fayda |
|---|---|---|
| LangChain | Seedha `openai` SDK | Halka, kam dependency, 8 GB RAM friendly. Groq / OpenAI / Gemini teeno isi se chalte hain |
| AI ka output seedha Excel mein | **Review table** → tab save | AI galti kare toh Excel kharab nahi hota; save se pehle edit kar sakte ho |
| Columns code mein bikhre | `config.py` ka **FIELDS** | Naya column = 1 line. Prompt, table, validation, Excel header sab auto-update |
| Koi validation nahi | `validator.py` | `Rs. 5,000/-` → `5000`, kai date formats → `DD-MM-YYYY`, zaroori field khali ho toh save band |
| Duplicate ka dhyan nahi | Fingerprint (`Entry_ID`) | Same entry do baar nahi jayegi |
| Direct overwrite | Auto **backup** + temp-file se safe save | Crash / galti par purana data wapas mil jata hai |
| Excel khuli ho toh crash | Saaf error message | "Excel band karke dobara try karo" |
| Fixed provider | `.env` mein `LLM_PROVIDER` badlo | Code chhue bina Groq ↔ OpenAI ↔ Gemini |
| Kuch pata nahi kab kya hua | `logs/app.log` + unit tests | Debug aur future changes aasaan |

---

## 2. Tech stack

| Kaam | Tool |
|---|---|
| Editor / Language | VS Code · Python 3.11 ya 3.12 (3.10+ chalega) |
| UI | Streamlit |
| OCR (image → text) | Tesseract + `pytesseract` + Pillow |
| PDF text | `pypdf` |
| Voice (optional) | `SpeechRecognition` (Google free web speech) |
| AI | Groq / OpenAI / Gemini — `openai` SDK se |
| Excel | `openpyxl` (read/append/save) + `pandas` (records tab, stats) |
| Config | `python-dotenv` (.env mein API keys) |

---

## 3. Architecture

```
[ UI Layer ]  app.py  (Streamlit)
     │   Text paste  |  Image/PDF upload  |  Voice
     ▼
[ Extraction Layer ]  core/extractor.py
     │   OCR / PDF text / speech-to-text  →  raw text  (UI mein edit kar sakte ho)
     ▼
[ AI Layer ]  core/ai_parser.py
     │   Prompt (FIELDS se auto-bana) → LLM → JSON  {"records": [...]}
     ▼
[ Validation Layer ]  core/validator.py
     │   Amount/Date clean · required check · duplicate fingerprint
     ▼
[ Review ]  UI table — user check/edit karta hai
     ▼
[ Storage Layer ]  core/excel_store.py
     │   backup → duplicate skip → row append → safe save
     ▼
[ Output ]  data/DataEntry.xlsx   +   "✅ Save ho gayi" message
```

### Folder structure

```
ai-excel-entry/
├── app.py                 # Streamlit UI
├── config.py              # FIELDS, paths, provider — sab settings yahin
├── core/
│   ├── extractor.py       # OCR / PDF / voice → text
│   ├── ai_parser.py       # text → structured records (LLM)
│   ├── validator.py       # cleaning + checks + duplicate ID
│   └── excel_store.py     # Excel read/append/backup
├── tests/test_core.py     # bina internet ke chalne wale tests
├── requirements.txt
├── .env.example           # copy karke .env banao
├── data/                  # DataEntry.xlsx yahin banegi (auto)
├── backups/               # auto backups (auto)
└── logs/app.log           # errors/info (auto)
```

---

## 4. Setup (Windows + VS Code)

1. **Python 3.11 / 3.12** install karo (installer mein “Add to PATH” tick karo).
   > 3.13 par `SpeechRecognition` (voice) mein dikkat aa sakti hai; sirf text/image chalana ho toh koi problem nahi.
2. **Project VS Code mein kholo** → Terminal:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
   (PowerShell script-error de toh Terminal ko *Command Prompt* par switch karo.)
3. **Tesseract OCR install karo** (sirf image ke liye): Windows installer “UB Mannheim Tesseract” search karke install karo. Installer mein *Additional language data → Hindi* tick karo agar Hindi bills padhne hain.
4. **`.env` banao:** `.env.example` ko copy karke `.env` naam do, phir:
   ```
   LLM_PROVIDER=groq
   GROQ_API_KEY=apni_key_yahan
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```
   API key: Groq ke console se free banti hai (free tier mein rate limits hoti hain).
5. **Chalao:**
   ```
   streamlit run app.py
   ```
   Browser apne-aap khulega.

### Pehle step-by-step test (recommended roadmap)

```
python -m core.excel_store                 # 1) bina AI ke Excel mein dummy entry
python -m unittest discover -s tests -v    # 2) saare core tests
streamlit run app.py                       # 3) poora app
```

---

## 5. Roz ka use

1. **Nayi Entry** tab → input chuno (text / image-PDF / voice).
2. **🤖 AI se fields nikalo** dabao → table aayegi.
3. Galti ho toh table mein seedha edit karo → **💾 Excel mein save karo**.

**📋 Records** tab mein search karo; sidebar se Excel download karo. Save se pehle Excel file **band** rakho.

---

## 6. Naya column kaise jodein

`config.py` mein `FIELDS` ke andar ek line:

```python
Field("City", "text", "City name of the customer"),
```

Bas. Prompt, review table, validation aur Excel — sab update. Purani Excel file mein bhi naya column end mein apne-aap jud jayega.
Type options: `"text"`, `"number"`, `"date"`. Zaroori banana ho toh `required=True`.

Duplicate ka rule badalna ho toh `DEDUPE_KEYS` edit karo.

## 7. AI provider / model badalna

`.env` mein `LLM_PROVIDER=openai` (ya `gemini`) + us provider ki key. Model naam time ke saath badalte hain — provider ke docs se dekhkar `.env` mein `LLM_MODEL=...` likh do.

---

## 8. Troubleshooting

| Problem | Solution |
|---|---|
| `.env mein ..._API_KEY nahi mila` | `.env` project folder mein hai? Key bhari hai? App restart karo |
| `Tesseract software install nahi mila` | Tesseract install karo + `.env` mein `TESSERACT_CMD` path do |
| Hindi text sahi nahi padh raha | Tesseract mein Hindi pack install karo, `.env` mein `OCR_LANG=eng+hin` |
| “Excel mein khuli hai” | Excel file band karo, phir Save dabao |
| “Ye scanned PDF lagta hai” | PDF ka screenshot / photo (JPG/PNG) upload karo |
| Voice mein error | `pip install SpeechRecognition`, internet on rakho, Python 3.11/3.12 use karo |
| AI galat field nikaal raha | Raw text box mein text saaf karo, ya `config.py` mein field ka `description` behtar likho |

---

## 9. Dhyan rakhne wali baatein

- **Privacy:** Cloud API use hone se invoice ka text us provider ko jata hai (aur voice Google ko). Bahut sensitive data ho toh pehle provider ki data policy dekh lo.
- **Existing Excel:** `openpyxl` se save karne par purani file ke charts / pivot tables / macros ud sakte hain. Sirf data wali sheet ho toh koi dikkat nahi; warna pehle ek copy rakho (backup auto banta hai).
- **Accuracy:** AI kabhi-kabhi galat padh sakta hai — isiliye review step rakha hai. Use skip mat karna.
- **`Entry_ID` / `Source` / `Added_On`** columns system ke hain; delete mat karna (duplicate check inhi par chalta hai).

## 10. Aage ke upgrades (jab zaroorat ho)

- Vision-capable LLM se image seedha padhwana (OCR step hat jayega, scanned PDF bhi chalegi)
- Folder-watch: koi bill folder mein daalo, apne-aap entry
- Google Sheets / SQLite backend
- Login + multiple users
