import json
from pathlib import Path

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


def test_agent_endpoint_forwards_history_to_run_stream(client, monkeypatch):
    captured = {}

    def fake_run_stream(message, **kwargs):
        captured["message"] = message
        captured["history"] = kwargs.get("history")
        return iter([{"type": "done", "iterations": 1}])

    monkeypatch.setattr(server.agent, "run_stream", fake_run_stream)

    history = [{"role": "user", "content": "vẽ mind map"}]
    client.post("/api/agent", json={"message": "chi tiết hơn", "history": history})

    assert captured["message"] == "chi tiết hơn"
    assert captured["history"] == history


def test_agent_endpoint_defaults_history_to_empty_list(client, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        server.agent, "run_stream",
        lambda m, **kw: (captured.update(history=kw.get("history")) or iter([{"type": "done", "iterations": 1}])),
    )
    client.post("/api/agent", json={"message": "x"})
    assert captured["history"] == []


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


def test_audio_route_rejects_windows_drive_relative_traversal(client, monkeypatch, tmp_path):
    """Chặn escape kiểu 'C:secret.txt' NGAY CẢ KHI AUDIO_DIR được dựng tương đối.

    Cơ chế lỗi: trên Windows, Path("audio_output") / "C:secret.txt" bỏ qua vế
    trái vì vế phải mang ký tự ổ đĩa — kết quả là "C:secret.txt" (tương đối
    theo thư mục hiện hành của TIẾN TRÌNH trên ổ đó), KHÔNG nằm dưới
    audio_output/. Chuỗi "C:secret.txt" không chứa "/", "\\" hay ".." nên bộ
    lọc substring của bản cũ không bắt được.

    Trong repo thật, tts.AUDIO_DIR = Path(__file__).parent / "audio_output"
    nên LUÔN là đường dẫn tuyệt đối — vì vậy request /audio/C:secret.txt cụ
    thể không rò rỉ gì trên máy phát triển hiện tại (join với vế trái tuyệt
    đối cùng ổ đĩa sẽ được pathlib giữ nguyên, không escape). Nhưng đó là một
    sự trùng hợp của cách AUDIO_DIR được dựng, không phải một chốt chặn có
    chủ đích trong route — nếu AUDIO_DIR từng bị đổi thành tương đối (hoặc
    trên máy có ổ đĩa khác với ổ chứa audio_output), lỗ hổng sẽ lộ ra ngay.
    Test này giả lập đúng kịch bản gốc bằng cách trỏ AUDIO_DIR tới một thư
    mục con TƯƠNG ĐỐI của cwd, để xác nhận route tự nó chặn được bằng
    resolve() + is_relative_to() — không phụ thuộc may rủi vào việc AUDIO_DIR
    có tuyệt đối hay không.
    """
    secret = tmp_path / "secret.txt"
    secret.write_text("BI MAT KHONG DUOC LO RA NGOAI")
    (tmp_path / "audio_output").mkdir()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(server.tts, "AUDIO_DIR", Path("audio_output"))

    drive = tmp_path.drive  # vd "C:" — phải khớp ổ đĩa của tmp_path để escape
    res = client.get(f"/audio/{drive}secret.txt")
    assert res.status_code == 404
