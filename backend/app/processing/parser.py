"""
Codex One v2 — Document Parser

Extracts text and metadata from PDF and ePub files.
Reuses proven parsing logic from v1 with async-friendly interface.
"""

import os
from pathlib import Path
from typing import Optional, Any


def parse_document(file_path: str) -> Optional[list[dict[str, Any]]]:
    """
    Parse a document file and return list of pages/sections.
    
    Returns list of dicts with:
        - 'text': extracted text content
        - 'metadata': dict with page/section info, filename, etc.
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_path)
    elif ext == ".epub":
        return _parse_epub(file_path)
    else:
        raise ValueError(f"Unsupported format: {ext}. Use PDF or ePub.")


def _parse_pdf(file_path: str) -> list[dict[str, Any]]:
    """Extract text from PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(file_path)
    filename = os.path.basename(file_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        if text and text.strip():
            pages.append({
                "text": text.strip(),
                "metadata": {
                    "filename": filename,
                    "page": page_num + 1,
                    "total_pages": len(doc),
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "format": "pdf",
                },
            })

    doc.close()
    return pages


def _parse_epub(file_path: str) -> list[dict[str, Any]]:
    """Extract text from ePub using ebooklib + BeautifulSoup."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(file_path, options={"ignore_ncx": True})
    filename = os.path.basename(file_path)

    # Extract metadata
    title = ""
    author = ""
    try:
        title_meta = book.get_metadata("DC", "title")
        title = title_meta[0][0] if title_meta else ""
        author_meta = book.get_metadata("DC", "creator")
        author = author_meta[0][0] if author_meta else ""
    except Exception:
        pass

    sections = []
    section_idx = 0

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        try:
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            text = soup.get_text(separator="\n", strip=True)

            if text and len(text.strip()) > 50:
                # Try to extract section title from headings
                heading = soup.find(["h1", "h2", "h3"])
                section_title = heading.get_text(strip=True) if heading else ""

                sections.append({
                    "text": text.strip(),
                    "metadata": {
                        "filename": filename,
                        "section": section_idx,
                        "section_title": section_title,
                        "title": title,
                        "author": author,
                        "format": "epub",
                    },
                })
                section_idx += 1
        except Exception:
            continue

    return sections
