from io import BytesIO

import pytest
from docx import Document
from pypdf import PdfWriter

from app.document_parser import DocumentParseError, parse_document


def _make_blank_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _make_encrypted_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("secret")
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _make_docx():
    document = Document()
    document.add_paragraph("操作系统课程笔记")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "课程"
    table.rows[0].cells[1].text = "学分"
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_parse_txt_returns_utf8_text() -> None:
    content = parse_document("笔记.txt", "死锁的四个必要条件".encode("utf-8"))

    assert len(content) == 1
    assert content[0].text == "死锁的四个必要条件"


def test_parse_txt_rejects_non_utf8() -> None:
    with pytest.raises(DocumentParseError, match="UTF-8"):
        parse_document("笔记.txt", b"\xff\xfe\x00")


def test_parse_docx_returns_paragraphs_and_tables() -> None:
    content = parse_document("笔记.docx", _make_docx())

    text = "\n".join(block.text for block in content)
    assert "操作系统课程笔记" in text
    assert "课程|学分" in text


def test_parse_docx_rejects_corrupted_file() -> None:
    with pytest.raises(DocumentParseError, match="DOCX"):
        parse_document("笔记.docx", b"not a docx")


def test_parse_pdf_rejects_encrypted_file() -> None:
    with pytest.raises(DocumentParseError, match="加密"):
        parse_document("笔记.pdf", _make_encrypted_pdf())


def test_parse_pdf_rejects_scanned_file() -> None:
    with pytest.raises(DocumentParseError, match="扫描版"):
        parse_document("笔记.pdf", _make_blank_pdf())


def test_parse_pdf_rejects_corrupted_file() -> None:
    with pytest.raises(DocumentParseError, match="损坏"):
        parse_document("笔记.pdf", b"not a pdf")


def test_parse_document_rejects_unsupported_extension() -> None:
    with pytest.raises(DocumentParseError, match="只支持"):
        parse_document("笔记.md", "content".encode("utf-8"))
