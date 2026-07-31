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
MAX_HISTORY_MESSAGES = 12  # ~6 lượt gần nhất — đủ ngữ cảnh, không phình token

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
- Bạn có thể được cung cấp lịch sử vài lượt hội thoại gần nhất (trong phiên làm
  việc hiện tại, KHÔNG lưu lại sau khi đóng trình duyệt). Nếu người dùng nhắc
  tới kết quả trước đó ("cũ", "vừa rồi", "bản trên", "chi tiết hơn nữa"), hãy
  đọc lịch sử đó để biết chính xác nội dung cần chỉnh sửa/mở rộng, rồi emit lại
  bản đã cập nhật — đừng tạo lại từ đầu theo hướng chung chung. Nếu lịch sử
  không đủ để xác định người dùng đang nhắc tới cái gì, hỏi lại thay vì đoán.
"""


def _sanitize_history(history: list[dict] | None) -> list[dict]:
    """Lọc lịch sử hội thoại từ client: chỉ giữ role/content hợp lệ, cắt bớt nếu quá dài.

    Lịch sử tới từ trình duyệt (JS, chỉ sống trong tab hiện tại — không DB,
    không đăng nhập, mất khi F5) nên không tin tưởng mù quáng cấu trúc của nó.
    """
    if not history:
        return []
    cleaned = [
        {"role": h["role"], "content": str(h["content"])}
        for h in history
        if isinstance(h, dict)
        and h.get("role") in ("user", "assistant")
        and isinstance(h.get("content"), str)
        and h["content"].strip()
    ]
    return cleaned[-MAX_HISTORY_MESSAGES:]


def run_stream(message: str, client=None, history: list[dict] | None = None) -> Iterator[dict]:
    """Chạy agent, yield từng event một.

    history: vài lượt hội thoại gần nhất trong CÙNG phiên trình duyệt (không
    phải lưu trữ dài hạn — xem non-goal ở spec.md §4), giúp agent hiểu các
    câu tham chiếu kiểu "mind map cũ", "chi tiết hơn nữa" thay vì mỗi lượt
    lại bắt đầu từ con số không.
    """
    client = client or _default_client()
    n_pages = tools.get_page_count()

    messages = [{"role": "system", "content": build_system_prompt(n_pages)}]
    messages.extend(_sanitize_history(history))
    messages.append({"role": "user", "content": message})

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
