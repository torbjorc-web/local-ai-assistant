import pytest
from fastapi.testclient import TestClient

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
            ),
            (
                2,
                "machine_learning.pdf",
                "data/documents/machine_learning.pdf",
                5,
                "2026-11-19 10:05:00",
            ),
        ]

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
    }


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