import pytest

import src.document_store as document_store_module
import src.memory as memory_module
import src.rag as rag_module
from src.rag import DocumentRAG


class FakeEmbeddingService:
    """
    Test-erstatning for EmbeddingService.

    Ingen Ollama-server eller embeddingmodell er nødvendig.
    """

    def create_embedding(self, text: str):
        text_lower = text.lower()

        if "python" in text_lower:
            return [1.0, 0.0, 0.0]

        if "azure" in text_lower:
            return [0.0, 1.0, 0.0]

        if "power bi" in text_lower:
            return [0.0, 0.0, 1.0]

        return [0.5, 0.5, 0.5]


@pytest.fixture
def rag(tmp_path, monkeypatch):
    test_db = tmp_path / "rag_test.db"
    documents_path = tmp_path / "documents"

    documents_path.mkdir()

    # Sørg for at Memory og DocumentStore bruker
    # testdatabasen, ikke data/assistant.db.
    monkeypatch.setattr(
        memory_module,
        "DB_PATH",
        test_db,
    )

    monkeypatch.setattr(
        document_store_module,
        "DB_PATH",
        test_db,
    )

    # Sørg for at RAG bruker midlertidig dokumentmappe.
    monkeypatch.setattr(
        rag_module,
        "DOCUMENTS_PATH",
        documents_path,
    )

    # Ikke kontakt Ollama under test.
    monkeypatch.setattr(
        rag_module,
        "EmbeddingService",
        FakeEmbeddingService,
    )

    return DocumentRAG()


def test_chunk_text_short_document(rag):
    chunks = rag._chunk_text(
        "Dette er et kort dokument."
    )

    assert chunks == [
        "Dette er et kort dokument."
    ]


def test_chunk_text_empty_document(rag):
    chunks = rag._chunk_text("   ")

    assert chunks == []


def test_chunk_text_long_document(rag):
    text = (
        "Python brukes til dataanalyse. "
        * 100
    )

    chunks = rag._chunk_text(text)

    assert len(chunks) > 1

    for chunk in chunks:
        assert chunk.strip()


def test_create_chunks_preserves_page_number(rag):
    sections = [
        {
            "page_number": 3,
            "content": (
                "Python brukes til maskinlæring."
            ),
            "extraction_method": "text",
        }
    ]

    chunks = rag._create_chunks(sections)

    assert len(chunks) == 1

    assert chunks[0]["page_number"] == 3
    assert "Python" in chunks[0]["content"]


def test_read_text_document(rag, tmp_path):
    document = tmp_path / "example.txt"

    document.write_text(
        "Python brukes til automatisering.",
        encoding="utf-8",
    )

    sections = rag._read_document(
        document
    )

    assert len(sections) == 1
    assert sections[0]["page_number"] is None
    assert (
        sections[0]["content"]
        == "Python brukes til automatisering."
    )


def test_index_text_document(rag, tmp_path):
    document = tmp_path / "python_notes.txt"

    document.write_text(
        (
            "Python brukes til dataanalyse, "
            "automatisering og maskinlæring."
        ),
        encoding="utf-8",
    )

    chunk_count = rag.index_document(
        document
    )

    assert chunk_count == 1

    documents = rag.list_documents()

    assert len(documents) == 1

    (
        document_id,
        file_name,
        file_path,
        stored_chunk_count,
        updated_at,
        page_count,
        file_size,
        used_ocr,
        extraction_method,
        ocr_pages,
    ) = documents[0]

    assert isinstance(document_id, int)
    assert file_name == "python_notes.txt"
    assert stored_chunk_count == 1
    assert updated_at is not None
    assert page_count is None
    assert file_size == document.stat().st_size
    assert used_ocr == 0
    assert extraction_method == "text"
    assert ocr_pages == "[]"

    details = rag.get_document(document_id)
    assert details["chunk_count"] == 1
    assert details["chunks"] == [
        {
            "chunk_index": 0,
            "page_number": None,
            "content": (
                "Python brukes til dataanalyse, "
                "automatisering og maskinlæring."
            ),
        }
    ]


def test_index_pdf_ocr_metadata(
    rag,
    tmp_path,
    monkeypatch,
):
    class FakePage:
        def __init__(self, text):
            self.text = text

        def get_text(self, *_args, **_kwargs):
            return self.text

        def get_pixmap(self, **_kwargs):
            return FakePixmap()

    class FakePixmap:
        def tobytes(self, _image_format):
            return b"fake-image"

    class FakePdf:
        def __init__(self):
            self.pages = [
                FakePage("Embedded text."),
                FakePage(""),
            ]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def __len__(self):
            return len(self.pages)

        def __iter__(self):
            return iter(self.pages)

    document = tmp_path / "scanned.pdf"
    document.write_bytes(b"%PDF-test")

    monkeypatch.setattr(
        rag_module.pymupdf,
        "open",
        lambda _path: FakePdf(),
    )
    monkeypatch.setattr(
        rag_module.Image,
        "open",
        lambda _image: object(),
    )
    monkeypatch.setattr(
        rag_module.pytesseract,
        "image_to_string",
        lambda _image, lang: (
            "OCR extracted text."
        ),
    )

    rag.index_document(document)

    document_id = rag.list_documents()[0][0]
    details = rag.get_document(document_id)

    assert details["page_count"] == 2
    assert details["used_ocr"] is True
    assert details["extraction_method"] == "pdf_text+ocr"
    assert details["ocr_pages"] == [2]
    assert [
        chunk["page_number"]
        for chunk in details["chunks"]
    ] == [1, 2]


def test_search_returns_relevant_document(
    rag,
    tmp_path,
):
    python_document = (
        tmp_path / "python_notes.txt"
    )

    azure_document = (
        tmp_path / "azure_notes.txt"
    )

    python_document.write_text(
        (
            "Python brukes til dataanalyse "
            "og automatisering."
        ),
        encoding="utf-8",
    )

    azure_document.write_text(
        (
            "Azure brukes til cloud og "
            "identitetsløsninger."
        ),
        encoding="utf-8",
    )

    rag.index_document(
        python_document
    )

    rag.index_document(
        azure_document
    )

    results = rag.search(
        "Hva bruker jeg Python til?"
    )

    assert results

    assert (
        results[0]["file_name"]
        == "python_notes.txt"
    )

    assert (
        "Python"
        in results[0]["content"]
    )


def test_search_preserves_chunk_metadata(
    rag,
    tmp_path,
):
    document = tmp_path / "python_notes.txt"

    document.write_text(
        "Python brukes til AI.",
        encoding="utf-8",
    )

    rag.index_document(document)

    results = rag.search(
        "Python"
    )

    assert results

    first_result = results[0]

    assert first_result["chunk_index"] == 0
    assert first_result["page_number"] is None
    assert "similarity" in first_result


def test_delete_document_removes_document(
    rag,
    tmp_path,
):
    document = tmp_path / "delete_me.txt"

    document.write_text(
        "Python testdokument.",
        encoding="utf-8",
    )

    rag.index_document(document)

    documents = rag.list_documents()

    document_id = documents[0][0]

    deleted = rag.delete_document(
        document_id
    )

    assert deleted is True
    assert rag.list_documents() == []