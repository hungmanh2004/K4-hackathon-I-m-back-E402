# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is a submission repo for a 1.5-day mini-hackathon ("SPEC → Prototype → Demo") whose deliverable is judged primarily on **decision-making and evidence**, not on how polished the product looks. The event docs (read in this order) define almost every constraint on how work here should proceed:

- `01-de-bai.md` — the assignment: 3 possible tracks (A. VLearn, B. Discord assistant, C. open), and 5 acceptance criteria that apply no matter which track/feature is chosen.
- `02-guide.md` — the 5-phase playbook (discover → spec → build → measure/validate → demo), mapped to 6 checkpoints (CP1-CP6).
- `03-template-ai-spec.md` — the literal template for `spec.md`, the central deliverable (§1-§9).
- `04-rubric.md` — 100-point rubric: 25 pts for on-time checkpoints + 75 pts scored against specific files (`spec.md` sections, `eval/`, `codebase/`, `validation/`, repo structure).
- `implementation_plan.md` — the actual build plan for this team's chosen feature (see Architecture below). Written for an agentic worker using `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**Chosen direction (per `implementation_plan.md`):** Track A (VLearn), building a "VLearn AI Study Agent" — real OpenAI-powered summarize / mind-map / audio-podcast features layered onto the existing `vlearn_clone.html` tutor UI.

## Required submission structure

The rubric scores specific files, so the repo is expected to converge on this shape (some directories don't exist yet — create them as work progresses, don't invent alternate locations):

```
README.md          ← member names + named task assignment
spec.md            ← the AI Spec, per 03-template-ai-spec.md (does not exist yet — central deliverable)
demo-slides.pdf     ← 6-slide deck per 02-guide.md §5.1
codebase/           ← prototype code (mark clearly which parts are mocked)
eval/               ← golden set + run-result tables (does not exist yet)
validation/         ← user-test feedback logs (does not exist yet)
reflection/          ← one file per member
```

`spec.md`'s quality bar is locked once committed (deadline: 23:59 of day 1) and must not change afterward — if you're asked to edit `spec.md` quality-bar numbers after that point, flag it rather than silently complying.

## Data rules (hard constraint, not a style preference)

`data/vlearn-pack/` contains real, anonymized production data (VLearn tutor chat logs, lecture transcripts, slides) licensed only for this hackathon:

- Never commit the data pack (or large verbatim excerpts of it) into files meant for submission — short illustrative quotes only; golden-set cases should cite segment/conversation codes (e.g. `[T04-012]`, `C0123`) instead of pasting long verbatim text.
- Never send more than the minimal necessary slice to external tools/APIs (free-tier LLM APIs may train on submitted data).
- Anonymization codes (`U/C/T/M####`) must not be reverse-engineered.
- `chatlog/chat_history_anonymized_for_hackathon.csv` — see `data/vlearn-pack/chatlog/DATA_DICTIONARY.md` before mining it (field meanings, known-broken columns like `total_cost_usd` which is always 0, `misconceptions`/`follow_ups` which are always empty).
- Full rules: `README.md` §"Bảo mật dữ liệu được cung cấp" and `data/vlearn-pack/README.md`.

## Architecture (per `docs/superpowers/plans/2026-07-30-vlearn-ai-study-agent.md`)

Status: **built**. The original `implementation_plan.md` (per-endpoint sketch) was superseded during build by `docs/superpowers/plans/2026-07-30-vlearn-ai-study-agent.md`, which is what actually shipped — read that plan, not `implementation_plan.md`, for design rationale.

- **Backend** (Python, in `codebase/`): FastAPI app (`server.py`) exposing exactly **one** working feature endpoint, `POST /api/agent` (body `{"message": str}`, streams Server-Sent Events), plus `GET /health` and a static `GET /audio/{filename}` file route. There is no `/api/extract-text`, `/api/summarize`, `/api/mindmap`, `/api/audio`, or `/api/chat` — summary/mind-map/audio are tools the agent calls internally over the one SSE endpoint, not separate REST routes. Backing modules:
  - `pdf_parser.py` — pure text extraction via `pymupdf` (`extract_pages(pdf_path) -> list[dict]`, `page_count(pdf_path) -> int`). No AI, no network.
  - `tools.py` — the agent's five tool implementations (`list_pages`, `read_pages`, `emit_summary`, `emit_mindmap`, `render_audio`) plus `TOOL_SCHEMAS`, `load_document`, `get_page_count`, `validate_mindmap`, `execute_tool`. Tools are pure data plumbing — no LLM calls inside them.
  - `agent.py` — the one place that calls the LLM: a tool-calling loop (`run_stream`, `run`, `build_system_prompt`) using model `gpt-4o-mini`, `MAX_ITERATIONS = 8`, Vietnamese-language system prompt.
  - `tts.py` — TTS via **ElevenLabs** (`eleven_turbo_v2_5`, NOT `eleven_multilingual_v2` — Vietnamese isn't supported by that model), voice chosen and pinned to `ELEVENLABS_VOICE_ID` during Task 1's voice spike. Content-hash cache keyed off the script text → MP3 files under `codebase/audio_output/`.
  - Config via **two** required env vars: `OPENAI_API_KEY` and `ELEVENLABS_API_KEY` (`.env`, not committed — see `codebase/.env.example`). The server's startup hook refuses to boot if either is missing.
- **Frontend**: `vlearn_clone.html` — upgraded from the original hardcoded/fake `sendMessage()` mock into a real SSE client that streams `POST /api/agent` from `http://localhost:8000`, renders a live tool-call trace, and populates 3 output tabs (Summary / Mind Map / Audio) — mind maps via the `markmap-autoloader` CDN script, summaries and chat replies via `marked.js`.
- No database, no auth, no deployment — this is a local-only demo prototype (`python`/`uvicorn` + open the HTML file in a browser).
- Demo PDF used for the whole flow: `HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf` (already in repo root), referenced from `codebase/` as `../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf`.

## Commands

Backend (from `codebase/`):
```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in OPENAI_API_KEY and ELEVENLABS_API_KEY
uvicorn server:app --reload --port 8000
```

Frontend: open `vlearn_clone.html` directly in a browser (no build step).

Manual smoke test of a module (pattern used throughout the as-executed plan):
```bash
cd codebase
python -c "from pdf_parser import extract_pages; print(extract_pages('../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf')[0])"
```

Test suite (pytest, from `codebase/`):
```bash
pytest -v
```

## Working conventions specific to this repo

- Every prototype tier (Sketch/Mock/Working) requires **at least one real AI API call** — never fully hardcode/mock the central AI decision, and clearly label in `spec.md` §4 which parts *are* mocked.
- Vietnamese is the working/output language throughout (spec sections, AI-facing prompts and their outputs, UI copy) — match existing tone when writing new prompts or spec content.
- Don't add scope beyond the single "lát cắt" (one user · one job · one AI decision · one outcome) defined in `spec.md` §4 — the rubric explicitly penalizes drift from the declared cut, and §4's "non-goals" list is meant to be enforced, not aspirational.
