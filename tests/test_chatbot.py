from types import SimpleNamespace

import src.chatbot as chatbot_module
from src.chatbot import Chatbot


def test_chat_stream_persists_complete_response(
    monkeypatch,
):
    saved_messages = []
    model_arguments = {}

    class FakeMemory:
        def create_conversation(self):
            return "streamed-conversation"

        def save_message(
            self,
            conversation_id,
            role,
            content,
        ):
            saved_messages.append(
                (conversation_id, role, content)
            )

    chatbot = object.__new__(Chatbot)
    chatbot.memory = FakeMemory()
    chatbot.conversation_id = None
    chatbot.messages = [
        {
            "role": "system",
            "content": "system prompt",
        }
    ]
    chatbot._get_messages_with_context = (
        lambda _message: chatbot.messages
    )

    def fake_chat(**kwargs):
        model_arguments.update(kwargs)
        return iter(
            [
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="Streaming "
                    )
                ),
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="response."
                    )
                ),
            ]
        )

    monkeypatch.setattr(
        chatbot_module.ollama,
        "chat",
        fake_chat,
    )

    chunks = list(chatbot.chat_stream("Question"))

    assert chunks == ["Streaming ", "response."]
    assert model_arguments["stream"] is True
    assert saved_messages == [
        (
            "streamed-conversation",
            "user",
            "Question",
        ),
        (
            "streamed-conversation",
            "assistant",
            "Streaming response.",
        ),
    ]
