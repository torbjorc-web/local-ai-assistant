import json
import sqlite3
from pathlib import Path

from src.memory import DB_PATH


class DocumentStore:
    def __init__(self):
        DB_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._create_tables()
        self._migrate_documents_table()
        self._migrate_document_chunks_table()

    def _migrate_documents_table(self):
        migrations = {
            "page_count": "INTEGER",
            "file_size": (
                "INTEGER NOT NULL DEFAULT 0"
            ),
            "used_ocr": (
                "INTEGER NOT NULL DEFAULT 0"
            ),
            "extraction_method": (
                "TEXT NOT NULL DEFAULT 'legacy'"
            ),
            "ocr_pages": (
                "TEXT NOT NULL DEFAULT '[]'"
            ),
        }

        with self._connect() as connection:
            columns = connection.execute(
                "PRAGMA table_info(documents)"
            ).fetchall()
            column_names = {
                column[1]
                for column in columns
            }

            if migrations.keys() <= column_names:
                return

            connection.execute("BEGIN IMMEDIATE")
            columns = connection.execute(
                "PRAGMA table_info(documents)"
            ).fetchall()
            column_names = {
                column[1]
                for column in columns
            }

            for name, definition in migrations.items():
                if name not in column_names:
                    connection.execute(
                        f"""
                        ALTER TABLE documents
                        ADD COLUMN {name} {definition}
                        """
                    )

    def _connect(self):
        connection = sqlite3.connect(DB_PATH)

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        return connection

    def _create_tables(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    file_name TEXT NOT NULL,
                    page_count INTEGER,
                    file_size INTEGER NOT NULL DEFAULT 0,
                    used_ocr INTEGER NOT NULL DEFAULT 0,
                    extraction_method TEXT NOT NULL DEFAULT 'legacy',
                    ocr_pages TEXT NOT NULL DEFAULT '[]',
                    updated_at DATETIME
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    page_number INTEGER,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    embedding_model TEXT NOT NULL,
                    created_at DATETIME
                        DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (document_id)
                        REFERENCES documents(id)
                        ON DELETE CASCADE,

                    UNIQUE (
                        document_id,
                        chunk_index
                    )
                )
                """
            )

    def _migrate_document_chunks_table(self):
        with self._connect() as connection:
            columns = connection.execute(
                """
                PRAGMA table_info(document_chunks)
                """
            ).fetchall()

            column_names = {
                column[1]
                for column in columns
            }

            if "page_number" in column_names:
                return

            connection.execute("BEGIN IMMEDIATE")
            columns = connection.execute(
                "PRAGMA table_info(document_chunks)"
            ).fetchall()
            column_names = {
                column[1]
                for column in columns
            }

            if "page_number" not in column_names:
                connection.execute(
                    """
                    ALTER TABLE document_chunks
                    ADD COLUMN page_number INTEGER
                    """
                )

    def save_document(
        self,
        file_path: Path,
        chunks: list[dict],
        embeddings: list[list[float]],
        embedding_model: str,
        metadata: dict | None = None,
    ) -> int:
        normalized_path = str(
            file_path.resolve()
        )
        metadata = metadata or {}
        ocr_pages = metadata.get(
            "ocr_pages",
            [],
        )

        if len(chunks) != len(embeddings):
            raise ValueError(
                "Antall chunks og embeddings er forskjellig."
            )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO documents (
                    file_path,
                    file_name,
                    page_count,
                    file_size,
                    used_ocr,
                    extraction_method,
                    ocr_pages,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)

                ON CONFLICT(file_path)
                DO UPDATE SET
                    file_name = excluded.file_name,
                    page_count = excluded.page_count,
                    file_size = excluded.file_size,
                    used_ocr = excluded.used_ocr,
                    extraction_method = excluded.extraction_method,
                    ocr_pages = excluded.ocr_pages,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    normalized_path,
                    file_path.name,
                    metadata.get("page_count"),
                    metadata.get(
                        "file_size",
                        file_path.stat().st_size,
                    ),
                    bool(metadata.get("used_ocr", False)),
                    metadata.get(
                        "extraction_method",
                        "text",
                    ),
                    json.dumps(ocr_pages),
                ),
            )

            document_row = connection.execute(
                """
                SELECT id
                FROM documents
                WHERE file_path = ?
                """,
                (normalized_path,),
            ).fetchone()

            if document_row is None:
                raise RuntimeError(
                    "Kunne ikke opprette dokumentet."
                )

            document_id = document_row[0]

            connection.execute(
                """
                DELETE FROM document_chunks
                WHERE document_id = ?
                """,
                (document_id,),
            )

            for chunk_index, (chunk, embedding) in enumerate(
                zip(chunks, embeddings)
            ):
                connection.execute(
                    """
                    INSERT INTO document_chunks (
                        document_id,
                        chunk_index,
                        page_number,
                        content,
                        embedding,
                        embedding_model
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        chunk_index,
                        chunk["page_number"],
                        chunk["content"],
                        json.dumps(embedding),
                        embedding_model,
                    ),
                )

        return len(chunks)

    def list_documents(self):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    d.id,
                    d.file_name,
                    d.file_path,
                    COUNT(c.id) AS chunk_count,
                    d.updated_at,
                    d.page_count,
                    d.file_size,
                    d.used_ocr,
                    d.extraction_method,
                    d.ocr_pages

                FROM documents AS d

                LEFT JOIN document_chunks AS c
                    ON c.document_id = d.id

                GROUP BY
                    d.id,
                    d.file_name,
                    d.file_path,
                    d.updated_at,
                    d.page_count,
                    d.file_size,
                    d.used_ocr,
                    d.extraction_method,
                    d.ocr_pages

                ORDER BY d.updated_at DESC
                """
            ).fetchall()

        return rows

    def get_document(self, document_id: int):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    file_name,
                    file_path,
                    page_count,
                    file_size,
                    used_ocr,
                    extraction_method,
                    ocr_pages,
                    updated_at
                FROM documents
                WHERE id = ?
                """,
                (document_id,),
            ).fetchone()

            if row is None:
                return None

            chunks = connection.execute(
                """
                SELECT
                    chunk_index,
                    page_number,
                    content
                FROM document_chunks
                WHERE document_id = ?
                ORDER BY chunk_index
                """,
                (document_id,),
            ).fetchall()

        return {
            "id": row[0],
            "file_name": row[1],
            "file_path": row[2],
            "page_count": row[3],
            "file_size": row[4],
            "used_ocr": bool(row[5]),
            "extraction_method": row[6],
            "ocr_pages": json.loads(row[7]),
            "updated_at": row[8],
            "chunk_count": len(chunks),
            "chunks": [
                {
                    "chunk_index": chunk[0],
                    "page_number": chunk[1],
                    "content": chunk[2],
                }
                for chunk in chunks
            ],
        }

    def load_chunks(
        self,
        embedding_model: str,
    ):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.id,
                    d.file_name,
                    d.file_path,
                    c.chunk_index,
                    c.page_number,
                    c.content,
                    c.embedding

                FROM document_chunks AS c

                INNER JOIN documents AS d
                    ON d.id = c.document_id

                WHERE c.embedding_model = ?
                """,
                (embedding_model,),
            ).fetchall()

        chunks = []

        for (
            chunk_id,
            file_name,
            file_path,
            chunk_index,
            page_number,
            content,
            embedding_json,
        ) in rows:
            chunks.append(
                {
                    "id": chunk_id,
                    "file_name": file_name,
                    "file_path": file_path,
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "content": content,
                    "embedding": json.loads(
                        embedding_json
                    ),
                }
            )

        return chunks

    def delete_document(
        self,
        document_id: int,
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM documents
                WHERE id = ?
                """,
                (document_id,),
            )

            return cursor.rowcount > 0