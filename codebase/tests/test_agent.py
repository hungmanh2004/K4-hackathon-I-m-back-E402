import json
from types import SimpleNamespace

import pytest

import agent
import tools

PDF = "../data/vlearn-pack/slides/d2-slide-hackathon.pdf"


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
