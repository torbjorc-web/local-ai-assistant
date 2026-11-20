import pytest
from fastapi.testclient import TestClient

from src.api import app, get_chatbot


@pytest.fixture
def client():
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