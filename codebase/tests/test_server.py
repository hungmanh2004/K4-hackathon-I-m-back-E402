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
