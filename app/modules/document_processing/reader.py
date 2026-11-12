from pathlib import Path

import pymupdf
from docx import Document
from docx.document import Document as _DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph


class UnsupportedDocumentError(Exception):
    pass


# ----------------- PDF -----------------

def read_pdf(file_path) -> str:
    doc = pymupdf.open(str(file_path))
    try:
        pages = [page.get_text("text", sort=True) for page in doc]
        full = "\n".join(pages)
    finally:
        doc.close()

    if not full.strip():
        raise UnsupportedDocumentError(
            "PDF không chứa lớp văn bản (có thể là PDF scan). "
            "Cần OCR — hiện chưa hỗ trợ trong phiên bản này."
        )
    return full


# ----------------- DOCX helpers -----------------

def _iter_block_items(parent):
    """
    Duyệt Paragraph và Table theo ĐÚNG thứ tự xuất hiện trong file DOCX.
    parent có thể là Document hoặc _Cell (để đệ quy vào bảng lồng nhau).
    """
    if isinstance(parent, _DocxDocument):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise TypeError(f"Không hỗ trợ parent kiểu {type(parent)}")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _table_to_text(table: Table) -> str:
    """Chuyển bảng thành text, đệ quy xử lý bảng lồng nhau trong cell."""
    rows_text: list[str] = []
    for row in table.rows:
        cells_text: list[str] = []
        for cell in row.cells:
            pieces: list[str] = []
            for block in _iter_block_items(cell):
                if isinstance(block, Paragraph):
                    if block.text.strip():
                        pieces.append(block.text.strip())
                elif isinstance(block, Table):
                    nested = _table_to_text(block)
                    if nested.strip():
                        pieces.append(nested.replace("\n", " / "))
            cells_text.append(" ".join(pieces).replace("\n", " "))
        if any(cells_text):
            rows_text.append(" | ".join(cells_text))
    return "\n".join(rows_text)


def _extract_from_hf(container) -> list[str]:
    """Trích Paragraph/Table từ header hoặc footer."""
    parts: list[str] = []
    if container is None:
        return parts
    for block in _iter_block_items(container):
        if isinstance(block, Paragraph):
            if block.text.strip():
                parts.append(block.text.strip())
        elif isinstance(block, Table):
            t = _table_to_text(block)
            if t.strip():
                parts.append(t)
    return parts


def read_docx(file_path, include_headers_footers: bool = False) -> str:
    doc = Document(str(file_path))
    parts: list[str] = []

    # Header / Footer (tùy chọn) — đặt trước phần thân để giữ ngữ cảnh tiêu đề
    if include_headers_footers:
        seen_linked = set()
        for section in doc.sections:
            for hf in (
                section.header, section.footer,
                section.first_page_header, section.first_page_footer,
                section.even_page_header, section.even_page_footer,
            ):
                if hf is None or hf.is_linked_to_previous:
                    continue
                # tránh trùng khi nhiều section dùng chung header
                key = id(hf.part)
                if key in seen_linked:
                    continue
                seen_linked.add(key)
                parts.extend(_extract_from_hf(hf))

    # Thân tài liệu — Paragraph và Table theo đúng thứ tự gốc
    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            if block.text.strip():
                parts.append(block.text.strip())
        elif isinstance(block, Table):
            t = _table_to_text(block)
            if t.strip():
                parts.append(t)

    return "\n".join(parts)


# ----------------- Public API -----------------

def read_txt(file_path) -> str:
    return Path(file_path).read_text(encoding="utf-8", errors="ignore")


def read_document(file_path, include_headers_footers: bool = False) -> str:
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return read_pdf(file_path)
    if suffix == ".docx":
        return read_docx(file_path, include_headers_footers=include_headers_footers)
    if suffix == ".txt":
        return read_txt(file_path)
    raise UnsupportedDocumentError(f"Định dạng không hỗ trợ: {suffix}")