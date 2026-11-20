from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

import src.document_store as document_store_module
import src.memory as memory_module
from src.document_store import DocumentStore
from src.memory import Memory


@pytest.fixture
def memory(tmp_path, monkeypatch):
    test_db = tmp_path / "test_assistant.db"

    monkeypatch.setattr(
        memory_module,
        "DB_PATH",
        test_db,
    )

    return Memory()


def test_database_tables_are_created(
    memory,
):
    with memory._connect() as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

    table_names = {
        row[0]
        for row in rows
    }

    assert "conversations" in table_names
    assert "messages" in table_names
    assert "memories" in table_names


def test_document_store_migrates_existing_database(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "legacy.db"
    monkeypatch.setattr(
        document_store_module,
        "DB_PATH",
        database_path,
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL UNIQUE,
                file_name TEXT NOT NULL,
                updated_at DATETIME
            )
            """
        )
        connection.execute(
            """
            INSERT INTO documents (
                id,
                file_path,
                file_name
            )
            VALUES (1, 'legacy.txt', 'legacy.txt')
            """
        )

    DocumentStore()

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(documents)"
            )
        }
        legacy_row = connection.execute(
            """
            SELECT file_name, used_ocr, extraction_method, ocr_pages
            FROM documents
            WHERE id = 1
            """
        ).fetchone()

    assert {
        "page_count",
        "file_size",
        "used_ocr",
        "extraction_method",
        "ocr_pages",
    }.issubset(columns)
    assert legacy_row == (
        "legacy.txt",
        0,
        "legacy",
        "[]",
    )


def test_document_store_migration_is_concurrency_safe(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "concurrent-legacy.db"
    monkeypatch.setattr(
        document_store_module,
        "DB_PATH",
        database_path,
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL UNIQUE,
                file_name TEXT NOT NULL,
                updated_at DATETIME
            )
            """
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        stores = list(
            executor.map(
                lambda _index: DocumentStore(),
                range(4),
            )
        )

    assert len(stores) == 4


def test_create_conversation(
    memory,
):
    conversation_id = (
        memory.create_conversation()
    )

    assert isinstance(
        conversation_id,
        str,
    )

    assert memory.conversation_exists(
        conversation_id
    )


def test_unknown_conversation_does_not_exist(
    memory,
):
    assert not memory.conversation_exists(
        "does-not-exist"
    )


def test_save_and_load_messages(
    memory,
):
    conversation_id = (
        memory.create_conversation()
    )

    memory.save_message(
        conversation_id,
        "user",
        "Hei!",
    )

    memory.save_message(
        conversation_id,
        "assistant",
        "Hei! Hvordan kan jeg hjelpe?",
    )

    messages = memory.load_messages(
        conversation_id
    )

    assert messages == [
        {
            "role": "user",
            "content": "Hei!",
        },
        {
            "role": "assistant",
            "content": (
                "Hei! Hvordan kan jeg hjelpe?"
            ),
        },
    ]


def test_messages_are_separated_by_conversation(
    memory,
):
    first_id = memory.create_conversation()
    second_id = memory.create_conversation()

    memory.save_message(
        first_id,
        "user",
        "Jeg liker Zelda.",
    )

    memory.save_message(
        second_id,
        "user",
        "Jeg liker Python.",
    )

    first_messages = memory.load_messages(
        first_id
    )

    second_messages = memory.load_messages(
        second_id
    )

    assert first_messages == [
        {
            "role": "user",
            "content": "Jeg liker Zelda.",
        }
    ]

    assert second_messages == [
        {
            "role": "user",
            "content": "Jeg liker Python.",
        }
    ]


def test_save_and_list_memory(
    memory,
):
    saved = memory.save_memory(
        category="preference",
        content="Jeg liker Zelda.",
        embedding=[0.1, 0.2, 0.3],
        embedding_model="test-model",
    )

    assert saved is True

    memories = memory.list_memories()

    assert len(memories) == 1

    (
        memory_id,
        category,
        content,
        created_at,
    ) = memories[0]

    assert isinstance(memory_id, int)
    assert category == "preference"
    assert content == "Jeg liker Zelda."
    assert created_at is not None


def test_duplicate_memory_is_rejected(
    memory,
):
    first_save = memory.save_memory(
        category="general",
        content="Jeg liker Python.",
        embedding=[0.1, 0.2],
        embedding_model="test-model",
    )

    second_save = memory.save_memory(
        category="general",
        content="Jeg liker Python.",
        embedding=[0.1, 0.2],
        embedding_model="test-model",
    )

    assert first_save is True
    assert second_save is False


def test_delete_memory(
    memory,
):
    memory.save_memory(
        category="general",
        content="Et minne som skal slettes.",
        embedding=[0.1, 0.2],
        embedding_model="test-model",
    )

    memories = memory.list_memories()

    memory_id = memories[0][0]

    deleted = memory.delete_memory(
        memory_id
    )

    assert deleted is True
    assert memory.list_memories() == []


def test_cleanup_empty_conversations(
    memory,
):
    empty_id = memory.create_conversation()
    used_id = memory.create_conversation()

    memory.save_message(
        used_id,
        "user",
        "Denne samtalen skal beholdes.",
    )

    deleted_count = (
        memory.cleanup_empty_conversations()
    )

    assert deleted_count == 1

    assert not memory.conversation_exists(
        empty_id
    )

    assert memory.conversation_exists(
        used_id
    )


def test_foreign_key_rejects_unknown_conversation(
    memory,
):
    with pytest.raises(
        sqlite3.IntegrityError
    ):
        memory.save_message(
            "unknown-conversation",
            "user",
            "Denne meldingen skal ikke lagres.",
        )