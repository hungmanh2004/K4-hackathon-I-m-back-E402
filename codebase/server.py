"""Tầng HTTP mỏng bọc quanh agent.

Chỉ MỘT endpoint làm việc thật (/api/agent) vì nút bấm và chat đi chung một
đường. Ba tính năng summary/mindmap/audio là tool BÊN TRONG agent, không phải
endpoint riêng.
"""
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import agent
import tools
import tts

load_dotenv()

PDF_PATH = "../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf"

app = FastAPI(title="VLearn AI Study Agent")

# Frontend là file HTML mở trực tiếp (origin null) nên phải mở CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgentRequest(BaseModel):
    message: str


@app.on_event("startup")
def startup() -> None:
    """Kiểm key và nạp PDF ngay lúc khởi động.

    Thiếu ELEVENLABS_API_KEY đặc biệt hiểm: summary và mind map vẫn chạy ngon,
    chỉ vỡ đúng lúc bấm nút Audio giữa demo. Nên chặn ngay từ đây.
    """
    missing = [
        name for name in ("OPENAI_API_KEY", "ELEVENLABS_API_KEY")
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(
            f"Thiếu biến môi trường: {', '.join(missing)}. "
            f"Sao chép .env.example thành .env và điền key."
        )

    tools.load_document(PDF_PATH)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "page_count": tools.get_page_count(), "pdf": PDF_PATH}


@app.post("/api/agent")
def api_agent(req: AgentRequest) -> StreamingResponse:
    def event_stream():
        try:
            for event in agent.run_stream(req.message):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            # Không bắt ở đây thì stream đứt im lặng và frontend treo loading mãi.
            payload = json.dumps(
                {"type": "error", "message": str(exc)}, ensure_ascii=False
            )
            yield f"data: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/audio/{filename}")
def serve_audio(filename: str) -> FileResponse:
    # So khớp bằng is_relative_to() sau resolve() thay vì lọc chuỗi con —
    # trên Windows, Path("audio_output") / "C:.env" bỏ qua vế trái vì vế phải
    # mang ký tự ổ đĩa, nên "C:.env" (không chứa "/", "\\" hay "..") có thể
    # thoát khỏi audio_output/ nếu chỉ chặn bằng substring.
    audio_dir = tts.AUDIO_DIR.resolve()
    path = (audio_dir / filename).resolve()
    if not path.is_relative_to(audio_dir) or not path.is_file():
        raise HTTPException(404, "Không tìm thấy file audio")

    return FileResponse(path, media_type="audio/mpeg")
