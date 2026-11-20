import json

import pytest
from fastapi.testclient import TestClient

import src.api as api_module
from src.api import app, get_chatbot


class FakeMemory:
    def conversation_exists(
        self,
        conversation_id: str,
    ):
        return (
            conversation_id
            == "existing-conversation"
        )

    def load_messages(
        self,
        conversation_id: str,
    ):
        if (
            conversation_id
            != "existing-conversation"
        ):
            return []

        return [
            {
                "role": "user",
                "content": "Tidligere melding",
            },
            {
                "role": "assistant",
                "content": "Tidligere svar",
            },
        ]


class FakeChatbot:
    def __init__(self):
        self.memory = FakeMemory()
        self.conversation_id = None

    def load_conversation(
        self,
        conversation_id: str,
    ):
        if (
            conversation_id
            != "existing-conversation"
        ):
            return False

        self.conversation_id = conversation_id

        return True

    def list_conversations(self):
        return [
            (
                "existing-conversation",
                "2026-11-19 10:00:00",
                2,
                "Tidligere melding",
            )
        ]

    def cleanup_empty_conversations(self):
        return 1

    def list_memories(self):
        return [
            (
                1,
                "general",
                "Jeg liker Python.",
                "2026-11-19 10:00:00",
            ),
            (
                2,
                "general",
                "Favorittspillet mitt er Zelda.",
                "2026-11-19 10:05:00",
            ),
        ]

    def remember(
        self,
        content: str,
        category: str = "general",
    ):
        if content == "Duplikatminne":
            return False

        return True

    def forget(
        self,
        memory_id: int,
    ):
        return memory_id in {1, 2}

    def list_documents(self):
        return [
            (
                1,
                "python_notes.md",
                "data/documents/python_notes.md",
                2,
                "2026-11-19 10:00:00",
                None,
                300,
                0,
                "text",
                "[]",
            ),
            (
                2,
                "machine_learning.pdf",
                "data/documents/machine_learning.pdf",
                5,
                "2026-11-19 10:05:00",
                12,
                4096,
                1,
                "ocr",
                "[1,2]",
            ),
        ]

    def get_document(self, document_id: int):
        if document_id != 1:
            return None

        return {
            "id": 1,
            "file_name": "python_notes.md",
            "file_path": (
                "data/documents/python_notes.md"
            ),
            "chunk_count": 1,
            "updated_at": "2026-11-19 10:00:00",
            "page_count": None,
            "file_size": 300,
            "used_ocr": False,
            "extraction_method": "text",
            "ocr_pages": [],
            "chunks": [
                {
                    "chunk_index": 0,
                    "page_number": None,
                    "content": "Python notes.",
                }
            ],
        }

    def index_documents(self):
        return [
            {
                "file_name": "python_notes.md",
                "chunk_count": 2,
                "status": "indexed",
                "used_ocr": False,
                "error": None,
            },
            {
                "file_name": "machine_learning.pdf",
                "chunk_count": 5,
                "status": "indexed",
                "used_ocr": True,
                "error": None,
            },
        ]

    def search_documents(
        self,
        query: str,
    ):
        return [
            {
                "file_name": "python_notes.md",
                "file_path": (
                    "data/documents/python_notes.md"
                ),
                "chunk_index": 0,
                "page_number": None,
                "content": (
                    "Python brukes til dataanalyse "
                    "og automatisering."
                ),
                "similarity": 0.81,
            }
        ]

    def delete_document(
        self,
        document_id: int,
    ):
        return document_id in {1, 2}

    def index_document(self, file_path):
        return 2


@pytest.fixture
def client(monkeypatch):
    chatbot = FakeChatbot()

    monkeypatch.setitem(
        app.dependency_overrides,
        get_chatbot,
        lambda: chatbot,
    )

    return TestClient(app)


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "application": "Local AI Assistant",
    }


def test_chat(client, monkeypatch):
    class FakeChatbot:
        conversation_id = "test-conversation"
        last_document_sources = []

        def chat(self, message):
            received_messages.append(message)
            return "Test response"

    received_messages = []
    chatbot = FakeChatbot()

    monkeypatch.setitem(
        app.dependency_overrides,
        get_chatbot,
        lambda: chatbot,
    )

    response = client.post(
        "/chat",
        json={"message": "  Hello  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "response": "Test response",
        "conversation_id": "test-conversation",
        "sources": [],
    }
    assert received_messages == ["Hello"]


def test_chat_stream_emits_chunks_and_completion(
    client,
    monkeypatch,
):
    class FakeChatbot:
        conversation_id = "streamed-conversation"
        last_document_sources = [
            {
                "file_name": "notes.pdf",
                "chunk_index": 2,
                "page_number": 3,
                "similarity": 0.9,
            }
        ]

        def chat_stream(self, message):
            assert message == "Stream this"
            yield "Hello"
            yield " world"

    chatbot = FakeChatbot()
    monkeypatch.setitem(
        app.dependency_overrides,
        get_chatbot,
        lambda: chatbot,
    )

    response = client.post(
        "/chat/stream",
        json={"message": " Stream this "},
    )

    assert response.status_code == 200
    events = [
        json.loads(line)
        for line in response.text.splitlines()
    ]
    assert events == [
        {
            "type": "chunk",
            "content": "Hello",
        },
        {
            "type": "chunk",
            "content": " world",
        },
        {
            "type": "done",
            "conversation_id": "streamed-conversation",
            "sources": [
                {
                    "file_name": "notes.pdf",
                    "chunk_index": 2,
                    "page_number": 3,
                    "similarity": 0.9,
                }
            ],
        },
    ]


def test_chat_stream_reports_generation_errors(
    client,
    monkeypatch,
):
    class FakeChatbot:
        conversation_id = "streamed-conversation"
        last_document_sources = []

        def chat_stream(self, _message):
            yield "Partial"
            raise RuntimeError("model unavailable")

        conversation_id = "streamed-conversation"
        last_document_sources = []

    monkeypatch.setitem(
        app.dependency_overrides,
        get_chatbot,
        lambda: FakeChatbot(),
    )

    response = client.post(
        "/chat/stream",
        json={"message": "Hello"},
    )

    events = [
        json.loads(line)
        for line in response.text.splitlines()
    ]
    assert events[-1]["type"] == "error"
    assert (
        events[-1]["conversation_id"]
        == "streamed-conversation"
    )
    assert "model unavailable" in events[-1]["detail"]


def test_chat_existing_conversation(client, monkeypatch):
    loaded_conversations = []
    received_messages = []

    class FakeChatbot:
        conversation_id = None
        last_document_sources = []

        def load_conversation(self, conversation_id):
            loaded_conversations.append(conversation_id)
            self.conversation_id = conversation_id
            return True

        def chat(self, message):
            received_messages.append(message)
            return "Continued response"

    chatbot = FakeChatbot()

    monkeypatch.setitem(
        app.dependency_overrides,
        get_chatbot,
        lambda: chatbot,
    )

    response = client.post(
        "/chat",
        json={
            "message": "Continue this conversation",
            "conversation_id": "test-conversation",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "response": "Continued response",
        "conversation_id": "test-conversation",
        "sources": [],
    }
    assert loaded_conversations == ["test-conversation"]
    assert received_messages == ["Continue this conversation"]


def test_get_conversation_messages(client):
    response = client.get(
        (
            "/conversations/"
            "existing-conversation/"
            "messages"
        )
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "role": "user",
            "content": "Tidligere melding",
        },
        {
            "role": "assistant",
            "content": "Tidligere svar",
        },
    ]


def test_get_unknown_conversation_messages(
    client,
):
    response = client.get(
        (
            "/conversations/"
            "unknown-conversation/"
            "messages"
        )
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Conversation not found.",
    }


def test_list_conversations(client):
    response = client.get(
        "/conversations"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    assert data[0] == {
        "id": "existing-conversation",
        "created_at": "2026-11-19 10:00:00",
        "message_count": 2,
        "first_message": "Tidligere melding",
    }


def test_chat_unknown_conversation(client):
    response = client.post(
        "/chat",
        json={
            "message": "Fortsett samtalen",
            "conversation_id": (
                "unknown-conversation"
            ),
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Conversation not found.",
    }


def test_cleanup_conversations(client):
    response = client.post(
        "/conversations/cleanup"
    )

    assert response.status_code == 200

    assert response.json() == {
        "deleted_count": 1,
    }


def test_list_memories(client):
    response = client.get(
        "/memories"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    assert data[0] == {
        "id": 1,
        "category": "general",
        "content": "Jeg liker Python.",
        "created_at": "2026-11-19 10:00:00",
    }

    assert data[1] == {
        "id": 2,
        "category": "general",
        "content": (
            "Favorittspillet mitt er Zelda."
        ),
        "created_at": "2026-11-19 10:05:00",
    }


def test_create_memory(client):
    response = client.post(
        "/memories",
        json={
            "content": (
                "Jeg liker Power BI."
            ),
            "category": "general",
        },
    )

    assert response.status_code == 201

    assert response.json() == {
        "saved": True,
    }


def test_create_duplicate_memory(client):
    response = client.post(
        "/memories",
        json={
            "content": "Duplikatminne",
            "category": "general",
        },
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail": "This memory already exists.",
    }


def test_delete_memory(client):
    response = client.delete(
        "/memories/1"
    )

    assert response.status_code == 200

    assert response.json() == {
        "deleted": True,
    }


def test_delete_unknown_memory(client):
    response = client.delete(
        "/memories/999"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Memory not found.",
    }


def test_list_documents(client):
    response = client.get(
        "/documents"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    assert data[0] == {
        "id": 1,
        "file_name": "python_notes.md",
        "file_path": (
            "data/documents/python_notes.md"
        ),
        "chunk_count": 2,
        "updated_at": (
            "2026-11-19 10:00:00"
        ),
        "page_count": None,
        "file_size": 300,
        "used_ocr": False,
        "extraction_method": "text",
        "ocr_pages": [],
    }

    assert data[1] == {
        "id": 2,
        "file_name": "machine_learning.pdf",
        "file_path": (
            "data/documents/"
            "machine_learning.pdf"
        ),
        "chunk_count": 5,
        "updated_at": (
            "2026-11-19 10:05:00"
        ),
        "page_count": 12,
        "file_size": 4096,
        "used_ocr": True,
        "extraction_method": "ocr",
        "ocr_pages": [1, 2],
    }

def test_get_document_details(client):
    response = client.get("/documents/1")

    assert response.status_code == 200
    data = response.json()
    assert data["page_count"] is None
    assert data["chunks"] == [
        {
            "chunk_index": 0,
            "page_number": None,
            "content": "Python notes.",
        }
    ]


def test_get_unknown_document_details(client):
    response = client.get("/documents/999")

    assert response.status_code == 404


def test_index_documents(client):
    response = client.post(
        "/documents/index"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    assert data[0] == {
        "file_name": "python_notes.md",
        "chunk_count": 2,
        "status": "indexed",
        "used_ocr": False,
        "error": None,
    }

    assert data[1] == {
        "file_name": "machine_learning.pdf",
        "chunk_count": 5,
        "status": "indexed",
        "used_ocr": True,
        "error": None,
    }


def test_search_documents(client):
    response = client.get(
        "/documents/search",
        params={
            "query": "Python",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    assert data[0] == {
        "file_name": "python_notes.md",
        "file_path": (
            "data/documents/python_notes.md"
        ),
        "chunk_index": 0,
        "page_number": None,
        "content": (
            "Python brukes til dataanalyse "
            "og automatisering."
        ),
        "similarity": 0.81,
    }


def test_delete_document(client):
    response = client.delete(
        "/documents/1"
    )

    assert response.status_code == 200

    assert response.json() == {
        "deleted": True,
    }


def test_delete_unknown_document(client):
    response = client.delete(
        "/documents/999"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Document not found.",
    }


def test_upload_document_sanitizes_windows_path(
    client,
    tmp_path,
    monkeypatch,
):
    documents_path = tmp_path / "documents"
    monkeypatch.setattr(
        api_module,
        "DOCUMENTS_PATH",
        documents_path,
    )

    content = b"Python notes"
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "C:\\private\\notes.txt",
                content,
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "file_name": "notes.txt",
        "file_size": len(content),
        "chunk_count": 2,
        "status": "indexed",
    }
    assert (
        documents_path / "notes.txt"
    ).read_bytes() == content


def test_upload_document(
    client,
    tmp_path,
    monkeypatch,
):
    documents_path = (
        tmp_path / "documents"
    )

    documents_path.mkdir()

    monkeypatch.setattr(
        api_module,
        "DOCUMENTS_PATH",
        documents_path,
    )

    content = (
        b"# Python\n\n"
        b"Python brukes til dataanalyse."
    )

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "uploaded_notes.md",
                content,
                "text/markdown",
            )
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data == {
        "file_name": "uploaded_notes.md",
        "file_size": len(content),
        "chunk_count": 2,
        "status": "indexed",
    }

    saved_file = (
        documents_path
        / "uploaded_notes.md"
    )

    assert saved_file.read_bytes() == content


def test_upload_document_rejects_oversized_file(
    client,
    tmp_path,
    monkeypatch,
):
    documents_path = tmp_path / "documents"
    monkeypatch.setattr(
        api_module,
        "DOCUMENTS_PATH",
        documents_path,
    )
    monkeypatch.setattr(
        api_module,
        "MAX_UPLOAD_SIZE",
        3,
    )

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "large.txt",
                b"four",
                "text/plain",
            )
        },
    )

    assert response.status_code == 413
    assert list(documents_path.iterdir()) == []


def test_upload_unsupported_document(
    client,
    tmp_path,
    monkeypatch,
):
    documents_path = (
        tmp_path / "documents"
    )

    documents_path.mkdir()

    monkeypatch.setattr(
        api_module,
        "DOCUMENTS_PATH",
        documents_path,
    )

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "program.exe",
                b"not allowed",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 415