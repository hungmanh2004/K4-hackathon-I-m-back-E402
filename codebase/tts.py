"""Sinh audio tiếng Việt bằng ElevenLabs, có cache theo nội dung script.

Vì sao cần cache: free tier ElevenLabs ~10.000 credit/tháng, ~1 credit mỗi
ký tự. Một script podcast tiếng Việt ~2.000-3.000 ký tự, tức cả tháng chỉ
đủ 3-5 lần sinh. Cache theo hash nội dung khiến việc chạy lại cùng một demo
không tốn thêm credit — và là lưới an toàn khi demo live: đã chạy thử trước
thì lúc demo thật là cache hit, không phụ thuộc mạng.
"""
import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MAX_TTS_CHARS = 5000
TTS_MODEL = "eleven_turbo_v2_5"  # KHÔNG dùng eleven_multilingual_v2 — không có tiếng Việt
AUDIO_DIR = Path(__file__).parent / "audio_output"


def truncate_at_sentence(text: str, max_chars: int) -> tuple[str, bool]:
    """Cắt text về <= max_chars, ưu tiên dừng ở cuối câu.

    Trả về (text_đã_cắt, có_bị_cắt_không). Không bao giờ cắt giữa từ nếu
    tìm được dấu chấm; nếu không có dấu chấm nào trong giới hạn thì cắt cứng.
    """
    if len(text) <= max_chars:
        return text, False

    window = text[:max_chars]
    cut = max(window.rfind("."), window.rfind("!"), window.rfind("?"))
    if cut > 0:
        return window[: cut + 1], True
    return window, True


def audio_path_for(script: str) -> Path:
    """Đường dẫn file mp3 suy ra từ nội dung script — cùng script, cùng file."""
    key = hashlib.sha256(script.encode("utf-8")).hexdigest()[:16]
    return AUDIO_DIR / f"{key}.mp3"


def _call_elevenlabs(script: str, path: Path) -> None:
    """Gọi API thật và ghi ra file.

    Tách riêng thành hàm để test có thể monkeypatch, xác nhận cache hit
    KHÔNG chạm tới API.
    """
    from elevenlabs.client import ElevenLabs

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    if not api_key:
        raise RuntimeError("Thiếu ELEVENLABS_API_KEY")
    if not voice_id:
        raise RuntimeError("Thiếu ELEVENLABS_VOICE_ID (chốt ở Task 1)")

    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=TTS_MODEL,
        text=script,
        output_format="mp3_44100_128",
    )

    # ElevenLabs trả generator các chunk bytes — không có stream_to_file()
    # như OpenAI, phải tự gom.
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        for chunk in audio:
            f.write(chunk)


def generate_audio(script: str) -> dict:
    """Sinh mp3 từ script. Trả {filename, char_count, cached, truncated}."""
    script, truncated = truncate_at_sentence(script, MAX_TTS_CHARS)
    path = audio_path_for(script)

    if os.getenv("TTS_MODE", "real") == "stub":
        return {
            "filename": path.name,
            "char_count": len(script),
            "cached": False,
            "truncated": truncated,
        }

    if path.exists():
        return {
            "filename": path.name,
            "char_count": len(script),
            "cached": True,
            "truncated": truncated,
        }

    _call_elevenlabs(script, path)
    return {
        "filename": path.name,
        "char_count": len(script),
        "cached": False,
        "truncated": truncated,
    }
