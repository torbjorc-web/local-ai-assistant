from collections.abc import Iterator

import ollama

from src.config import (
    EMBEDDING_MODEL,
    KEYWORD_WEIGHT,
    MEMORY_MIN_SIMILARITY,
    MEMORY_TOP_K,
    MODEL,
    SEMANTIC_WEIGHT,
    SYSTEM_PROMPT,
)
from src.embeddings import EmbeddingService
from src.memory import Memory
from src.rag import DocumentRAG


class Chatbot:
    def __init__(self):
        self.memory = Memory()
        self.embedding_service = EmbeddingService()
        self.document_rag = DocumentRAG()

        # Ny samtale opprettes først ved første melding.
        self.conversation_id = None

        self.messages = self._new_message_list()

        # Oppdateres etter hvert dokumentbaserte svar.
        self.last_document_sources = []

    # ---------------------------------------------------------
    # Base conversation setup
    # ---------------------------------------------------------

    def _new_message_list(self):
        return [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    def _ensure_conversation(self):
        if self.conversation_id is None:
            self.conversation_id = (
                self.memory.create_conversation()
            )

    # ---------------------------------------------------------
    # Long-term memory retrieval
    # ---------------------------------------------------------

    def _get_relevant_memories(
        self,
        user_input: str,
    ):
        query_embedding = (
            self.embedding_service.create_embedding(
                user_input
            )
        )

        return self.memory.search_memories(
            query=user_input,
            query_embedding=query_embedding,
            embedding_model=EMBEDDING_MODEL,
            top_k=MEMORY_TOP_K,
            min_similarity=MEMORY_MIN_SIMILARITY,
            semantic_weight=SEMANTIC_WEIGHT,
            keyword_weight=KEYWORD_WEIGHT,
        )

    # ---------------------------------------------------------
    # Document retrieval
    # ---------------------------------------------------------

    def _get_relevant_documents(
        self,
        user_input: str,
    ):
        return self.document_rag.search(
            user_input
        )

    def _build_context_message(
        self,
        relevant_memories,
        relevant_documents,
    ):
        context_sections = []

        if relevant_memories:
            memory_text = "\n".join(
                (
                    f"- [{memory['category']}] "
                    f"{memory['content']}"
                )
                for memory in relevant_memories
            )

            context_sections.append(
                "RELEVANTE LANGTIDSMINNER:\n"
                f"{memory_text}"
            )

        if relevant_documents:
            document_parts = []

            for index, document in enumerate(
                relevant_documents,
                start=1,
            ):
                page_number = document.get(
                    "page_number"
                )

                if page_number is None:
                    source_label = (
                        f"{document['file_name']}, "
                        f"del {document['chunk_index']}"
                    )
                else:
                    source_label = (
                        f"{document['file_name']}, "
                        f"side {page_number}, "
                        f"del {document['chunk_index']}"
                    )

                document_parts.append(
                    (
                        f"[Kilde {index}: {source_label}]\n"
                        f"{document['content']}"
                    )
                )

            document_text = "\n\n".join(
                document_parts
            )

            context_sections.append(
                "RELEVANTE DOKUMENTUTDRAG:\n"
                f"{document_text}"
            )

        if not context_sections:
            return None

        combined_context = "\n\n".join(
            context_sections
        )

        return {
            "role": "system",
            "content": (
                "Nedenfor finnes hentet kontekst som kan "
                "brukes til å svare på brukerens spørsmål.\n\n"
                f"{combined_context}\n\n"
                "Instruksjoner:\n"
                "- Bruk bare konteksten når den er relevant.\n"
                "- Ikke finn på informasjon som ikke finnes "
                "i konteksten eller samtalen.\n"
                "- Når dokumentutdrag brukes, oppgi kilden "
                "som [Kilde 1], [Kilde 2] og så videre.\n"
                "- Hvis dokumentene ikke inneholder svaret, "
                "si tydelig at svaret ikke finnes i de "
                "indekserte dokumentene."
            ),
        }

    def _get_messages_with_context(
        self,
        user_input: str,
    ):
        messages_with_context = (
            self.messages.copy()
        )

        relevant_memories = (
            self._get_relevant_memories(
                user_input
            )
        )

        relevant_documents = (
            self._get_relevant_documents(
                user_input
            )
        )

        self.last_document_sources = (
            relevant_documents
        )

        context_message = (
            self._build_context_message(
                relevant_memories,
                relevant_documents,
            )
        )

        if context_message is not None:
            # Grunnprompten ligger på indeks 0.
            # Hentet kontekst legges rett etter.
            messages_with_context.insert(
                1,
                context_message,
            )

        return messages_with_context

    # ---------------------------------------------------------
    # Chat
    # ---------------------------------------------------------

    def _begin_chat_turn(self, user_input: str):
        self._ensure_conversation()

        user_message = {
            "role": "user",
            "content": user_input,
        }

        self.messages.append(
            user_message
        )

        self.memory.save_message(
            self.conversation_id,
            "user",
            user_input,
        )

        messages_with_context = (
            self._get_messages_with_context(
                user_input
            )
        )
        return messages_with_context

    def _save_assistant_message(
        self,
        assistant_message: str,
    ):
        self.messages.append(
            {
                "role": "assistant",
                "content": assistant_message,
            }
        )

        self.memory.save_message(
            self.conversation_id,
            "assistant",
            assistant_message,
        )

    def chat(self, user_input: str) -> str:
        messages_with_context = (
            self._begin_chat_turn(user_input)
        )
        response = ollama.chat(
            model=MODEL,
            messages=messages_with_context,
        )

        assistant_message = (
            response.message.content
        )

        self._save_assistant_message(
            assistant_message
        )

        return assistant_message

    def chat_stream(
        self,
        user_input: str,
    ) -> Iterator[str]:
        messages_with_context = (
            self._begin_chat_turn(user_input)
        )
        response_stream = ollama.chat(
            model=MODEL,
            messages=messages_with_context,
            stream=True,
        )

        response_parts = []

        for response_chunk in response_stream:
            content = response_chunk.message.content

            if content:
                response_parts.append(content)
                yield content

        self._save_assistant_message(
            "".join(response_parts)
        )

    # ---------------------------------------------------------
    # Conversation management
    # ---------------------------------------------------------

    def clear_history(self):
        self.conversation_id = None
        self.messages = self._new_message_list()
        self.last_document_sources = []

    def list_conversations(self):
        return self.memory.list_conversations()

    def load_conversation(
        self,
        conversation_id: str,
    ) -> bool:
        if not self.memory.conversation_exists(
            conversation_id
        ):
            return False

        stored_messages = (
            self.memory.load_messages(
                conversation_id
            )
        )

        self.conversation_id = (
            conversation_id
        )

        self.messages = (
            self._new_message_list()
        )

        self.messages.extend(
            stored_messages
        )

        self.last_document_sources = []

        return True

    def cleanup_empty_conversations(self) -> int:
        return (
            self.memory.cleanup_empty_conversations()
        )

    # ---------------------------------------------------------
    # Long-term memory management
    # ---------------------------------------------------------

    def remember(
        self,
        content: str,
        category: str = "general",
    ) -> bool:
        embedding = (
            self.embedding_service.create_embedding(
                content
            )
        )

        return self.memory.save_memory(
            category=category,
            content=content,
            embedding=embedding,
            embedding_model=EMBEDDING_MODEL,
        )

    def list_memories(self):
        return self.memory.list_memories()

    def forget(
        self,
        memory_id: int,
    ) -> bool:
        return self.memory.delete_memory(
            memory_id
        )

    def reindex_memories(self) -> int:
        memories = (
            self.memory.get_memories_without_embeddings()
        )

        indexed_count = 0

        for memory_id, content in memories:
            embedding = (
                self.embedding_service.create_embedding(
                    content
                )
            )

            self.memory.update_memory_embedding(
                memory_id=memory_id,
                embedding=embedding,
                embedding_model=EMBEDDING_MODEL,
            )

            indexed_count += 1

        return indexed_count

    def search_memories(
        self,
        query: str,
    ):
        query_embedding = (
            self.embedding_service.create_embedding(
                query
            )
        )

        return self.memory.search_memories(
            query=query,
            query_embedding=query_embedding,
            embedding_model=EMBEDDING_MODEL,
            top_k=MEMORY_TOP_K,
            min_similarity=MEMORY_MIN_SIMILARITY,
            semantic_weight=SEMANTIC_WEIGHT,
            keyword_weight=KEYWORD_WEIGHT,
        )

    # ---------------------------------------------------------
    # Document management
    # ---------------------------------------------------------

    def index_documents(self):
        return (
            self.document_rag.index_all_documents()
        )

    def index_document(
        self,
        file_path,
    ) -> int:
        return self.document_rag.index_document(
            file_path
        )

    def list_documents(self):
        return (
            self.document_rag.list_documents()
        )

    def get_document(self, document_id: int):
        return self.document_rag.get_document(
            document_id
        )

    def search_documents(
        self,
        query: str,
    ):
        return self.document_rag.search(
            query
        )

    def delete_document(
        self,
        document_id: int,
    ) -> bool:
        return self.document_rag.delete_document(
            document_id
        )