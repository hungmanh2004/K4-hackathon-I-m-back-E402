import pytest

from pdf_parser import extract_pages, page_count

PDF = "../HCI - UX-UI 01 HCI Intro Ver 1.1 .pdf"


def test_page_count_is_positive():
    assert page_count(PDF) > 0


def test_extract_pages_length_matches_page_count():
    pages = extract_pages(PDF)
    assert len(pages) == page_count(PDF)


def test_pages_are_one_indexed_and_ordered():
    pages = extract_pages(PDF)
    assert [p["page"] for p in pages] == list(range(1, len(pages) + 1))


def test_every_page_has_text_key_as_string():
    pages = extract_pages(PDF)
    assert all(isinstance(p["text"], str) for p in pages)


def test_document_has_meaningful_text_overall():
    # Slide PDF, không phải bản scan — tổng text phải đáng kể.
    # Không assert từng trang vì trang thuần ảnh hợp lệ và sẽ rỗng.
    pages = extract_pages(PDF)
    total = sum(len(p["text"]) for p in pages)
    assert total > 1000


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        extract_pages("../khong-ton-tai.pdf")
