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
