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
