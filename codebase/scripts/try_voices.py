"""Nghe thử giọng tiếng Việt của ElevenLabs bằng câu NGẮN.

Vì sao câu ngắn: free tier ~10.000 credit/tháng, ~1 credit/ký tự.
Câu test dưới đây ~90 ký tự, thử 3 giọng hết ~270 credit.
Dùng nguyên script podcast (~3.000 ký tự) để thử giọng sẽ đốt sạch quota.

Chạy:  python scripts/try_voices.py <voice_id> [<voice_id> ...]
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

# Câu test có dấu đầy đủ, có số, có thuật ngữ tiếng Anh xen kẽ —
# đúng kiểu câu sẽ xuất hiện trong podcast thật.
SAMPLE = "Xin chào, đây là bản tóm tắt bài giảng day 2, phần giao diện người dùng, trang 12."

OUT_DIR = Path(__file__).parent.parent / "audio_output" / "voice_test"


def main(voice_ids: list[str]) -> None:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit("Thiếu ELEVENLABS_API_KEY trong .env")

    client = ElevenLabs(api_key=api_key)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for voice_id in voice_ids:
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            model_id="eleven_turbo_v2_5",
            text=SAMPLE,
            output_format="mp3_44100_128",
        )
        path = OUT_DIR / f"{voice_id}.mp3"
        with open(path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        print(f"{voice_id} -> {path}  ({len(SAMPLE)} ký tự)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
