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
