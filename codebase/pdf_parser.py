"""Trích xuất text từ PDF theo từng trang. Hàm thuần — không AI, không mạng."""
import os

import fitz  # pymupdf


def extract_pages(pdf_path: str) -> list[dict]:
    """Trả về [{"page": 1, "text": "..."}, ...] — page đánh số từ 1.

    Trang thuần ảnh sẽ có text rỗng; đó là hợp lệ, không phải lỗi.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Không tìm thấy PDF: {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        return [
            {"page": i + 1, "text": doc[i].get_text("text").strip()}
            for i in range(len(doc))
        ]
    finally:
        doc.close()


def page_count(pdf_path: str) -> int:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Không tìm thấy PDF: {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()
