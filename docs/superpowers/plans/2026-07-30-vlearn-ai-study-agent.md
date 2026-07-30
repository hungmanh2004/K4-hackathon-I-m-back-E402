# VLearn AI Study Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local AI agent that reads a fixed slide PDF and produces a summary, a page-anchored mind map, and a ~1-minute Vietnamese audio podcast — all driven by one OpenAI tool-calling loop whose steps stream live to the browser.

**Architecture:** A FastAPI backend exposes exactly one working endpoint (`POST /api/agent`) that streams Server-Sent Events. Behind it, an agent loop gives `gpt-4o-mini` five tools: two for reading the PDF (`list_pages`, `read_pages`) and three for producing output (`emit_summary`, `emit_mindmap`, `render_audio`). The agent decides which pages to read and which artifacts to produce; the tools themselves contain no LLM calls. The existing `vlearn_clone.html` is upgraded from a hardcoded mock into a real SSE client.

**Tech Stack:** Python 3.10+ · FastAPI · uvicorn · pymupdf · openai · elevenlabs · pytest · vanilla HTML/CSS/JS · markmap + marked.js via CDN

**Design doc:** [`docs/superpowers/specs/2026-07-30-vlearn-ai-study-agent-design.md`](../specs/2026-07-30-vlearn-ai-study-agent-design.md)

## Global Constraints

- **Working directory for all backend commands is `codebase/`.** Every `python`/`pytest`/`uvicorn` command in this plan assumes you are inside `codebase/`.
- **PDF path:** `../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf` (relative to `codebase/`). The filename contains spaces and a space before `.pdf` — always quote it.
- **LLM model:** `gpt-4o-mini`. **TTS model:** `eleven_turbo_v2_5`.
- **`MAX_ITERATIONS = 8`** — agent loop hard stop.
- **`MAX_TTS_CHARS = 5000`** — truncate at sentence boundary above this.
- **Two API keys required:** `OPENAI_API_KEY` and `ELEVENLABS_API_KEY`. Server refuses to start if either is missing.
- **Never commit `.env`.** Only `.env.example` is committed.
- **All user-facing text and all AI output is Vietnamese.** Prompts are written in Vietnamese.
- **JSON serialisation for SSE must use `ensure_ascii=False`** or Vietnamese becomes `\uXXXX`.
- **ElevenLabs free tier is ~10,000 credits/month at ~1 credit per character.** Never call the real TTS API in a loop or in tests. Only Task 1 and one manual check in Task 7 call it for real.

---

### Task 1: Project setup and ElevenLabs Vietnamese voice spike

This task exists to kill the highest risk first: if ElevenLabs cannot read Vietnamese acceptably, the audio leg of the product is dead and we need to know before writing any other code.

**Files:**
- Modify: `codebase/requirements.txt`
- Create: `codebase/.gitignore`
- Create: `codebase/.env.example`
- Create: `codebase/conftest.py`
- Create: `codebase/scripts/try_voices.py`

**Interfaces:**
- Consumes: nothing
- Produces: a working Python environment; a chosen `ELEVENLABS_VOICE_ID` recorded in `.env.example`; `codebase/` importable by pytest

- [ ] **Step 1: Replace `codebase/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
pymupdf==1.24.0
openai>=1.55.0,<2
elevenlabs>=1.9.0
python-dotenv==1.0.1
pytest==8.3.3
httpx==0.27.2
```

`httpx` is required by FastAPI's `TestClient`. `python-multipart` was removed — there is no file upload in this design.

- [ ] **Step 2: Create `codebase/.gitignore`**

```
.env
__pycache__/
*.pyc
audio_output/*.mp3
.pytest_cache/
```

- [ ] **Step 3: Create `codebase/.env.example`**

```
# LLM — dùng cho agent loop
OPENAI_API_KEY=sk-your-openai-key-here

# TTS — dùng cho sinh audio tiếng Việt
ELEVENLABS_API_KEY=your-elevenlabs-key-here

# Voice ID chọn sau khi nghe thử ở Task 1 (scripts/try_voices.py).
# Ghi lại giọng đã chọn vào comment bên dưới để người sau biết vì sao chọn nó.
# Đã chọn: <điền tên giọng + lý do sau khi nghe>
ELEVENLABS_VOICE_ID=

# real | stub — stub không gọi API, dùng cho eval và test
TTS_MODE=real
```

- [ ] **Step 4: Create `codebase/conftest.py`**

```python
# Sự tồn tại của file này khiến pytest thêm thư mục codebase/ vào sys.path,
# nhờ đó test trong codebase/tests/ import được pdf_parser, tools, agent...
# File cố tình để trống.
```

Without this file, `pytest` inserts only `codebase/tests/` into `sys.path` and every `import pdf_parser` in the test suite fails with `ModuleNotFoundError`.

- [ ] **Step 5: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: installs without error. Confirm with `python -c "import fitz, openai, elevenlabs, fastapi; print('ok')"` → prints `ok`.

- [ ] **Step 6: Create `codebase/scripts/try_voices.py`**

```python
"""Nghe thử giọng tiếng Việt của ElevenLabs bằng câu NGẮN.

Vì sao câu ngắn: free tier ~10.000 credit/tháng, ~1 credit/ký tự.
Câu test dưới đây ~90 ký tự, thử 3 giọng hết ~270 credit.
Dùng nguyên script podcast (~3.000 ký tự) để thử giọng sẽ đốt sạch quota.

Chạy:  python scripts/try_voices.py <voice_id> [<voice_id> ...]
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

# Câu test có dấu đầy đủ, có số, có thuật ngữ tiếng Anh xen kẽ —
# đúng kiểu câu sẽ xuất hiện trong podcast thật.
SAMPLE = "Xin chào, đây là bản tóm tắt bài giảng HCI, phần giao diện người dùng, trang 12."

OUT_DIR = Path(__file__).parent.parent / "audio_output" / "voice_test"


def main(voice_ids: list[str]) -> None:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit("Thiếu ELEVENLABS_API_KEY trong .env")

    client = ElevenLabs(api_key=api_key)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for voice_id in voice_ids:
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            model_id="eleven_turbo_v2_5",
            text=SAMPLE,
            output_format="mp3_44100_128",
        )
        path = OUT_DIR / f"{voice_id}.mp3"
        with open(path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        print(f"{voice_id} -> {path}  ({len(SAMPLE)} ký tự)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
```

- [ ] **Step 7: Pick 2-3 voice IDs to test**

Go to the ElevenLabs Voice Library in the web app and copy 2-3 voice IDs. Prefer voices tagged as multilingual.

**Model choice matters and is not obvious:** `eleven_multilingual_v2` covers 29 languages and **Vietnamese is not among them**, despite the name suggesting otherwise. Vietnamese arrived with the 32-language models — `eleven_turbo_v2_5` and `eleven_flash_v2_5`. This plan uses `eleven_turbo_v2_5`.

If ElevenLabs now offers a newer model with better Vietnamese coverage, verify it against their current docs and use it instead — update `model_id` in this script and in `tts.py` (Task 3) together.

- [ ] **Step 8: Run the spike and listen**

Run: `python scripts/try_voices.py <id1> <id2> <id3>`
Expected: 3 MP3 files under `codebase/audio_output/voice_test/`.

Play each one. Judge on: are Vietnamese tone marks pronounced, is it intelligible at normal speed, is the accent tolerable to a Vietnamese listener.

**Decision gate:**
- At least one voice acceptable → record its ID in `.env.example` (Step 3's comment line) and in your `.env`. Continue to Task 2.
- No voice acceptable → **stop and report to the user before continuing.** The audio feature needs to be renegotiated (different provider, or dropped to a non-goal). Do not silently build a feature that sounds broken.

- [ ] **Step 9: Commit**

```bash
git add codebase/requirements.txt codebase/.gitignore codebase/.env.example \
        codebase/conftest.py codebase/scripts/try_voices.py
git commit -m "chore: project setup + ElevenLabs Vietnamese voice spike"
```

---

### Task 2: PDF parser

**Files:**
- Create: `codebase/pdf_parser.py`
- Create: `codebase/tests/test_pdf_parser.py`

**Interfaces:**
- Consumes: nothing (pure, no AI, no network)
- Produces:
  - `extract_pages(pdf_path: str) -> list[dict]` — each dict is `{"page": int, "text": str}`, `page` is 1-indexed, list is ordered by page
  - `page_count(pdf_path: str) -> int`

- [ ] **Step 1: Write the failing test**

Create `codebase/tests/test_pdf_parser.py`:

```python
import pytest

from pdf_parser import extract_pages, page_count

PDF = "../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf"


def test_page_count_is_positive():
    assert page_count(PDF) > 0


def test_extract_pages_length_matches_page_count():
    pages = extract_pages(PDF)
    assert len(pages) == page_count(PDF)


def test_pages_are_one_indexed_and_ordered():
    pages = extract_pages(PDF)
    assert [p["page"] for p in pages] == list(range(1, len(pages) + 1))


def test_every_page_has_text_key_as_string():
    pages = extract_pages(PDF)
    assert all(isinstance(p["text"], str) for p in pages)


def test_document_has_meaningful_text_overall():
    # Slide PDF, không phải bản scan — tổng text phải đáng kể.
    # Không assert từng trang vì trang thuần ảnh hợp lệ và sẽ rỗng.
    pages = extract_pages(PDF)
    total = sum(len(p["text"]) for p in pages)
    assert total > 1000


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        extract_pages("../khong-ton-tai.pdf")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pdf_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pdf_parser'`

- [ ] **Step 3: Write the implementation**

Create `codebase/pdf_parser.py`:

```python
"""Trích xuất text từ PDF theo từng trang. Hàm thuần — không AI, không mạng."""
import os

import fitz  # pymupdf


def extract_pages(pdf_path: str) -> list[dict]:
    """Trả về [{"page": 1, "text": "..."}, ...] — page đánh số từ 1.

    Trang thuần ảnh sẽ có text rỗng; đó là hợp lệ, không phải lỗi.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Không tìm thấy PDF: {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        return [
            {"page": i + 1, "text": doc[i].get_text("text").strip()}
            for i in range(len(doc))
        ]
    finally:
        doc.close()


def page_count(pdf_path: str) -> int:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Không tìm thấy PDF: {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pdf_parser.py -v`
Expected: 6 passed

- [ ] **Step 5: Record the real page count**

Run: `python -c "from pdf_parser import page_count; print(page_count('../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf'))"`
Expected: prints an integer. Note it — `vlearn_clone.html` currently hardcodes `totalPages = 44`, and Task 7 replaces that with the real value from the backend.

- [ ] **Step 6: Commit**

```bash
git add codebase/pdf_parser.py codebase/tests/test_pdf_parser.py
git commit -m "feat: add per-page PDF text extraction"
```

---

### Task 3: ElevenLabs TTS with content-hash cache

**Files:**
- Create: `codebase/tts.py`
- Create: `codebase/tests/test_tts.py`

**Interfaces:**
- Consumes: `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `TTS_MODE` from environment
- Produces:
  - `MAX_TTS_CHARS: int = 5000`
  - `AUDIO_DIR: pathlib.Path` — `codebase/audio_output/`
  - `truncate_at_sentence(text: str, max_chars: int) -> tuple[str, bool]` — returns `(text, was_truncated)`
  - `audio_path_for(script: str) -> pathlib.Path` — deterministic path from SHA-256 of script
  - `generate_audio(script: str) -> dict` — returns `{"filename": str, "char_count": int, "cached": bool, "truncated": bool}`

- [ ] **Step 1: Write the failing test**

Create `codebase/tests/test_tts.py`:

```python
import tts


def test_truncate_leaves_short_text_alone():
    text = "Câu một. Câu hai."
    out, was_truncated = tts.truncate_at_sentence(text, 100)
    assert out == text
    assert was_truncated is False


def test_truncate_cuts_at_sentence_boundary_not_mid_word():
    text = "Câu một rất dài. Câu hai cũng dài. Câu ba nữa."
    out, was_truncated = tts.truncate_at_sentence(text, 20)
    assert was_truncated is True
    assert out.endswith(".")
    assert len(out) <= 20


def test_truncate_falls_back_to_hard_cut_when_no_sentence_fits():
    # Không có dấu chấm nào trong giới hạn -> vẫn phải trả về thứ gì đó
    text = "mot cau rat dai khong co dau cham nao ca va cu the keo mai"
    out, was_truncated = tts.truncate_at_sentence(text, 20)
    assert was_truncated is True
    assert len(out) <= 20
    assert out  # không rỗng


def test_audio_path_is_deterministic():
    assert tts.audio_path_for("xin chào") == tts.audio_path_for("xin chào")


def test_audio_path_differs_for_different_scripts():
    assert tts.audio_path_for("xin chào") != tts.audio_path_for("tạm biệt")


def test_stub_mode_does_not_call_api(monkeypatch):
    monkeypatch.setenv("TTS_MODE", "stub")
    result = tts.generate_audio("Xin chào các bạn.")
    assert result["filename"].endswith(".mp3")
    assert result["char_count"] == len("Xin chào các bạn.")
    assert result["cached"] is False


def test_cache_hit_returns_existing_file_without_calling_api(monkeypatch):
    monkeypatch.setenv("TTS_MODE", "real")
    script = "Kịch bản dùng để kiểm tra cache, không gọi API."

    # Tạo sẵn file ở đúng đường dẫn cache -> generate_audio phải short-circuit.
    path = tts.audio_path_for(script)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-mp3-bytes")

    def explode(*args, **kwargs):
        raise AssertionError("Cache hit mà vẫn gọi API ElevenLabs")

    monkeypatch.setattr(tts, "_call_elevenlabs", explode)

    try:
        result = tts.generate_audio(script)
        assert result["cached"] is True
        assert result["filename"] == path.name
    finally:
        path.unlink()


def test_script_over_limit_is_truncated(monkeypatch):
    monkeypatch.setenv("TTS_MODE", "stub")
    long_script = ("Đây là một câu dài. " * 400)  # ~8000 ký tự
    result = tts.generate_audio(long_script)
    assert result["truncated"] is True
    assert result["char_count"] <= tts.MAX_TTS_CHARS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tts'`

- [ ] **Step 3: Write the implementation**

Create `codebase/tts.py`:

```python
"""Sinh audio tiếng Việt bằng ElevenLabs, có cache theo nội dung script.

Vì sao cần cache: free tier ElevenLabs ~10.000 credit/tháng, ~1 credit mỗi
ký tự. Một script podcast tiếng Việt ~2.000-3.000 ký tự, tức cả tháng chỉ
đủ 3-5 lần sinh. Cache theo hash nội dung khiến việc chạy lại cùng một demo
không tốn thêm credit — và là lưới an toàn khi demo live: đã chạy thử trước
thì lúc demo thật là cache hit, không phụ thuộc mạng.
"""
import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MAX_TTS_CHARS = 5000
TTS_MODEL = "eleven_turbo_v2_5"  # KHÔNG dùng eleven_multilingual_v2 — không có tiếng Việt
AUDIO_DIR = Path(__file__).parent / "audio_output"


def truncate_at_sentence(text: str, max_chars: int) -> tuple[str, bool]:
    """Cắt text về <= max_chars, ưu tiên dừng ở cuối câu.

    Trả về (text_đã_cắt, có_bị_cắt_không). Không bao giờ cắt giữa từ nếu
    tìm được dấu chấm; nếu không có dấu chấm nào trong giới hạn thì cắt cứng.
    """
    if len(text) <= max_chars:
        return text, False

    window = text[:max_chars]
    cut = max(window.rfind("."), window.rfind("!"), window.rfind("?"))
    if cut > 0:
        return window[: cut + 1], True
    return window, True


def audio_path_for(script: str) -> Path:
    """Đường dẫn file mp3 suy ra từ nội dung script — cùng script, cùng file."""
    key = hashlib.sha256(script.encode("utf-8")).hexdigest()[:16]
    return AUDIO_DIR / f"{key}.mp3"


def _call_elevenlabs(script: str, path: Path) -> None:
    """Gọi API thật và ghi ra file.

    Tách riêng thành hàm để test có thể monkeypatch, xác nhận cache hit
    KHÔNG chạm tới API.
    """
    from elevenlabs.client import ElevenLabs

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    if not api_key:
        raise RuntimeError("Thiếu ELEVENLABS_API_KEY")
    if not voice_id:
        raise RuntimeError("Thiếu ELEVENLABS_VOICE_ID (chốt ở Task 1)")

    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=TTS_MODEL,
        text=script,
        output_format="mp3_44100_128",
    )

    # ElevenLabs trả generator các chunk bytes — không có stream_to_file()
    # như OpenAI, phải tự gom.
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        for chunk in audio:
            f.write(chunk)


def generate_audio(script: str) -> dict:
    """Sinh mp3 từ script. Trả {filename, char_count, cached, truncated}."""
    script, truncated = truncate_at_sentence(script, MAX_TTS_CHARS)
    path = audio_path_for(script)

    if os.getenv("TTS_MODE", "real") == "stub":
        return {
            "filename": path.name,
            "char_count": len(script),
            "cached": False,
            "truncated": truncated,
        }

    if path.exists():
        return {
            "filename": path.name,
            "char_count": len(script),
            "cached": True,
            "truncated": truncated,
        }

    _call_elevenlabs(script, path)
    return {
        "filename": path.name,
        "char_count": len(script),
        "cached": False,
        "truncated": truncated,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tts.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add codebase/tts.py codebase/tests/test_tts.py
git commit -m "feat: add ElevenLabs TTS with content-hash cache and sentence-safe truncation"
```

---

### Task 4: Agent tools

**Files:**
- Create: `codebase/tools.py`
- Create: `codebase/tests/test_tools.py`

**Interfaces:**
- Consumes: `pdf_parser.extract_pages`, `tts.generate_audio`
- Produces:
  - `ToolResult` dataclass with fields `content: str`, `summary: str`, `artifact: dict | None`
  - `load_document(pdf_path: str) -> None` — loads pages into module state; must be called before `execute_tool`
  - `get_page_count() -> int`
  - `TOOL_SCHEMAS: list[dict]` — OpenAI function-calling schemas for all five tools
  - `validate_mindmap(outline_md: str, n_pages: int) -> dict` — returns `{"invalid_pages": list[int], "branch_count": int, "max_depth": int, "issues": list[str]}`
  - `execute_tool(name: str, args: dict) -> ToolResult`

- [ ] **Step 1: Write the failing test**

Create `codebase/tests/test_tools.py`:

```python
import pytest

import tools

PDF = "../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf"


@pytest.fixture(autouse=True)
def loaded_document():
    tools.load_document(PDF)


# --- validate_mindmap ---

GOOD_MAP = """# HCI Nhập môn
## Khái niệm cơ bản
### Định nghĩa HCI [Tr.3]
### Lịch sử phát triển [Tr.5]
## Nguyên tắc thiết kế
### Lấy người dùng làm trung tâm [Tr.10]
## Ứng dụng
### Thiết kế giao diện [Tr.15]
"""


def test_valid_mindmap_reports_no_issues():
    r = tools.validate_mindmap(GOOD_MAP, n_pages=44)
    assert r["invalid_pages"] == []
    assert r["branch_count"] == 3
    assert r["max_depth"] == 3
    assert r["issues"] == []


def test_page_reference_beyond_document_is_flagged():
    r = tools.validate_mindmap("# A\n## B\n### C [Tr.999]\n", n_pages=44)
    assert 999 in r["invalid_pages"]
    assert any("999" in i for i in r["issues"])


def test_page_reference_zero_is_flagged():
    r = tools.validate_mindmap("# A\n## B\n### C [Tr.0]\n", n_pages=44)
    assert 0 in r["invalid_pages"]


def test_too_few_main_branches_is_flagged():
    r = tools.validate_mindmap("# A\n## B\n### C [Tr.1]\n", n_pages=44)
    assert r["branch_count"] == 1
    assert any("nhánh" in i for i in r["issues"])


def test_depth_over_four_is_flagged():
    deep = "# A\n## B\n### C\n#### D\n##### E [Tr.1]\n"
    r = tools.validate_mindmap(deep, n_pages=44)
    assert r["max_depth"] == 5
    assert any("cấp" in i for i in r["issues"])


# --- execute_tool ---

def test_list_pages_reports_every_page():
    result = tools.execute_tool("list_pages", {})
    assert str(tools.get_page_count()) in result.summary
    assert result.artifact is None


def test_read_pages_returns_requested_page_text():
    result = tools.execute_tool("read_pages", {"pages": [1, 2]})
    assert "Trang 1" in result.content
    assert "Trang 2" in result.content
    assert result.artifact is None


def test_read_pages_ignores_out_of_range_pages():
    result = tools.execute_tool("read_pages", {"pages": [1, 9999]})
    assert "Trang 1" in result.content
    assert "9999" in result.content  # phải báo cho model biết trang này không tồn tại


def test_emit_summary_produces_summary_artifact():
    result = tools.execute_tool("emit_summary", {"markdown": "- Ý chính [Tr.1]"})
    assert result.artifact["kind"] == "summary"
    assert result.artifact["content"] == "- Ý chính [Tr.1]"


def test_emit_mindmap_produces_mindmap_artifact_with_issues_list():
    result = tools.execute_tool("emit_mindmap", {"outline_md": GOOD_MAP})
    assert result.artifact["kind"] == "mindmap"
    assert result.artifact["issues"] == []


def test_emit_mindmap_artifact_carries_precomputed_metrics():
    # Eval đọc lại hai số này thay vì parse markdown lần nữa
    result = tools.execute_tool("emit_mindmap", {"outline_md": GOOD_MAP})
    assert result.artifact["branch_count"] == 3
    assert result.artifact["max_depth"] == 3


def test_emit_mindmap_reports_problems_back_to_the_model():
    bad = "# A\n## B\n### C [Tr.999]\n"
    result = tools.execute_tool("emit_mindmap", {"outline_md": bad})
    assert result.artifact["issues"]
    # content quay lại model phải nêu vấn đề để nó có cơ hội sửa
    assert "999" in result.content


def test_render_audio_produces_audio_artifact(monkeypatch):
    monkeypatch.setenv("TTS_MODE", "stub")
    result = tools.execute_tool("render_audio", {"script": "Xin chào các bạn."})
    assert result.artifact["kind"] == "audio"
    assert result.artifact["url"].startswith("/audio/")


def test_unknown_tool_raises():
    with pytest.raises(ValueError):
        tools.execute_tool("khong_ton_tai", {})


def test_all_schemas_are_wellformed():
    names = {s["function"]["name"] for s in tools.TOOL_SCHEMAS}
    assert names == {
        "list_pages", "read_pages", "emit_summary", "emit_mindmap", "render_audio"
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools'`

- [ ] **Step 3: Write the implementation**

Create `codebase/tools.py`:

```python
"""Bộ tool của agent.

Nguyên tắc thiết kế: tool CHỈ là cổng truy cập dữ liệu và kênh xuất kết quả.
Không tool nào gọi LLM. Toàn bộ phần suy nghĩ (đọc trang nào, khái niệm nào
là nhánh chính) nằm trong agent — nếu nhét LLM vào trong tool thì agent chỉ
còn là router và ta mất đúng thứ khiến nó là agent.
"""
import re
from dataclasses import dataclass

import pdf_parser
import tts

MIN_MAIN_BRANCHES = 3
MAX_DEPTH = 4

_pages: list[dict] = []


@dataclass
class ToolResult:
    content: str          # nội dung trả lại cho model
    summary: str          # mô tả ngắn cho panel trace trên UI
    artifact: dict | None # kết quả đẩy lên UI, None nếu tool không sinh output


def load_document(pdf_path: str) -> None:
    """Nạp PDF vào bộ nhớ. Phải gọi trước execute_tool."""
    global _pages
    _pages = pdf_parser.extract_pages(pdf_path)


def get_page_count() -> int:
    return len(_pages)


# --- Kiểm tra mind map (code thuần, không LLM) ---

_PAGE_REF = re.compile(r"\[Tr\.(\d+)\]")


def validate_mindmap(outline_md: str, n_pages: int) -> dict:
    """Soát outline markdown trước khi cho render.

    Bắt ba loại lỗi: trích trang không tồn tại (bịa nguồn), quá ít nhánh
    chính (outline suy biến thành danh sách phẳng), cây quá sâu (không đọc được).
    """
    invalid_pages = sorted(
        {n for n in (int(m) for m in _PAGE_REF.findall(outline_md))
         if n < 1 or n > n_pages}
    )

    branch_count, max_depth = 0, 0
    for line in outline_md.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        max_depth = max(max_depth, level)
        if level == 2:
            branch_count += 1

    issues = []
    if invalid_pages:
        issues.append(
            f"Trích dẫn trang không tồn tại: {invalid_pages}. "
            f"Tài liệu chỉ có {n_pages} trang."
        )
    if branch_count < MIN_MAIN_BRANCHES:
        issues.append(
            f"Chỉ có {branch_count} nhánh chính (dòng '## '), "
            f"cần ít nhất {MIN_MAIN_BRANCHES}."
        )
    if max_depth > MAX_DEPTH:
        issues.append(f"Cây sâu {max_depth} cấp, tối đa {MAX_DEPTH} cấp.")

    return {
        "invalid_pages": invalid_pages,
        "branch_count": branch_count,
        "max_depth": max_depth,
        "issues": issues,
    }


# --- Khai báo schema cho OpenAI ---

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_pages",
            "description": (
                "Liệt kê mục lục thô của tài liệu: số trang, dòng đầu và độ dài "
                "mỗi trang. Gọi cái này TRƯỚC để biết nên đọc sâu trang nào."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_pages",
            "description": (
                "Đọc toàn bộ text của các trang chỉ định. Gọi MỘT lần với đầy đủ "
                "các trang cần thiết, đừng gọi nhiều lần lẻ tẻ."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pages": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Danh sách số trang, đánh số từ 1.",
                    }
                },
                "required": ["pages"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emit_summary",
            "description": "Xuất bản tóm tắt ra tab Tóm tắt của giao diện.",
            "parameters": {
                "type": "object",
                "properties": {
                    "markdown": {
                        "type": "string",
                        "description": (
                            "Tóm tắt dạng markdown tiếng Việt, mỗi ý ghi nguồn [Tr.N]."
                        ),
                    }
                },
                "required": ["markdown"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emit_mindmap",
            "description": "Xuất sơ đồ tư duy ra tab Mind Map của giao diện.",
            "parameters": {
                "type": "object",
                "properties": {
                    "outline_md": {
                        "type": "string",
                        "description": (
                            "Markdown heading: đúng MỘT dòng '# ' làm gốc, các dòng "
                            "'## ' là nhánh chính (tối thiểu 3), tối đa 4 cấp. "
                            "Mỗi node lá kết thúc bằng [Tr.N]."
                        ),
                    }
                },
                "required": ["outline_md"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "render_audio",
            "description": (
                "Đọc script thành audio tiếng Việt và xuất ra tab Audio. "
                "Chỉ gọi khi người dùng yêu cầu audio/podcast/nghe."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": (
                            "Script podcast tiếng Việt 300-500 từ, văn nói tự nhiên. "
                            "KHÔNG markdown, KHÔNG ký hiệu [Tr.N] (đọc lên nghe kỳ)."
                        ),
                    }
                },
                "required": ["script"],
            },
        },
    },
]


# --- Thực thi ---

def _tool_list_pages() -> ToolResult:
    lines = [
        f"Trang {p['page']}: {(p['text'].splitlines() or [''])[0][:60]!r} "
        f"({len(p['text'])} ký tự)"
        for p in _pages
    ]
    return ToolResult(
        content=f"Tài liệu có {len(_pages)} trang.\n" + "\n".join(lines),
        summary=f"Liệt kê {len(_pages)} trang",
        artifact=None,
    )


def _tool_read_pages(pages: list[int]) -> ToolResult:
    by_number = {p["page"]: p["text"] for p in _pages}
    chunks, missing = [], []

    for n in pages:
        if n in by_number:
            chunks.append(f"--- Trang {n} ---\n{by_number[n]}")
        else:
            missing.append(n)

    content = "\n\n".join(chunks)
    if missing:
        content += (
            f"\n\n[Lưu ý] Các trang không tồn tại nên bị bỏ qua: {missing}. "
            f"Tài liệu chỉ có {len(_pages)} trang."
        )

    total = sum(len(c) for c in chunks)
    return ToolResult(
        content=content,
        summary=f"Đọc {len(chunks)} trang ({total} ký tự)",
        artifact=None,
    )


def _tool_emit_summary(markdown: str) -> ToolResult:
    return ToolResult(
        content="Đã hiển thị tóm tắt lên giao diện.",
        summary=f"Xuất tóm tắt ({len(markdown)} ký tự)",
        artifact={"kind": "summary", "content": markdown},
    )


def _tool_emit_mindmap(outline_md: str) -> ToolResult:
    report = validate_mindmap(outline_md, len(_pages))

    if report["issues"]:
        content = (
            "Đã hiển thị sơ đồ nhưng có vấn đề, các node lỗi bị gắn cờ cảnh báo:\n"
            + "\n".join(f"- {i}" for i in report["issues"])
            + "\nNếu sửa được thì gọi lại emit_mindmap với bản đã sửa."
        )
    else:
        content = "Đã hiển thị sơ đồ tư duy lên giao diện."

    return ToolResult(
        content=content,
        summary=f"Xuất sơ đồ ({report['branch_count']} nhánh chính)",
        artifact={
            "kind": "mindmap",
            "content": outline_md,
            "issues": report["issues"],
            "invalid_pages": report["invalid_pages"],
            # Đẩy kèm số liệu đã tính để eval khỏi phải parse markdown lần nữa
            "branch_count": report["branch_count"],
            "max_depth": report["max_depth"],
        },
    )


def _tool_render_audio(script: str) -> ToolResult:
    info = tts.generate_audio(script)
    note = " (dùng lại bản đã sinh trước đó)" if info["cached"] else ""
    return ToolResult(
        content=f"Đã tạo audio {info['char_count']} ký tự{note}.",
        summary=f"Sinh audio {info['char_count']} ký tự{note}",
        artifact={
            "kind": "audio",
            "url": f"/audio/{info['filename']}",
            "script": script,
            "char_count": info["char_count"],
            "truncated": info["truncated"],
        },
    )


_DISPATCH = {
    "list_pages": lambda a: _tool_list_pages(),
    "read_pages": lambda a: _tool_read_pages(a["pages"]),
    "emit_summary": lambda a: _tool_emit_summary(a["markdown"]),
    "emit_mindmap": lambda a: _tool_emit_mindmap(a["outline_md"]),
    "render_audio": lambda a: _tool_render_audio(a["script"]),
}


def execute_tool(name: str, args: dict) -> ToolResult:
    if name not in _DISPATCH:
        raise ValueError(f"Tool không tồn tại: {name}")
    return _DISPATCH[name](args)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tools.py -v`
Expected: 15 passed

- [ ] **Step 5: Commit**

```bash
git add codebase/tools.py codebase/tests/test_tools.py
git commit -m "feat: add agent tools with mind map validation guard"
```

---

### Task 5: Agent loop

**Files:**
- Create: `codebase/agent.py`
- Create: `codebase/tests/test_agent.py`

**Interfaces:**
- Consumes: `tools.TOOL_SCHEMAS`, `tools.execute_tool`, `tools.get_page_count`
- Produces:
  - `MODEL: str = "gpt-4o-mini"`, `MAX_ITERATIONS: int = 8`
  - `build_system_prompt(n_pages: int) -> str`
  - `run_stream(message: str, client=None) -> Iterator[dict]` — yields event dicts
  - `run(message: str, client=None) -> dict` — returns `{"trace": list[dict], "artifacts": dict, "error": str | None, "iterations": int}`

Event shapes emitted by `run_stream`:

| `type` | Extra fields |
|---|---|
| `status` | `text` |
| `tool_call` | `name`, `args` |
| `tool_result` | `name`, `summary` |
| `artifact` | `kind` plus the artifact's own fields |
| `message` | `content` |
| `error` | `message` |
| `done` | `iterations` |

- [ ] **Step 1: Write the failing test**

Create `codebase/tests/test_agent.py`:

```python
import json
from types import SimpleNamespace

import pytest

import agent
import tools

PDF = "../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf"


@pytest.fixture(autouse=True)
def loaded_document():
    tools.load_document(PDF)


# --- Fake OpenAI client: trả về kịch bản định sẵn, không gọi mạng ---

def _tool_call(call_id, name, args):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


def _response(tool_calls=None, content=None):
    msg = SimpleNamespace(role="assistant", content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class FakeClient:
    """Phát lần lượt các response đã dựng sẵn."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls += 1
        if not self._responses:
            return _response(content="Xong.")
        return self._responses.pop(0)


def test_plain_reply_without_tools_emits_message_then_done():
    client = FakeClient([_response(content="Chào bạn.")])
    events = list(agent.run_stream("xin chào", client=client))
    types = [e["type"] for e in events]
    assert "message" in types
    assert types[-1] == "done"


def test_tool_call_emits_call_then_result():
    client = FakeClient([
        _response(tool_calls=[_tool_call("c1", "list_pages", {})]),
        _response(content="Tài liệu có nhiều trang."),
    ])
    events = list(agent.run_stream("tài liệu này có gì", client=client))
    types = [e["type"] for e in events]
    assert types.index("tool_call") < types.index("tool_result")


def test_emit_summary_surfaces_an_artifact_event():
    client = FakeClient([
        _response(tool_calls=[_tool_call("c1", "emit_summary", {"markdown": "- Ý [Tr.1]"})]),
        _response(content="Đã tóm tắt."),
    ])
    events = list(agent.run_stream("tóm tắt", client=client))
    artifacts = [e for e in events if e["type"] == "artifact"]
    assert len(artifacts) == 1
    assert artifacts[0]["kind"] == "summary"


def test_two_emits_in_one_turn_produce_two_artifacts():
    client = FakeClient([
        _response(tool_calls=[
            _tool_call("c1", "emit_summary", {"markdown": "- Ý [Tr.1]"}),
            _tool_call("c2", "emit_mindmap", {
                "outline_md": "# A\n## B\n### x [Tr.1]\n## C\n### y [Tr.2]\n## D\n### z [Tr.3]\n"
            }),
        ]),
        _response(content="Xong cả hai."),
    ])
    events = list(agent.run_stream("tóm tắt rồi vẽ sơ đồ", client=client))
    kinds = [e["kind"] for e in events if e["type"] == "artifact"]
    assert kinds == ["summary", "mindmap"]


def test_loop_stops_at_max_iterations():
    # Luôn trả tool call -> phải bị chặn, không chạy vô hạn
    endless = [_response(tool_calls=[_tool_call(f"c{i}", "list_pages", {})])
               for i in range(agent.MAX_ITERATIONS + 5)]
    client = FakeClient(endless)
    events = list(agent.run_stream("lặp mãi", client=client))
    assert client.calls <= agent.MAX_ITERATIONS
    assert events[-1]["type"] == "done"


def test_api_failure_emits_error_then_done():
    class ExplodingClient:
        def __init__(self):
            def boom(**kwargs):
                raise RuntimeError("API sập")
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=boom))

    events = list(agent.run_stream("bất kỳ", client=ExplodingClient()))
    types = [e["type"] for e in events]
    assert "error" in types
    assert types[-1] == "done"


def test_run_collects_the_same_events_as_run_stream():
    client = FakeClient([
        _response(tool_calls=[_tool_call("c1", "emit_summary", {"markdown": "- Ý [Tr.1]"})]),
        _response(content="Đã tóm tắt."),
    ])
    result = agent.run("tóm tắt", client=client)
    assert "summary" in result["artifacts"]
    assert result["error"] is None
    assert result["iterations"] >= 1


def test_system_prompt_states_the_real_page_count():
    prompt = agent.build_system_prompt(44)
    assert "44" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent'`

- [ ] **Step 3: Write the implementation**

Create `codebase/agent.py`:

```python
"""Vòng lặp agent — nơi duy nhất gọi LLM.

run_stream() là nguồn sự thật duy nhất. run() chỉ là bản đã rút cạn của nó,
dùng cho eval. Không viết đường chạy thứ hai cho eval: hai đường sẽ trôi khỏi
nhau và eval sẽ đo một thứ khác với thứ đang chạy thật.
"""
import json
import os
from typing import Iterator

from dotenv import load_dotenv

import tools

load_dotenv()

MODEL = "gpt-4o-mini"
MAX_ITERATIONS = 8

_client = None


def _default_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def build_system_prompt(n_pages: int) -> str:
    return f"""Bạn là VLearn Study Agent, trợ lý học tập làm việc trên MỘT tài liệu slide PDF tiếng Việt.

Tài liệu có {n_pages} trang. Bạn KHÔNG được thấy sẵn nội dung — phải dùng tool để đọc.

Quy trình:
1. Gọi list_pages() để biết tài liệu có gì.
2. Gọi read_pages() MỘT lần với đầy đủ các trang cần thiết. Đừng gọi lẻ tẻ nhiều lần.
3. Dùng đúng tool tương ứng với thứ người dùng yêu cầu:
   - tóm tắt        -> emit_summary
   - sơ đồ tư duy    -> emit_mindmap
   - audio/podcast   -> render_audio
4. Người dùng yêu cầu nhiều thứ thì gọi nhiều tool emit trong CÙNG một lượt,
   sau khi đã đọc trang một lần.

Quy tắc bắt buộc:
- Mọi thông tin phải lấy từ nội dung đã đọc. Tuyệt đối không bịa.
- Ghi nguồn theo dạng [Tr.N] với N là số trang thật.
- emit_mindmap: đúng MỘT dòng '# ' làm gốc, các dòng '## ' là nhánh chính
  (tối thiểu 3), tối đa 4 cấp heading, mỗi node lá kết thúc bằng [Tr.N].
- render_audio: script tiếng Việt 300-500 từ, văn nói tự nhiên, KHÔNG markdown,
  KHÔNG ký hiệu [Tr.N] vì đọc lên nghe rất kỳ.
- Nếu tài liệu không có thông tin người dùng hỏi, nói thẳng là không có.
- Trả lời người dùng bằng tiếng Việt, ngắn gọn.
"""


def run_stream(message: str, client=None) -> Iterator[dict]:
    """Chạy agent, yield từng event một."""
    client = client or _default_client()
    n_pages = tools.get_page_count()

    messages = [
        {"role": "system", "content": build_system_prompt(n_pages)},
        {"role": "user", "content": message},
    ]

    yield {"type": "status", "text": "Agent bắt đầu xử lý..."}

    iterations = 0
    try:
        for _ in range(MAX_ITERATIONS):
            iterations += 1
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools.TOOL_SCHEMAS,
            )
            reply = response.choices[0].message

            if not reply.tool_calls:
                yield {"type": "message", "content": reply.content or ""}
                break

            messages.append({
                "role": "assistant",
                "content": reply.content,
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {
                            "name": c.function.name,
                            "arguments": c.function.arguments,
                        },
                    }
                    for c in reply.tool_calls
                ],
            })

            for call in reply.tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                yield {"type": "tool_call", "name": name, "args": args}

                try:
                    result = tools.execute_tool(name, args)
                except Exception as exc:  # tool hỏng không được giết cả phiên
                    result = tools.ToolResult(
                        content=f"Tool lỗi: {exc}",
                        summary=f"{name} lỗi",
                        artifact=None,
                    )

                yield {"type": "tool_result", "name": name, "summary": result.summary}

                if result.artifact:
                    yield {"type": "artifact", **result.artifact}

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result.content,
                })
        else:
            yield {
                "type": "status",
                "text": f"Đã chạm giới hạn {MAX_ITERATIONS} vòng, dừng và trả kết quả hiện có.",
            }
    except Exception as exc:
        yield {"type": "error", "message": str(exc)}

    yield {"type": "done", "iterations": iterations}


def run(message: str, client=None) -> dict:
    """Bản đồng bộ của run_stream — dùng cho eval. Cùng một logic."""
    trace, artifacts, error, iterations = [], {}, None, 0

    for event in run_stream(message, client=client):
        trace.append(event)
        if event["type"] == "artifact":
            artifacts[event["kind"]] = event
        elif event["type"] == "error":
            error = event["message"]
        elif event["type"] == "done":
            iterations = event["iterations"]

    return {
        "trace": trace,
        "artifacts": artifacts,
        "error": error,
        "iterations": iterations,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_agent.py -v`
Expected: 8 passed

- [ ] **Step 5: Run the whole suite**

Run: `pytest -v`
Expected: all tests from Tasks 2-5 pass (37 total: 6 + 8 + 15 + 8)

- [ ] **Step 6: Commit**

```bash
git add codebase/agent.py codebase/tests/test_agent.py
git commit -m "feat: add streaming agent loop with iteration cap and error containment"
```

---

### Task 6: FastAPI server with SSE

**Files:**
- Create: `codebase/server.py`
- Create: `codebase/tests/test_server.py`

**Interfaces:**
- Consumes: `agent.run_stream`, `tools.load_document`, `tools.get_page_count`, `tts.AUDIO_DIR`
- Produces:
  - `GET /health` → `{"status": "ok", "page_count": int, "pdf": str}`
  - `POST /api/agent` body `{"message": str}` → `text/event-stream` of `data: {json}\n\n`
  - `GET /audio/{filename}` → MP3 file response
  - `PDF_PATH: str` module constant
  - `app: FastAPI`

- [ ] **Step 1: Write the failing test**

Create `codebase/tests/test_server.py`:

```python
import json

import pytest
from fastapi.testclient import TestClient

import server


@pytest.fixture
def client():
    with TestClient(server.app) as c:
        yield c


def _parse_sse(body: str) -> list[dict]:
    """Tách body SSE thành danh sách event dict."""
    return [
        json.loads(part[len("data: "):])
        for part in body.split("\n\n")
        if part.startswith("data: ")
    ]


def test_health_reports_real_page_count(client):
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert data["page_count"] > 0


def test_agent_endpoint_returns_event_stream_content_type(client, monkeypatch):
    monkeypatch.setattr(server.agent, "run_stream",
                        lambda m, **kw: iter([{"type": "done", "iterations": 1}]))
    res = client.post("/api/agent", json={"message": "xin chào"})
    assert res.headers["content-type"].startswith("text/event-stream")


def test_agent_endpoint_streams_every_event(client, monkeypatch):
    scripted = [
        {"type": "status", "text": "bắt đầu"},
        {"type": "tool_call", "name": "list_pages", "args": {}},
        {"type": "done", "iterations": 1},
    ]
    monkeypatch.setattr(server.agent, "run_stream", lambda m, **kw: iter(scripted))

    res = client.post("/api/agent", json={"message": "bất kỳ"})
    assert _parse_sse(res.text) == scripted


def test_vietnamese_is_not_escaped_in_the_stream(client, monkeypatch):
    monkeypatch.setattr(server.agent, "run_stream",
                        lambda m, **kw: iter([{"type": "message", "content": "Tiếng Việt có dấu"}]))
    res = client.post("/api/agent", json={"message": "x"})
    assert "Tiếng Việt có dấu" in res.text
    assert "\\u" not in res.text


def test_agent_crash_becomes_an_error_event_not_a_500(client, monkeypatch):
    def exploding(message, **kwargs):
        raise RuntimeError("hỏng giữa chừng")
        yield  # pragma: no cover — biến hàm thành generator

    monkeypatch.setattr(server.agent, "run_stream", exploding)

    res = client.post("/api/agent", json={"message": "x"})
    events = _parse_sse(res.text)
    assert events[-1]["type"] == "error"
    assert "hỏng giữa chừng" in events[-1]["message"]


def test_missing_audio_file_returns_404(client):
    assert client.get("/audio/khong-ton-tai.mp3").status_code == 404


def test_audio_route_rejects_path_traversal(client):
    assert client.get("/audio/..%2F..%2Fserver.py").status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_server.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server'`

- [ ] **Step 3: Write the implementation**

Create `codebase/server.py`:

```python
"""Tầng HTTP mỏng bọc quanh agent.

Chỉ MỘT endpoint làm việc thật (/api/agent) vì nút bấm và chat đi chung một
đường. Ba tính năng summary/mindmap/audio là tool BÊN TRONG agent, không phải
endpoint riêng.
"""
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import agent
import tools
import tts

load_dotenv()

PDF_PATH = "../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf"

app = FastAPI(title="VLearn AI Study Agent")

# Frontend là file HTML mở trực tiếp (origin null) nên phải mở CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgentRequest(BaseModel):
    message: str


@app.on_event("startup")
def startup() -> None:
    """Kiểm key và nạp PDF ngay lúc khởi động.

    Thiếu ELEVENLABS_API_KEY đặc biệt hiểm: summary và mind map vẫn chạy ngon,
    chỉ vỡ đúng lúc bấm nút Audio giữa demo. Nên chặn ngay từ đây.
    """
    missing = [
        name for name in ("OPENAI_API_KEY", "ELEVENLABS_API_KEY")
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(
            f"Thiếu biến môi trường: {', '.join(missing)}. "
            f"Sao chép .env.example thành .env và điền key."
        )

    tools.load_document(PDF_PATH)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "page_count": tools.get_page_count(), "pdf": PDF_PATH}


@app.post("/api/agent")
def api_agent(req: AgentRequest) -> StreamingResponse:
    def event_stream():
        try:
            for event in agent.run_stream(req.message):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            # Không bắt ở đây thì stream đứt im lặng và frontend treo loading mãi.
            payload = json.dumps(
                {"type": "error", "message": str(exc)}, ensure_ascii=False
            )
            yield f"data: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/audio/{filename}")
def serve_audio(filename: str) -> FileResponse:
    # Chỉ nhận tên file trần — chặn ../ đi ra ngoài audio_output/
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(404, "Không tìm thấy file audio")

    path = tts.AUDIO_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Không tìm thấy file audio")

    return FileResponse(path, media_type="audio/mpeg")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_server.py -v`
Expected: 7 passed

Note: these tests need `OPENAI_API_KEY` and `ELEVENLABS_API_KEY` present in `.env` because `TestClient` as a context manager triggers the startup event. They do not make any API call.

- [ ] **Step 5: Start the server and check it live**

Run: `uvicorn server:app --reload --port 8000`

In another terminal:

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","page_count":<N>,"pdf":"../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf"}`

- [ ] **Step 6: Make one real end-to-end agent call**

```bash
curl -N -X POST http://localhost:8000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"message":"Tóm tắt tài liệu này giúp tôi"}'
```

Expected: `data: {...}` lines appear **progressively**, not all at once — that is the proof SSE is streaming. You should see `status`, then `tool_call`/`tool_result` for `list_pages` and `read_pages`, then an `artifact` with `"kind":"summary"`, then `done`.

The `-N` flag disables curl's buffering; without it you will see everything arrive at the end and wrongly conclude streaming is broken.

- [ ] **Step 7: Commit**

```bash
git add codebase/server.py codebase/tests/test_server.py
git commit -m "feat: add FastAPI server streaming agent events over SSE"
```

---

### Task 7: Frontend — SSE client and output panel

**Files:**
- Modify: `vlearn_clone.html` (repo root)

**Interfaces:**
- Consumes: `GET /health`, `POST /api/agent` (SSE), `GET /audio/{filename}`
- Produces: no code interface — this is the end-user surface

- [ ] **Step 1: Widen the sidebar**

In `vlearn_clone.html:27`, change:

```css
      --sidebar-w: 280px;
```

to:

```css
      --sidebar-w: 420px;
```

280px is too narrow to read a mind map. 420px plus markmap's built-in pan/zoom is usable, and Step 4 adds a full-screen toggle for the demo.

- [ ] **Step 2: Add the new CSS**

Insert immediately before the closing `</style>` tag (`vlearn_clone.html:180`):

```css
    /* --- Agent UI --- */
    .action-buttons { display: flex; gap: 6px; padding: 8px 12px; border-bottom: 1px solid var(--gray-200); flex-shrink: 0; }
    .action-btn { flex: 1; height: 30px; border-radius: 6px; border: 1px solid var(--gray-200); background: var(--white); color: var(--gray-700); font-size: 11.5px; font-family: 'Inter', sans-serif; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px; }
    .action-btn:hover:not(:disabled) { background: var(--blue-light); border-color: var(--blue-primary); color: var(--blue-primary); }
    .action-btn:disabled { opacity: .5; cursor: not-allowed; }

    .trace-panel { padding: 6px 12px; background: var(--gray-50); border-bottom: 1px solid var(--gray-200); font-size: 10.5px; color: var(--gray-600); max-height: 110px; overflow-y: auto; flex-shrink: 0; }
    .trace-panel:empty { display: none; }
    .trace-line { padding: 1px 0; display: flex; gap: 5px; }
    .trace-line .tick { color: var(--green); }

    .output-panel { display: none; flex-direction: column; border-bottom: 1px solid var(--gray-200); flex-shrink: 0; background: var(--white); }
    .output-panel.open { display: flex; }
    .output-panel.expanded { position: fixed; inset: 0; z-index: 500; border: none; }
    .tab-bar { display: flex; gap: 2px; padding: 6px 8px 0; border-bottom: 1px solid var(--gray-200); align-items: center; }
    .tab { height: 26px; padding: 0 8px; border: none; background: transparent; border-radius: 6px 6px 0 0; font-size: 11.5px; font-family: 'Inter', sans-serif; color: var(--gray-500); cursor: pointer; }
    .tab.active { background: var(--blue-light); color: var(--blue-primary); font-weight: 600; }
    .tab-spacer { margin-left: auto; }
    .tab-content { display: none; padding: 10px 12px; overflow: auto; height: 320px; font-size: 12px; line-height: 1.55; }
    .output-panel.expanded .tab-content { height: calc(100vh - 40px); }
    .tab-content.active { display: block; }
    .tab-content h1, .tab-content h2, .tab-content h3 { font-size: 13px; margin: 8px 0 4px; }
    .tab-content ul { padding-left: 18px; }
    .tab-content code { background: var(--gray-100); padding: 1px 4px; border-radius: 3px; }
    #mindmapSvg { width: 100%; height: 100%; }
    .issue-banner { background: #fef3c7; border: 1px solid #fbbf24; color: #92400e; padding: 6px 8px; border-radius: 6px; font-size: 11px; margin-bottom: 8px; }
    .audio-script { margin-top: 10px; font-size: 11.5px; color: var(--gray-600); white-space: pre-wrap; }
    .error-box { background: #fee2e2; border: 1px solid #fca5a5; color: #991b1b; padding: 8px 10px; border-radius: 6px; font-size: 11.5px; }
```

- [ ] **Step 3: Add the CDN scripts**

Insert immediately before the closing `</head>` tag (`vlearn_clone.html:181`):

```html
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.16"></script>
```

- [ ] **Step 4: Add the action buttons, trace panel and output panel**

In `vlearn_clone.html`, find the context bar line (`vlearn_clone.html:287`):

```html
    <div class="context-bar">Ngu canh: <span>Slide trang 1</span></div>
```

Insert immediately **after** it:

```html
    <div class="action-buttons">
      <button class="action-btn" id="btnSummary" onclick="runAction('summary')">📝 Tóm tắt</button>
      <button class="action-btn" id="btnMindmap" onclick="runAction('mindmap')">🧠 Mind Map</button>
      <button class="action-btn" id="btnAudio" onclick="runAction('audio')">🎧 Audio</button>
    </div>
    <div class="trace-panel" id="tracePanel"></div>
    <div class="output-panel" id="outputPanel">
      <div class="tab-bar">
        <button class="tab active" data-tab="summary" onclick="showTab('summary')">📝 Tóm tắt</button>
        <button class="tab" data-tab="mindmap" onclick="showTab('mindmap')">🧠 Mind Map</button>
        <button class="tab" data-tab="audio" onclick="showTab('audio')">🎧 Audio</button>
        <span class="tab-spacer"></span>
        <button class="tab" onclick="toggleExpand()" title="Phóng to / thu nhỏ">⛶</button>
      </div>
      <div class="tab-content active" id="tab-summary"></div>
      <div class="tab-content" id="tab-mindmap">
        <svg id="mindmapSvg"></svg>
      </div>
      <div class="tab-content" id="tab-audio">
        <audio id="audioPlayer" controls style="width:100%"></audio>
        <div class="audio-script" id="audioScript"></div>
      </div>
    </div>
```

- [ ] **Step 5: Replace the mock JavaScript**

In `vlearn_clone.html`, delete lines 334-361 — the `replies` array, `let ri = 0;`, and the entire mock `sendMessage()` function. Keep `toggleSidebar`, `setMode`, `zoomIn`, `zoomOut`, `updatePageInfo`, `nextPage`, `prevPage`, `handleKey` and `autoResize` exactly as they are.

In their place, insert:

```javascript
  // ---------- Agent client ----------
  const API_BASE = 'http://localhost:8000';

  // Ba nút chỉ là shortcut bơm câu tiếng Việt cố định vào CÙNG agent loop
  // mà ô chat dùng — không có endpoint riêng cho từng tính năng.
  const PRESETS = {
    summary: 'Tóm tắt tài liệu này, mỗi ý ghi rõ nguồn trang.',
    mindmap: 'Vẽ sơ đồ tư duy cho toàn bộ tài liệu này.',
    audio:   'Viết script podcast ngắn cho tài liệu này rồi đọc thành audio.',
  };

  let busy = false;

  function setBusy(state) {
    busy = state;
    ['btnSummary', 'btnMindmap', 'btnAudio'].forEach(id => {
      document.getElementById(id).disabled = state;
    });
  }

  function showTab(name) {
    document.querySelectorAll('.tab[data-tab]').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === name);
    });
    document.querySelectorAll('.tab-content').forEach(c => {
      c.classList.toggle('active', c.id === 'tab-' + name);
    });
    document.getElementById('outputPanel').classList.add('open');
  }

  function toggleExpand() {
    document.getElementById('outputPanel').classList.toggle('expanded');
  }

  function addTrace(text, done) {
    const panel = document.getElementById('tracePanel');
    const line = document.createElement('div');
    line.className = 'trace-line';
    line.innerHTML = (done ? '<span class="tick">✓</span>' : '<span>⋯</span>')
                   + '<span>' + text.replace(/</g, '&lt;') + '</span>';
    panel.appendChild(line);
    panel.scrollTop = panel.scrollHeight;
    return line;
  }

  function addBubble(html, who) {
    const c = document.getElementById('chatMessages');
    const wrap = document.createElement('div');
    if (who === 'user') {
      wrap.style.cssText = 'display:flex;flex-direction:column;align-items:flex-end';
      wrap.innerHTML = '<div class="msg-bubble msg-user">' + html + '</div>'
                     + '<div class="msg-time right">Ban · vua xong</div>';
    } else {
      wrap.innerHTML = '<div class="msg-bubble msg-bot">' + html + '</div>'
                     + '<div class="msg-time">VLearn Tutor · vua xong</div>';
    }
    c.appendChild(wrap);
    c.scrollTop = c.scrollHeight;
    return wrap;
  }

  function renderArtifact(ev) {
    if (ev.kind === 'summary') {
      document.getElementById('tab-summary').innerHTML = marked.parse(ev.content);
      showTab('summary');

    } else if (ev.kind === 'mindmap') {
      const box = document.getElementById('tab-mindmap');
      const warning = (ev.issues && ev.issues.length)
        ? '<div class="issue-banner">⚠ ' + ev.issues.join('<br>⚠ ') + '</div>'
        : '';

      // Nếu markmap (CDN) hỏng hoặc không render được, vẫn phải thấy nội dung.
      // Outline markdown thô đọc được bằng mắt — degrade gracefully thay vì
      // để trống màn hình giữa lúc demo.
      const fallback = '<pre style="white-space:pre-wrap;font-size:11.5px">'
                     + ev.content.replace(/</g, '&lt;') + '</pre>';

      try {
        if (!window.markmap || !window.markmap.autoLoader) {
          throw new Error('markmap chưa nạp được từ CDN');
        }
        // markmap-autoloader quét và render các thẻ .markmap
        box.innerHTML = warning + '<div class="markmap"><script type="text/template">'
                      + ev.content + '<\/script></div>';
        window.markmap.autoLoader.renderAll();
      } catch (err) {
        console.warn('markmap hỏng, dùng outline thô:', err);
        box.innerHTML = warning + fallback;
      }
      showTab('mindmap');

    } else if (ev.kind === 'audio') {
      document.getElementById('audioPlayer').src = API_BASE + ev.url;
      document.getElementById('audioScript').textContent = ev.script || '';
      showTab('audio');
    }
  }

  function handleEvent(ev) {
    if (ev.type === 'status') {
      addTrace(ev.text, false);

    } else if (ev.type === 'tool_call') {
      addTrace(ev.name + '(' + JSON.stringify(ev.args).slice(0, 60) + ')', false);

    } else if (ev.type === 'tool_result') {
      addTrace(ev.summary, true);

    } else if (ev.type === 'artifact') {
      renderArtifact(ev);

    } else if (ev.type === 'message') {
      addBubble(marked.parse(ev.content || ''), 'bot');

    } else if (ev.type === 'error') {
      addBubble('<div class="error-box">Lỗi: '
                + String(ev.message).replace(/</g, '&lt;') + '</div>', 'bot');

    } else if (ev.type === 'done') {
      setBusy(false);
    }
  }

  async function askAgent(message) {
    if (busy) return;
    setBusy(true);
    document.getElementById('tracePanel').innerHTML = '';

    let res;
    try {
      res = await fetch(API_BASE + '/api/agent', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message}),
      });
    } catch (err) {
      addBubble('<div class="error-box">Không kết nối được backend. '
              + 'Đã chạy <code>uvicorn server:app --port 8000</code> chưa?</div>', 'bot');
      setBusy(false);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, {stream: true});

      // Chunk mạng KHÔNG trùng ranh giới event: một event có thể bị cắt làm
      // đôi giữa hai chunk, hoặc ba event về chung một chunk. Nên phải tích
      // buffer, tách theo '\n\n', và luôn giữ lại phần tử cuối vì nó có thể
      // còn dở. JSON.parse thẳng từng chunk sẽ vỡ ngẫu nhiên.
      const parts = buffer.split('\n\n');
      buffer = parts.pop();

      for (const part of parts) {
        if (!part.startsWith('data: ')) continue;
        try {
          handleEvent(JSON.parse(part.slice(6)));
        } catch (err) {
          console.error('Event hỏng:', part, err);
        }
      }
    }

    setBusy(false);  // phòng khi stream đứt mà chưa kịp nhận event 'done'
  }

  function runAction(kind) {
    addBubble(PRESETS[kind], 'user');
    askAgent(PRESETS[kind]);
  }

  function sendMessage() {
    const inp = document.getElementById('chatInput');
    const txt = inp.value.trim();
    if (!txt || busy) return;
    inp.value = '';
    inp.style.height = 'auto';
    addBubble(txt.replace(/</g, '&lt;'), 'user');
    askAgent(txt);
  }

  // Lấy số trang thật từ backend thay vì hardcode.
  window.addEventListener('load', async () => {
    try {
      const health = await (await fetch(API_BASE + '/health')).json();
      totalPages = health.page_count;
      updatePageInfo();
    } catch (err) {
      console.warn('Backend chưa chạy, giữ số trang mặc định.');
    }
  });
```

- [ ] **Step 6: Verify the three buttons end to end**

Start the backend (`uvicorn server:app --reload --port 8000` from `codebase/`), then open `vlearn_clone.html` in a browser.

Check each:
1. Page loads → `Trang 1 / <N>` shows the **real** page count from `/health`, not 44.
2. Click **📝 Tóm tắt** → trace lines appear one by one (not all at once), Summary tab fills with Vietnamese markdown containing `[Tr.N]` references.
3. Click **🧠 Mind Map** → markmap renders an interactive tree. Drag to pan, scroll to zoom. Click ⛶ to expand full screen.
4. Click **🎧 Audio** → audio player appears, press play, Vietnamese speech is audible. **This is the one real ElevenLabs call in this task — do not repeat it more than necessary.**
5. Type `Tóm tắt rồi vẽ sơ đồ luôn` in chat → trace shows `read_pages` called **once**, then both `emit_summary` and `emit_mindmap`. This is the tool-chaining proof.

If trace lines all appear simultaneously at the end, SSE is not streaming — check that `event_stream` in `server.py` is a generator (has `yield`, not `return`).

- [ ] **Step 7: Verify failure behaviour**

Stop the backend, reload the page, click 📝 Tóm tắt.
Expected: red error box saying the backend is not reachable. Buttons re-enable — they do not stay stuck disabled.

- [ ] **Step 8: Commit**

```bash
git add vlearn_clone.html
git commit -m "feat: wire VLearn UI to streaming agent with live trace and 3 output tabs"
```

---

### Task 8: Evaluation harness

**Files:**
- Create: `eval/golden_set.json` (repo root, not under `codebase/`)
- Create: `eval/run_eval.py`
- Create: `codebase/tests/test_eval_checks.py`

**Interfaces:**
- Consumes: `agent.run`, `tools.load_document`
- Produces:
  - `eval/run_eval.py` with `CHECKS: dict[str, Callable[[dict], tuple[bool, str]]]` mapping check name → function taking an `agent.run` result and returning `(passed, detail)`
  - `eval/results-<timestamp>.md` written on each run

- [ ] **Step 1: Create `eval/golden_set.json`**

```json
[
  {
    "id": "S01",
    "message": "Tóm tắt tài liệu này giúp tôi",
    "checks": ["no_error", "summary_nonempty", "summary_has_citation", "within_iteration_limit"]
  },
  {
    "id": "S02",
    "message": "Cho tôi các ý chính của bài giảng dưới dạng gạch đầu dòng",
    "checks": ["no_error", "summary_nonempty", "summary_has_citation", "within_iteration_limit"]
  },
  {
    "id": "M01",
    "message": "Vẽ sơ đồ tư duy cho toàn bộ tài liệu",
    "checks": ["no_error", "mindmap_pages_valid", "mindmap_min_branches_3", "mindmap_max_depth_4", "within_iteration_limit"]
  },
  {
    "id": "M02",
    "message": "Lập bản đồ khái niệm của bài này, mỗi node ghi rõ trang",
    "checks": ["no_error", "mindmap_pages_valid", "mindmap_min_branches_3", "within_iteration_limit"]
  },
  {
    "id": "C01",
    "message": "Tóm tắt rồi vẽ sơ đồ luôn",
    "checks": ["no_error", "summary_nonempty", "mindmap_pages_valid", "single_read_pass", "within_iteration_limit"]
  },
  {
    "id": "C02",
    "message": "Tôi muốn vừa có bản tóm tắt vừa có sơ đồ tư duy của tài liệu",
    "checks": ["no_error", "summary_nonempty", "mindmap_pages_valid", "within_iteration_limit"]
  },
  {
    "id": "A01",
    "message": "Đọc tóm tắt tài liệu này thành podcast cho tôi nghe",
    "checks": ["no_error", "audio_generated", "audio_script_has_no_page_markers", "within_iteration_limit"]
  },
  {
    "id": "E01",
    "message": "Tóm tắt trang 999 của tài liệu",
    "checks": ["no_error", "within_iteration_limit"]
  },
  {
    "id": "E02",
    "message": "Giải thích định lý Pythagore trong tài liệu này",
    "checks": ["no_error", "within_iteration_limit", "no_fabricated_summary_pages"]
  },
  {
    "id": "E03",
    "message": "Tài liệu này có bao nhiêu trang và nói về chủ đề gì?",
    "checks": ["no_error", "within_iteration_limit"]
  }
]
```

Only **A01** touches audio. That is deliberate: ElevenLabs free tier is ~10,000 credits/month at ~1 credit per character, and one podcast script is ~2,000-3,000 characters. Ten audio cases would exhaust a month's quota in a single run.

- [ ] **Step 2: Write the failing test for the check functions**

Create `codebase/tests/test_eval_checks.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))

from run_eval import CHECKS  # noqa: E402


def _result(artifacts=None, error=None, iterations=2, trace=None):
    return {
        "artifacts": artifacts or {},
        "error": error,
        "iterations": iterations,
        "trace": trace or [],
    }


def test_no_error_passes_when_error_is_none():
    passed, _ = CHECKS["no_error"](_result())
    assert passed


def test_no_error_fails_when_error_present():
    passed, detail = CHECKS["no_error"](_result(error="API sập"))
    assert not passed
    assert "API sập" in detail


def test_summary_nonempty_requires_100_chars():
    short = {"summary": {"content": "ngắn"}}
    assert not CHECKS["summary_nonempty"](_result(short))[0]

    long = {"summary": {"content": "x" * 150}}
    assert CHECKS["summary_nonempty"](_result(long))[0]


def test_summary_has_citation_looks_for_page_marker():
    assert CHECKS["summary_has_citation"](_result({"summary": {"content": "Ý A [Tr.3]"}}))[0]
    assert not CHECKS["summary_has_citation"](_result({"summary": {"content": "Ý A"}}))[0]


def test_mindmap_pages_valid_fails_on_invalid_pages():
    bad = {"mindmap": {"content": "# A", "invalid_pages": [999], "issues": ["x"]}}
    passed, detail = CHECKS["mindmap_pages_valid"](_result(bad))
    assert not passed
    assert "999" in detail


def test_mindmap_min_branches_reads_precomputed_count():
    three = {"mindmap": {"branch_count": 3, "invalid_pages": []}}
    assert CHECKS["mindmap_min_branches_3"](_result(three))[0]

    two = {"mindmap": {"branch_count": 2, "invalid_pages": []}}
    assert not CHECKS["mindmap_min_branches_3"](_result(two))[0]


def test_mindmap_max_depth_reads_precomputed_depth():
    ok = {"mindmap": {"max_depth": 4, "invalid_pages": []}}
    assert CHECKS["mindmap_max_depth_4"](_result(ok))[0]

    deep = {"mindmap": {"max_depth": 5, "invalid_pages": []}}
    assert not CHECKS["mindmap_max_depth_4"](_result(deep))[0]


def test_audio_script_must_not_contain_page_markers():
    clean = {"audio": {"script": "Xin chào các bạn.", "url": "/audio/x.mp3"}}
    assert CHECKS["audio_script_has_no_page_markers"](_result(clean))[0]

    dirty = {"audio": {"script": "Xin chào [Tr.3].", "url": "/audio/x.mp3"}}
    assert not CHECKS["audio_script_has_no_page_markers"](_result(dirty))[0]


def test_single_read_pass_counts_read_pages_calls():
    once = [{"type": "tool_call", "name": "read_pages", "args": {}}]
    assert CHECKS["single_read_pass"](_result(trace=once))[0]

    twice = once * 2
    assert not CHECKS["single_read_pass"](_result(trace=twice))[0]


def test_within_iteration_limit_fails_at_the_cap():
    import agent
    assert not CHECKS["within_iteration_limit"](_result(iterations=agent.MAX_ITERATIONS))[0]
    assert CHECKS["within_iteration_limit"](_result(iterations=3))[0]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_eval_checks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'run_eval'`

- [ ] **Step 4: Write `eval/run_eval.py`**

```python
"""Chạy golden set qua agent và in bảng pass/fail.

Chỉ kiểm những thứ MÁY tự kiểm được — cấu trúc và tính hợp lệ của trích dẫn
trang. Không kiểm "tóm tắt hay dở"; việc đó cần người và không nhét vào vòng
lặp tự động được.

Mặc định TTS_MODE=stub để không đốt quota ElevenLabs. Muốn nghe thật:
    TTS_MODE=real python eval/run_eval.py
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codebase"))

# Phải đặt TRƯỚC khi import tts (qua tools) để module đọc đúng giá trị.
os.environ.setdefault("TTS_MODE", "stub")

import agent      # noqa: E402
import tools      # noqa: E402

PDF_PATH = str(ROOT / "HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf")
GOLDEN_SET = Path(__file__).parent / "golden_set.json"

_PAGE_REF = re.compile(r"\[Tr\.(\d+)\]")


def _tool_calls(result: dict, name: str) -> int:
    return sum(
        1 for e in result["trace"]
        if e.get("type") == "tool_call" and e.get("name") == name
    )


# --- Các phép kiểm: nhận kết quả agent.run, trả (passed, detail) ---

def check_no_error(r):
    return (r["error"] is None), (r["error"] or "không có lỗi")


def check_summary_nonempty(r):
    content = r["artifacts"].get("summary", {}).get("content", "")
    return len(content) >= 100, f"{len(content)} ký tự"


def check_summary_has_citation(r):
    content = r["artifacts"].get("summary", {}).get("content", "")
    refs = _PAGE_REF.findall(content)
    return bool(refs), f"{len(refs)} trích dẫn trang"


def check_mindmap_pages_valid(r):
    mm = r["artifacts"].get("mindmap")
    if not mm:
        return False, "không có mind map"
    invalid = mm.get("invalid_pages", [])
    return not invalid, (f"trang không hợp lệ: {invalid}" if invalid else "mọi trang hợp lệ")


def check_mindmap_min_branches_3(r):
    # Đọc số đã tính sẵn trong artifact — guard ở tools.validate_mindmap là
    # nguồn sự thật duy nhất, eval không parse markdown lần thứ hai.
    mm = r["artifacts"].get("mindmap")
    if not mm:
        return False, "không có mind map"
    n = mm.get("branch_count", 0)
    return n >= 3, f"{n} nhánh chính"


def check_mindmap_max_depth_4(r):
    mm = r["artifacts"].get("mindmap")
    if not mm:
        return False, "không có mind map"
    d = mm.get("max_depth", 0)
    return d <= 4, f"sâu {d} cấp"


def check_audio_generated(r):
    au = r["artifacts"].get("audio")
    if not au:
        return False, "không có audio"
    return bool(au.get("url")), f"{au.get('char_count', 0)} ký tự"


def check_audio_script_has_no_page_markers(r):
    au = r["artifacts"].get("audio")
    if not au:
        return False, "không có audio"
    refs = _PAGE_REF.findall(au.get("script", ""))
    return not refs, (f"còn {len(refs)} ký hiệu [Tr.N] trong script" if refs else "script sạch")


def check_single_read_pass(r):
    n = _tool_calls(r, "read_pages")
    return n <= 1, f"gọi read_pages {n} lần"


def check_within_iteration_limit(r):
    return r["iterations"] < agent.MAX_ITERATIONS, f"{r['iterations']} vòng"


def check_no_fabricated_summary_pages(r):
    """Mọi [Tr.N] trong summary phải trỏ tới trang có thật."""
    content = r["artifacts"].get("summary", {}).get("content", "")
    n_pages = tools.get_page_count()
    bad = [int(m) for m in _PAGE_REF.findall(content) if not 1 <= int(m) <= n_pages]
    return not bad, (f"trang bịa: {bad}" if bad else "không có trang bịa")


CHECKS = {
    "no_error": check_no_error,
    "summary_nonempty": check_summary_nonempty,
    "summary_has_citation": check_summary_has_citation,
    "mindmap_pages_valid": check_mindmap_pages_valid,
    "mindmap_min_branches_3": check_mindmap_min_branches_3,
    "mindmap_max_depth_4": check_mindmap_max_depth_4,
    "audio_generated": check_audio_generated,
    "audio_script_has_no_page_markers": check_audio_script_has_no_page_markers,
    "single_read_pass": check_single_read_pass,
    "within_iteration_limit": check_within_iteration_limit,
    "no_fabricated_summary_pages": check_no_fabricated_summary_pages,
}


def main() -> None:
    tools.load_document(PDF_PATH)
    cases = json.loads(GOLDEN_SET.read_text(encoding="utf-8"))

    rows, total, passed_total = [], 0, 0

    for case in cases:
        print(f"[{case['id']}] {case['message']}")
        result = agent.run(case["message"])

        for name in case["checks"]:
            passed, detail = CHECKS[name](result)
            total += 1
            passed_total += passed
            rows.append((case["id"], name, passed, detail))
            print(f"    {'PASS' if passed else 'FAIL'}  {name}: {detail}")

    pct = (100 * passed_total / total) if total else 0
    print(f"\nTổng: {passed_total}/{total} ({pct:.1f}%)")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(__file__).parent / f"results-{stamp}.md"
    lines = [
        f"# Kết quả eval — {stamp}",
        "",
        f"TTS_MODE = `{os.environ['TTS_MODE']}` · model = `{agent.MODEL}`",
        "",
        f"**Tổng: {passed_total}/{total} ({pct:.1f}%)**",
        "",
        "| Case | Phép kiểm | Kết quả | Chi tiết |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {cid} | {name} | {'PASS' if ok else 'FAIL'} | {detail} |"
        for cid, name, ok, detail in rows
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Đã ghi {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the check-function tests**

Run: `pytest tests/test_eval_checks.py -v`
Expected: 10 passed

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: all 54 tests pass (6 + 8 + 15 + 8 + 7 + 10)

- [ ] **Step 7: Run the real evaluation**

From the repo root: `python eval/run_eval.py`

Expected: ten cases run against the real OpenAI API, a pass/fail line per check, a total percentage, and `eval/results-<timestamp>.md` written.

This costs OpenAI tokens but **zero ElevenLabs credits** because `TTS_MODE` defaults to `stub`.

Do not tune the checks to make failures disappear. A failing check is information — record it. If a check is wrong (it tests something the design never promised), fix the check and say so. If the agent is wrong, that is a real finding for the demo.

- [ ] **Step 8: Commit**

```bash
git add eval/golden_set.json eval/run_eval.py eval/results-*.md \
        codebase/tests/test_eval_checks.py
git commit -m "feat: add evaluation harness with machine-verifiable checks"
```

---

## Post-Implementation Verification

- [ ] `pytest -v` from `codebase/` — all tests pass
- [ ] `uvicorn server:app --port 8000` starts and `/health` returns the real page count
- [ ] All three buttons work in the browser against a live backend
- [ ] Trace lines appear **progressively**, proving SSE streams rather than buffers
- [ ] `Tóm tắt rồi vẽ sơ đồ luôn` produces both artifacts from a single `read_pages` call
- [ ] Audio plays and the Vietnamese is intelligible
- [ ] `python eval/run_eval.py` completes and writes a results file
- [ ] `git status` shows no `.env` and no `.mp3` staged
