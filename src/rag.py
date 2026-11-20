from io import BytesIO
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image

from src.config import (
    DOCUMENT_CHUNK_OVERLAP,
    DOCUMENT_CHUNK_SIZE,
    DOCUMENT_MIN_SIMILARITY,
    DOCUMENT_TOP_K,
    DOCUMENTS_PATH,
    EMBEDDING_MODEL,
    OCR_LANGUAGES,
    SUPPORTED_DOCUMENT_EXTENSIONS,
    TESSERACT_COMMAND,
)
from src.document_store import DocumentStore
from src.embeddings import EmbeddingService


class DocumentRAG:
    def __init__(self):
        self.store = DocumentStore()
        self.embedding_service = (
            EmbeddingService()
        )

        DOCUMENTS_PATH.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _read_document(
        self,
        file_path: Path,
    ) -> list[dict]:
        sections, _ = self._read_document_with_metadata(
            file_path
        )
        return sections

    def _read_document_with_metadata(
        self,
        file_path: Path,
    ) -> tuple[list[dict], dict]:
        extension = file_path.suffix.lower()
        file_size = file_path.stat().st_size

        if extension in {".txt", ".md"}:
            text = file_path.read_text(
                encoding="utf-8",
            )
            sections = [
                {
                    "page_number": None,
                    "content": text,
                }
            ]
            return sections, {
                "page_count": None,
                "file_size": file_size,
                "used_ocr": False,
                "extraction_method": "text",
                "ocr_pages": [],
            }

        if extension == ".pdf":
            pages = []
            ocr_pages = []

            with pymupdf.open(file_path) as document:
                page_count = len(document)

                for page_index, page in enumerate(
                    document,
                    start=1,
                ):
                    text = page.get_text(
                        "text",
                        sort=True,
                    ).strip()

                    if not text:
                        pytesseract.pytesseract.tesseract_cmd = str(
                            TESSERACT_COMMAND
                        )
                        pixmap = page.get_pixmap(
                            dpi=200,
                            alpha=False,
                        )
                        image = Image.open(
                            BytesIO(
                                pixmap.tobytes("png")
                            )
                        )
                        text = pytesseract.image_to_string(
                            image,
                            lang=OCR_LANGUAGES,
                        ).strip()
                        ocr_pages.append(page_index)

                    if text:
                        pages.append(
                            {
                                "page_number": page_index,
                                "content": text,
                            }
                        )

            if not pages:
                raise ValueError(
                    "PDF-en inneholder ingen uttrekkbar tekst "
                    "etter OCR."
                )

            extraction_method = (
                "pdf_text+ocr"
                if ocr_pages and len(ocr_pages) < page_count
                else "ocr"
                if ocr_pages
                else "pdf_text"
            )

            return pages, {
                "page_count": page_count,
                "file_size": file_size,
                "used_ocr": bool(ocr_pages),
                "extraction_method": extraction_method,
                "ocr_pages": ocr_pages,
            }

        raise ValueError(
            f"Dokumenttypen {extension} støttes ikke."
        )

    def _chunk_text(
        self,
        text: str,
    ) -> list[str]:
        cleaned_text = text.strip()

        if not cleaned_text:
            return []

        chunks = []
        start = 0
        text_length = len(cleaned_text)

        while start < text_length:
            end = min(
                start + DOCUMENT_CHUNK_SIZE,
                text_length,
            )

            chunk = cleaned_text[start:end]

            if end < text_length:
                paragraph_break = chunk.rfind(
                    "\n\n"
                )
                sentence_break = chunk.rfind(
                    ". "
                )

                split_position = max(
                    paragraph_break,
                    sentence_break,
                )

                if split_position > (
                    DOCUMENT_CHUNK_SIZE // 2
                ):
                    end = start + split_position + 1
                    chunk = cleaned_text[start:end]

            chunk = chunk.strip()

            if chunk:
                chunks.append(chunk)

            if end >= text_length:
                break

            next_start = (
                end - DOCUMENT_CHUNK_OVERLAP
            )

            if next_start <= start:
                next_start = end

            start = next_start

        return chunks

    def _create_chunks(
        self,
        document_sections: list[dict],
    ) -> list[dict]:
        chunks = []

        for section in document_sections:
            section_chunks = self._chunk_text(
                section["content"]
            )

            for chunk in section_chunks:
                chunks.append(
                    {
                        "page_number": (
                            section["page_number"]
                        ),
                        "content": chunk,
                    }
                )

        return chunks

    def _create_embeddings(
        self,
        chunks: list[dict],
    ) -> list[list[float]]:
        return [
            self.embedding_service.create_embedding(
                chunk["content"]
            )
            for chunk in chunks
        ]

    def index_document(
        self,
        file_path: Path,
    ) -> int:
        chunk_count, _ = self._index_document(
            file_path
        )
        return chunk_count

    def _index_document(
        self,
        file_path: Path,
    ) -> tuple[int, dict]:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Fant ikke filen: {file_path}"
            )

        extension = file_path.suffix.lower()

        if extension not in (
            SUPPORTED_DOCUMENT_EXTENSIONS
        ):
            supported = ", ".join(
                sorted(
                    SUPPORTED_DOCUMENT_EXTENSIONS
                )
            )

            raise ValueError(
                "Dokumenttypen støttes ikke. "
                f"Støttede typer: {supported}"
            )

        document_sections, metadata = (
            self._read_document_with_metadata(
                file_path
            )
        )

        chunks = self._create_chunks(
            document_sections
        )

        if not chunks:
            raise ValueError(
                "Dokumentet inneholder ingen tekst."
            )

        embeddings = self._create_embeddings(
            chunks
        )

        chunk_count = self.store.save_document(
            file_path=file_path,
            chunks=chunks,
            embeddings=embeddings,
            embedding_model=EMBEDDING_MODEL,
            metadata=metadata,
        )
        return chunk_count, metadata

    def index_all_documents(self):
        results = []

        for file_path in sorted(
            DOCUMENTS_PATH.rglob("*")
        ):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in (
                SUPPORTED_DOCUMENT_EXTENSIONS
            ):
                continue

            try:
                chunk_count, metadata = self._index_document(
                    file_path
                )

                results.append(
                    {
                        "file_name": file_path.name,
                        "chunk_count": chunk_count,
                        "status": "indexed",
                        "used_ocr": metadata["used_ocr"],
                        "page_count": metadata["page_count"],
                        "error": None,
                    }
                )

            except Exception as error:
                results.append(
                    {
                        "file_name": file_path.name,
                        "chunk_count": 0,
                        "status": "error",
                        "error": str(error),
                    }
                )

        return results

    def search(
        self,
        query: str,
    ):
        query_embedding = (
            self.embedding_service.create_embedding(
                query
            )
        )

        stored_chunks = (
            self.store.load_chunks(
                EMBEDDING_MODEL
            )
        )

        results = []

        for chunk in stored_chunks:
            stored_embedding = chunk[
                "embedding"
            ]

            if len(stored_embedding) != len(
                query_embedding
            ):
                continue

            similarity = sum(
                query_value * document_value
                for query_value, document_value
                in zip(
                    query_embedding,
                    stored_embedding,
                )
            )

            if similarity < (
                DOCUMENT_MIN_SIMILARITY
            ):
                continue

            results.append(
                {
                    "id": chunk["id"],
                    "file_name": (
                        chunk["file_name"]
                    ),
                    "file_path": (
                        chunk["file_path"]
                    ),
                    "chunk_index": (
                        chunk["chunk_index"]
                    ),
                    "page_number": (
                        chunk["page_number"]
                    ),
                    "content": chunk["content"],
                    "similarity": similarity,
                }
            )

        results.sort(
            key=lambda result: result[
                "similarity"
            ],
            reverse=True,
        )

        return results[:DOCUMENT_TOP_K]

    def list_documents(self):
        return self.store.list_documents()

    def get_document(self, document_id: int):
        return self.store.get_document(document_id)

    def delete_document(
        self,
        document_id: int,
    ) -> bool:
        return self.store.delete_document(
            document_id
        )