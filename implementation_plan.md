> **Superseded.** This early sketch predates the actual build and diverged from it (endpoints, module names, and the TTS provider all changed). What was actually built is documented in [`docs/superpowers/plans/2026-07-30-vlearn-ai-study-agent.md`](docs/superpowers/plans/2026-07-30-vlearn-ai-study-agent.md) — read that instead. This file is kept for historical reference only.

# VLearn AI Study Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working prototype AI Agent tích hợp vào giao diện VLearn (HTML đã có), có thể: (1) tóm tắt PDF thành text ngắn, (2) sinh sơ đồ tư duy mind map, (3) chuyển thành audio podcast — sử dụng OpenAI API thật.

**Architecture:** Python FastAPI backend cung cấp 3 API endpoints (summarize, mindmap, audio). Frontend là file `vlearn_clone.html` hiện có, được nâng cấp thêm 3 tab output (Summary / Mind Map / Audio) trong sidebar chatbot. Backend trích xuất text từ PDF bằng `pymupdf`, gọi OpenAI GPT cho summarize/mindmap, gọi OpenAI TTS cho audio.

**Tech Stack:** Python 3.10+ · FastAPI · pymupdf (fitz) · openai Python SDK · markmap (CDN, frontend) · HTML/CSS/JS vanilla

## User Review Required

> [!IMPORTANT]
> **OpenAI API Key:** Bạn cần có API key từ OpenAI. Backend sẽ đọc từ biến môi trường `OPENAI_API_KEY`. Bạn đã có key chưa?

> [!IMPORTANT]
> **Scope giới hạn:** Plan này build **prototype demo** gói gọn trong project hiện tại — KHÔNG deploy, KHÔNG database, KHÔNG authentication. Chỉ cần chạy `python server.py` + mở `vlearn_clone.html` là demo được.

> [!WARNING]
> **File PDF:** Plan sử dụng file `HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf` (5.6MB) đã có trong project. Đây là PDF slide nên pymupdf trích text được tốt. Nếu PDF là scan (ảnh), sẽ cần OCR — nhưng file này không phải scan.

## Open Questions

> [!IMPORTANT]
> 1. **OpenAI model nào?** Plan mặc định dùng `gpt-4o-mini` cho summarize/mindmap (rẻ, nhanh) và `tts-1` cho audio. Bạn muốn dùng model khác không?
> 2. **Giọng TTS:** OpenAI TTS hỗ trợ 6 giọng (alloy, echo, fable, onyx, nova, shimmer). Plan mặc định dùng `nova` (giọng nữ, tự nhiên). Bạn có preference?
> 3. **Ngôn ngữ output:** Summary/mindmap bằng tiếng Việt hay tiếng Anh? Plan mặc định tiếng Việt (vì user là học viên VN).

## Proposed Changes

### Component 1: Backend — PDF Parser + AI Agent

Tạo folder `codebase/` chứa toàn bộ backend Python.

---

#### [NEW] [requirements.txt](file:///c:/Users/Hung%20Tran/OneDrive%20-%20Hanoi%20University%20of%20Science%20and%20Technology/Desktop/AI%20In%20Action/LABS/K4-hackathon-I-m-back-E402/codebase/requirements.txt)

Dependencies cho backend: `fastapi`, `uvicorn`, `pymupdf`, `openai`, `python-dotenv`

---

#### [NEW] [server.py](file:///c:/Users/Hung%20Tran/OneDrive%20-%20Hanoi%20University%20of%20Science%20and%20Technology/Desktop/AI%20In%20Action/LABS/K4-hackathon-I-m-back-E402/codebase/server.py)

FastAPI server chính với 4 endpoints:
- `POST /api/extract-text` — trích xuất toàn bộ text từ PDF, trả về per-page
- `POST /api/summarize` — nhận text → gọi OpenAI → trả summary
- `POST /api/mindmap` — nhận text → gọi OpenAI → trả Markdown outline (cho markmap)
- `POST /api/audio` — nhận text → gọi OpenAI TTS → trả file MP3

Có CORS middleware để frontend HTML gọi được.

---

#### [NEW] [pdf_parser.py](file:///c:/Users/Hung%20Tran/OneDrive%20-%20Hanoi%20University%20of%20Science%20and%20Technology/Desktop/AI%20In%20Action/LABS/K4-hackathon-I-m-back-E402/codebase/pdf_parser.py)

Module trích xuất text từ PDF bằng pymupdf:
- `extract_all_text(pdf_path) -> str` — toàn bộ text
- `extract_text_by_page(pdf_path) -> list[dict]` — text từng trang kèm page number
- `get_page_count(pdf_path) -> int`

---

#### [NEW] [ai_agent.py](file:///c:/Users/Hung%20Tran/OneDrive%20-%20Hanoi%20University%20of%20Science%20and%20Technology/Desktop/AI%20In%20Action/LABS/K4-hackathon-I-m-back-E402/codebase/ai_agent.py)

Module gọi OpenAI API với 3 tools:
- `summarize(text, style="concise") -> str` — tóm tắt, hỗ trợ style: concise/detailed/bullet
- `to_mindmap(text) -> str` — trả Markdown heading outline cho markmap render
- `to_audio_script(text) -> str` — viết lại text dạng podcast script tự nhiên

---

#### [NEW] [tts_engine.py](file:///c:/Users/Hung%20Tran/OneDrive%20-%20Hanoi%20University%20of%20Science%20and%20Technology/Desktop/AI%20In%20Action/LABS/K4-hackathon-I-m-back-E402/codebase/tts_engine.py)

Module gọi OpenAI TTS:
- `generate_audio(text, voice="nova", output_path="output.mp3") -> str` — trả đường dẫn file MP3

---

#### [NEW] [.env.example](file:///c:/Users/Hung%20Tran/OneDrive%20-%20Hanoi%20University%20of%20Science%20and%20Technology/Desktop/AI%20In%20Action/LABS/K4-hackathon-I-m-back-E402/codebase/.env.example)

Template cho environment variables: `OPENAI_API_KEY=sk-your-key-here`

---

### Component 2: Frontend — Nâng cấp VLearn Clone HTML

---

#### [MODIFY] [vlearn_clone.html](file:///c:/Users/Hung%20Tran/OneDrive%20-%20Hanoi%20University%20of%20Science%20and%20Technology/Desktop/AI%20In%20Action/LABS/K4-hackathon-I-m-back-E402/vlearn_clone.html)

Thay đổi lớn:
1. **Thêm 3 nút action** trong chatbot sidebar: 📝 Tóm tắt / 🧠 Mind Map / 🎧 Audio
2. **Thêm panel kết quả** bên dưới chat messages — có tab switch giữa Summary / Mind Map / Audio
3. **Tích hợp markmap** (CDN) để render mind map từ Markdown
4. **Audio player** HTML5 native
5. **Kết nối API thật** thay vì replies mock — gọi FastAPI backend qua `fetch()`
6. **Loading states** với skeleton animation khi đang gọi AI
7. **Chat thật** — gửi câu hỏi đến `/api/chat` endpoint, AI trả lời dựa trên context PDF

---

### File Structure tổng thể sau khi build

```
K4-hackathon-I-m-back-E402/
├── vlearn_clone.html          ← frontend (mở bằng browser)
├── HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf  ← PDF demo
├── codebase/
│   ├── requirements.txt
│   ├── server.py              ← chạy: uvicorn server:app --reload
│   ├── pdf_parser.py
│   ├── ai_agent.py
│   ├── tts_engine.py
│   ├── .env.example
│   └── audio_output/          ← thư mục chứa file MP3 sinh ra
├── data/                      ← data pack (không sửa)
├── 01-de-bai.md ... 04-rubric.md  ← docs hackathon
└── README.md
```

---

## Verification Plan

### Automated Tests

```bash
# 1. Test PDF parser
cd codebase
python -c "from pdf_parser import extract_all_text; print(extract_all_text('../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf')[:200])"

# 2. Test AI agent
python -c "from ai_agent import summarize; print(summarize('HCI is the study of how people interact with computers.'))"

# 3. Test server starts
uvicorn server:app --host 0.0.0.0 --port 8000 &
curl http://localhost:8000/health
```

### Manual Verification

1. Mở `vlearn_clone.html` trong browser
2. Bấm nút "📝 Tóm tắt" → chờ → xem summary hiện ra trong panel
3. Bấm nút "🧠 Mind Map" → chờ → xem markmap render interactive
4. Bấm nút "🎧 Audio" → chờ → bấm play nghe audio
5. Gõ câu hỏi trong chat → nhận câu trả lời từ AI dựa trên nội dung PDF

---

## Detailed Task Breakdown

### Task 1: PDF Parser Module

**Files:**
- Create: `codebase/pdf_parser.py`
- Create: `codebase/requirements.txt`

**Interfaces:**
- Consumes: PDF file path (string)
- Produces: `extract_all_text(pdf_path: str) -> str`, `extract_text_by_page(pdf_path: str) -> list[dict]`, `get_page_count(pdf_path: str) -> int`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
pymupdf==1.24.0
openai==1.40.0
python-dotenv==1.0.1
python-multipart==0.0.9
```

- [ ] **Step 2: Create pdf_parser.py with extract functions**

```python
import fitz  # pymupdf

def extract_all_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text_parts = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            text_parts.append(f"--- Trang {page_num + 1} ---\n{text.strip()}")
    doc.close()
    return "\n\n".join(text_parts)

def extract_text_by_page(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        pages.append({
            "page": page_num + 1,
            "text": text.strip()
        })
    doc.close()
    return pages

def get_page_count(pdf_path: str) -> int:
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count
```

- [ ] **Step 3: Install dependencies and test parser**

```bash
cd codebase
pip install -r requirements.txt
python -c "from pdf_parser import extract_all_text, get_page_count; t = extract_all_text('../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf'); print(f'Pages: {get_page_count(\"../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf\")}, Text length: {len(t)} chars'); print(t[:300])"
```

Expected: Prints page count and first 300 chars of extracted text successfully.

- [ ] **Step 4: Commit**

```bash
git add codebase/requirements.txt codebase/pdf_parser.py
git commit -m "feat: add PDF text extraction module using pymupdf"
```

---

### Task 2: AI Agent Module (OpenAI)

**Files:**
- Create: `codebase/ai_agent.py`
- Create: `codebase/.env.example`

**Interfaces:**
- Consumes: Text string from pdf_parser
- Produces: `summarize(text: str, style: str = "concise") -> str`, `to_mindmap(text: str) -> str`, `to_audio_script(text: str) -> str`, `chat_with_context(question: str, context: str) -> str`

- [ ] **Step 1: Create .env.example**

```
OPENAI_API_KEY=sk-your-key-here
```

- [ ] **Step 2: Create .env with actual key (user provides)**

User tạo file `codebase/.env` với API key thật. File này KHÔNG commit (thêm vào .gitignore).

- [ ] **Step 3: Create ai_agent.py**

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

def summarize(text: str, style: str = "concise") -> str:
    style_prompts = {
        "concise": "Tóm tắt ngắn gọn trong 3-5 câu, giữ ý chính.",
        "detailed": "Tóm tắt chi tiết, giữ đầy đủ các ý quan trọng, chia thành các đoạn.",
        "bullet": "Tóm tắt dạng bullet points, mỗi ý chính một dòng."
    }
    prompt = style_prompts.get(style, style_prompts["concise"])

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": f"Bạn là trợ lý học tập. {prompt} Trả lời bằng tiếng Việt."},
            {"role": "user", "content": f"Tóm tắt nội dung tài liệu sau:\n\n{text}"}
        ],
        temperature=0.3,
        max_tokens=2000
    )
    return response.choices[0].message.content

def to_mindmap(text: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": """Bạn là trợ lý tạo sơ đồ tư duy. Chuyển nội dung thành cấu trúc Markdown heading.
Quy tắc:
- Dùng # cho chủ đề chính
- Dùng ## cho nhánh lớn
- Dùng ### cho nhánh con
- Dùng #### cho chi tiết
- Mỗi nhánh là một ý ngắn gọn (tối đa 10 từ)
- Tối đa 4 cấp depth
- Trả lời bằng tiếng Việt
Chỉ trả về Markdown, không giải thích thêm."""},
            {"role": "user", "content": f"Tạo sơ đồ tư duy cho nội dung sau:\n\n{text}"}
        ],
        temperature=0.3,
        max_tokens=2000
    )
    return response.choices[0].message.content

def to_audio_script(text: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": """Bạn là người viết script podcast giáo dục. Viết lại nội dung dưới dạng script podcast tự nhiên, hấp dẫn.
Quy tắc:
- Giọng kể chuyện thân thiện, dễ hiểu
- Mở đầu bằng lời chào ngắn
- Giải thích các khái niệm bằng ví dụ đời thường
- Kết thúc bằng tóm tắt key takeaways
- Độ dài vừa phải (300-500 từ)
- Trả lời bằng tiếng Việt"""},
            {"role": "user", "content": f"Viết podcast script cho nội dung:\n\n{text}"}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    return response.choices[0].message.content

def chat_with_context(question: str, context: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": f"""Bạn là VLearn Tutor — trợ lý học tập thông minh. Trả lời câu hỏi dựa trên nội dung tài liệu được cung cấp.
Quy tắc:
- Chỉ trả lời dựa trên nội dung tài liệu. Nếu không tìm thấy thông tin, nói rõ.
- Trích dẫn trang slide khi có thể: [Trang N]
- Giọng thân thiện, dễ hiểu
- Trả lời bằng tiếng Việt
- Ngắn gọn, đúng trọng tâm

Nội dung tài liệu:
{context[:8000]}"""},
            {"role": "user", "content": question}
        ],
        temperature=0.4,
        max_tokens=1000
    )
    return response.choices[0].message.content
```

- [ ] **Step 4: Test ai_agent.py**

```bash
cd codebase
python -c "
from pdf_parser import extract_all_text
from ai_agent import summarize
text = extract_all_text('../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf')
print(summarize(text[:3000], 'bullet'))
"
```

Expected: Prints bullet-point summary of the PDF content in Vietnamese.

- [ ] **Step 5: Commit**

```bash
git add codebase/ai_agent.py codebase/.env.example
git commit -m "feat: add OpenAI-powered AI agent with summarize, mindmap, audio tools"
```

---

### Task 3: TTS Engine Module

**Files:**
- Create: `codebase/tts_engine.py`
- Create: `codebase/audio_output/` (directory)

**Interfaces:**
- Consumes: Text string (podcast script from ai_agent.to_audio_script)
- Produces: `generate_audio(text: str, voice: str = "nova", output_dir: str = "audio_output") -> str` — returns file path

- [ ] **Step 1: Create audio_output directory**

```bash
mkdir -p codebase/audio_output
```

- [ ] **Step 2: Create tts_engine.py**

```python
import os
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_audio(text: str, voice: str = "nova", output_dir: str = "audio_output") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filename = f"podcast_{int(time.time())}.mp3"
    output_path = os.path.join(output_dir, filename)

    # OpenAI TTS has a 4096 char limit per request
    # Split into chunks if needed
    chunks = _split_text(text, max_chars=4000)

    if len(chunks) == 1:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=chunks[0]
        )
        response.stream_to_file(output_path)
    else:
        # For multiple chunks, generate separately and note in filename
        # For prototype, just use first chunk
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=chunks[0]
        )
        response.stream_to_file(output_path)

    return filename

def _split_text(text: str, max_chars: int = 4000) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    sentences = text.replace("。", ".").split(".")
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current += sentence + "."
        else:
            if current:
                chunks.append(current.strip())
            current = sentence + "."
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text[:max_chars]]
```

- [ ] **Step 3: Test TTS engine**

```bash
cd codebase
python -c "
from tts_engine import generate_audio
path = generate_audio('Xin chào! Đây là bài test text-to-speech từ OpenAI.')
print(f'Audio saved to: {path}')
"
```

Expected: Creates MP3 file in `audio_output/` directory.

- [ ] **Step 4: Commit**

```bash
git add codebase/tts_engine.py
git commit -m "feat: add OpenAI TTS engine for audio generation"
```

---

### Task 4: FastAPI Server

**Files:**
- Create: `codebase/server.py`

**Interfaces:**
- Consumes: pdf_parser, ai_agent, tts_engine modules
- Produces: REST API at `http://localhost:8000` with endpoints:
  - `GET /health` → `{"status": "ok"}`
  - `POST /api/extract-text` body `{pdf_path}` → `{text, pages, page_count}`
  - `POST /api/summarize` body `{text, style}` → `{summary}`
  - `POST /api/mindmap` body `{text}` → `{markdown}`
  - `POST /api/audio` body `{text, voice}` → `{filename, url}`
  - `POST /api/chat` body `{question, context}` → `{answer}`
  - `GET /audio/{filename}` → serves MP3 file

- [ ] **Step 1: Create server.py**

```python
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from pdf_parser import extract_all_text, extract_text_by_page, get_page_count
from ai_agent import summarize, to_mindmap, to_audio_script, chat_with_context
from tts_engine import generate_audio

app = FastAPI(title="VLearn AI Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class ExtractRequest(BaseModel):
    pdf_path: str

class SummarizeRequest(BaseModel):
    text: str
    style: Optional[str] = "concise"

class MindmapRequest(BaseModel):
    text: str

class AudioRequest(BaseModel):
    text: str
    voice: Optional[str] = "nova"

class ChatRequest(BaseModel):
    question: str
    context: str

# --- Cache for extracted text ---
_text_cache: dict = {}

# --- Endpoints ---
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/extract-text")
def extract_text(req: ExtractRequest):
    if not os.path.exists(req.pdf_path):
        raise HTTPException(404, f"PDF not found: {req.pdf_path}")
    try:
        all_text = extract_all_text(req.pdf_path)
        pages = extract_text_by_page(req.pdf_path)
        count = get_page_count(req.pdf_path)
        _text_cache["last"] = all_text
        return {"text": all_text, "pages": pages, "page_count": count}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/summarize")
def api_summarize(req: SummarizeRequest):
    try:
        result = summarize(req.text, req.style)
        return {"summary": result}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/mindmap")
def api_mindmap(req: MindmapRequest):
    try:
        result = to_mindmap(req.text)
        return {"markdown": result}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/audio")
def api_audio(req: AudioRequest):
    try:
        script = to_audio_script(req.text)
        filename = generate_audio(script, req.voice)
        return {"filename": filename, "url": f"/audio/{filename}", "script": script}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        answer = chat_with_context(req.question, req.context)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/audio/{filename}")
def serve_audio(filename: str):
    path = os.path.join("audio_output", filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Audio file not found")
    return FileResponse(path, media_type="audio/mpeg", filename=filename)
```

- [ ] **Step 2: Test server starts and health check works**

```bash
cd codebase
uvicorn server:app --host 0.0.0.0 --port 8000 &
sleep 2
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 3: Test extract-text endpoint**

```bash
curl -X POST http://localhost:8000/api/extract-text \
  -H "Content-Type: application/json" \
  -d '{"pdf_path": "../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf"}'
```

Expected: JSON with `text`, `pages` array, and `page_count`.

- [ ] **Step 4: Commit**

```bash
git add codebase/server.py
git commit -m "feat: add FastAPI server with all AI agent endpoints"
```

---

### Task 5: Frontend — Nâng cấp VLearn HTML

**Files:**
- Modify: `vlearn_clone.html`

**Interfaces:**
- Consumes: All API endpoints from server.py at `http://localhost:8000`
- Produces: Working UI with 3 AI features + real chat

- [ ] **Step 1: Thêm CSS cho 3 tab output và action buttons**

Thêm styles cho:
- `.action-buttons` — row 3 nút (Tóm tắt / Mind Map / Audio)
- `.output-panel` — container hiển thị kết quả
- `.tab-bar` — tab switch Summary / Mind Map / Audio
- `.loading-skeleton` — skeleton animation khi chờ AI
- `.audio-player` — styled HTML5 audio player
- `.mindmap-container` — container cho markmap

- [ ] **Step 2: Thêm markmap CDN trong `<head>`**

```html
<script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@latest"></script>
```

- [ ] **Step 3: Thêm action buttons vào chatbot sidebar**

3 nút nằm giữa context-bar và chat-messages:
```html
<div class="action-buttons">
  <button onclick="doSummarize()" id="btn-summarize">📝 Tóm tắt</button>
  <button onclick="doMindmap()" id="btn-mindmap">🧠 Mind Map</button>
  <button onclick="doAudio()" id="btn-audio">🎧 Audio</button>
</div>
```

- [ ] **Step 4: Thêm output panel với tab system**

Panel hiển thị kết quả, có thể toggle hiện/ẩn:
```html
<div class="output-panel" id="outputPanel" style="display:none">
  <div class="tab-bar">
    <button class="tab active" data-tab="summary">📝 Tóm tắt</button>
    <button class="tab" data-tab="mindmap">🧠 Mind Map</button>
    <button class="tab" data-tab="audio">🎧 Audio</button>
  </div>
  <div class="tab-content" id="tab-summary"><!-- summary text --></div>
  <div class="tab-content" id="tab-mindmap" style="display:none">
    <div id="mindmap-container"></div>
  </div>
  <div class="tab-content" id="tab-audio" style="display:none">
    <audio controls id="audioPlayer"></audio>
    <div id="audioScript"></div>
  </div>
</div>
```

- [ ] **Step 5: Viết JavaScript kết nối API thật**

Thay thế mock `sendMessage()` bằng `fetch()` gọi `/api/chat`.
Thêm hàm `doSummarize()`, `doMindmap()`, `doAudio()` gọi API tương ứng.
Khi page load, tự động gọi `/api/extract-text` để cache text PDF.

```javascript
const API_BASE = 'http://localhost:8000';
let pdfText = '';

async function loadPdfText() {
  const res = await fetch(`${API_BASE}/api/extract-text`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pdf_path: '../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf'})
  });
  const data = await res.json();
  pdfText = data.text;
}

async function doSummarize() {
  showLoading('summary');
  const res = await fetch(`${API_BASE}/api/summarize`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text: pdfText, style: 'bullet'})
  });
  const data = await res.json();
  document.getElementById('tab-summary').innerHTML = marked(data.summary);
  showTab('summary');
}

// Similar for doMindmap(), doAudio()

async function sendMessage() {
  // ... get user input
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: txt, context: pdfText})
  });
  const data = await res.json();
  // ... render data.answer as bot message
}

window.addEventListener('load', loadPdfText);
```

- [ ] **Step 6: Thêm Markdown rendering cho summary**

Include `marked.js` CDN để render markdown output từ AI:
```html
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
```

- [ ] **Step 7: Test toàn bộ flow end-to-end**

1. Start server: `cd codebase && uvicorn server:app --reload --port 8000`
2. Mở `vlearn_clone.html` trong browser
3. Test 3 nút: Tóm tắt → Mind Map → Audio
4. Test chat với câu hỏi: "HCI là gì?"

- [ ] **Step 8: Commit**

```bash
git add vlearn_clone.html
git commit -m "feat: upgrade VLearn UI with AI summarize, mindmap, audio features"
```

---

### Task 6: Polish & Documentation

**Files:**
- Modify: `README.md` (thêm hướng dẫn chạy)
- Create: `codebase/.gitignore`

- [ ] **Step 1: Create codebase/.gitignore**

```
.env
__pycache__/
audio_output/*.mp3
```

- [ ] **Step 2: Update README với hướng dẫn demo**

Thêm section "Hướng dẫn chạy prototype" vào README:
```markdown
## Chạy Prototype

### Yêu cầu
- Python 3.10+
- OpenAI API key

### Cài đặt
cd codebase
pip install -r requirements.txt
cp .env.example .env  # rồi điền API key

### Chạy
cd codebase
uvicorn server:app --reload --port 8000

### Demo
Mở file vlearn_clone.html bằng browser.
```

- [ ] **Step 3: Test clean install từ đầu**

```bash
cd codebase
pip install -r requirements.txt
cp .env.example .env  # điền key
uvicorn server:app --reload --port 8000
# Mở vlearn_clone.html → test 3 features
```

- [ ] **Step 4: Commit**

```bash
git add codebase/.gitignore README.md
git commit -m "docs: add setup instructions and gitignore"
```
