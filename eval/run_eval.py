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

from dotenv import load_dotenv  # noqa: E402

# agent.py's own load_dotenv() searches upward from the current working
# directory, which is codebase/ when run from there but the repo root when
# invoked as `python eval/run_eval.py`. Load codebase/.env explicitly here
# first so OPENAI_API_KEY / ELEVENLABS_API_KEY are set regardless of cwd.
load_dotenv(ROOT / "codebase" / ".env")

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
