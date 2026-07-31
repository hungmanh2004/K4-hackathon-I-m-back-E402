import pytest

import tools

PDF = "../data/vlearn-pack/slides/d2-slide-hackathon.pdf"


@pytest.fixture(autouse=True)
def loaded_document():
    tools.load_document(PDF)


# --- validate_mindmap ---

GOOD_MAP = """# Xác định bài toán AI
- Mô hình Double Diamond ... [Tr.3].
- Sai lầm thường gặp ... [Tr.7].
- Chỉ số đo lường ... [Tr.12].
- Ba mô hình cơ bản: Prompt Chaining, Routing, và Parallelization ... [Tr.20].
- Cây quyết định ... [Tr.21].
- Reward function ... [Tr.22].
- 6 yếu tố bài toán cốt lõi ... 3 yếu tố quyết định ... [Tr.27].
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


def test_depth_of_exactly_four_passes():
    # 3 nhánh chính để không đụng cảnh báo "quá ít nhánh" — chỉ cô lập biên độ sâu.
    ok = "# A\n## B\n### C\n#### D [Tr.1]\n## E\n### F [Tr.2]\n## G\n### H [Tr.3]\n"
    r = tools.validate_mindmap(ok, n_pages=44)
    assert r["max_depth"] == 4
    assert r["issues"] == []


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
