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