import json
import re
import sqlite3
import uuid
from pathlib import Path


DB_PATH = Path("data/assistant.db")


class Memory:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        self._create_tables()
        self._migrate_memories_table()

    def _connect(self):
        connection = sqlite3.connect(DB_PATH)
        connection.execute("PRAGMA foreign_keys = ON")

        return connection

    # ---------------------------------------------------------
    # Database setup
    # ---------------------------------------------------------

    def _create_tables(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at DATETIME
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME
                        DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (conversation_id)
                        REFERENCES conversations(id)
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL UNIQUE,
                    embedding TEXT,
                    embedding_model TEXT,
                    created_at DATETIME
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _migrate_memories_table(self):
        with self._connect() as connection:
            columns = connection.execute(
                """
                PRAGMA table_info(memories)
                """
            ).fetchall()

            column_names = {
                column[1]
                for column in columns
            }

            if "embedding" not in column_names:
                connection.execute(
                    """
                    ALTER TABLE memories
                    ADD COLUMN embedding TEXT
                    """
                )

            if "embedding_model" not in column_names:
                connection.execute(
                    """
                    ALTER TABLE memories
                    ADD COLUMN embedding_model TEXT
                    """
                )

    # ---------------------------------------------------------
    # Conversations
    # ---------------------------------------------------------

    def create_conversation(self) -> str:
        conversation_id = str(uuid.uuid4())

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (id)
                VALUES (?)
                """,
                (conversation_id,),
            )

        return conversation_id

    def conversation_exists(
        self,
        conversation_id: str,
    ) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()

        return row is not None

    def list_conversations(self):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.id,
                    c.created_at,
                    COUNT(m.id) AS message_count,
                    COALESCE(
                        (
                            SELECT content
                            FROM messages
                            WHERE conversation_id = c.id
                              AND role = 'user'
                            ORDER BY id
                            LIMIT 1
                        ),
                        '(tom samtale)'
                    ) AS first_message

                FROM conversations AS c

                LEFT JOIN messages AS m
                    ON m.conversation_id = c.id

                GROUP BY
                    c.id,
                    c.created_at

                ORDER BY
                    c.created_at DESC
                """
            ).fetchall()

        return rows

    def cleanup_empty_conversations(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM conversations
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM messages
                    WHERE messages.conversation_id =
                          conversations.id
                )
                """
            )

            return cursor.rowcount

    # ---------------------------------------------------------
    # Messages
    # ---------------------------------------------------------

    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO messages (
                    conversation_id,
                    role,
                    content
                )
                VALUES (?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    content,
                ),
            )

    def load_messages(
        self,
        conversation_id: str,
    ):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    role,
                    content

                FROM messages

                WHERE conversation_id = ?

                ORDER BY id
                """,
                (conversation_id,),
            ).fetchall()

        return [
            {
                "role": role,
                "content": content,
            }
            for role, content in rows
        ]

    # ---------------------------------------------------------
    # Long-term memory
    # ---------------------------------------------------------

    def save_memory(
        self,
        category: str,
        content: str,
        embedding: list[float],
        embedding_model: str,
    ) -> bool:
        embedding_json = json.dumps(embedding)

        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO memories (
                        category,
                        content,
                        embedding,
                        embedding_model
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        category,
                        content,
                        embedding_json,
                        embedding_model,
                    ),
                )

            return True

        except sqlite3.IntegrityError:
            return False

    def list_memories(self):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    category,
                    content,
                    created_at

                FROM memories

                ORDER BY id
                """
            ).fetchall()

        return rows

    def get_memories_without_embeddings(self):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    content

                FROM memories

                WHERE embedding IS NULL
                   OR embedding = ''

                ORDER BY id
                """
            ).fetchall()

        return rows

    def update_memory_embedding(
        self,
        memory_id: int,
        embedding: list[float],
        embedding_model: str,
    ):
        embedding_json = json.dumps(embedding)

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE memories

                SET
                    embedding = ?,
                    embedding_model = ?

                WHERE id = ?
                """,
                (
                    embedding_json,
                    embedding_model,
                    memory_id,
                ),
            )

    # ---------------------------------------------------------
    # Hybrid search helpers
    # ---------------------------------------------------------

    def _tokenize(
        self,
        text: str,
    ) -> set[str]:
        stopwords = {
            "jeg",
            "meg",
            "min",
            "mitt",
            "mine",
            "du",
            "deg",
            "din",
            "ditt",
            "dine",
            "er",
            "et",
            "en",
            "og",
            "eller",
            "om",
            "på",
            "i",
            "av",
            "til",
            "for",
            "med",
            "som",
            "det",
            "den",
            "de",
            "hva",
            "hvilke",
            "hvilken",
            "vet",
            "liker",
        }

        words = re.findall(
            r"\b[\wæøåÆØÅ]+\b",
            text.lower(),
        )

        return {
            word
            for word in words
            if len(word) >= 3
            and word not in stopwords
        }

    def _keyword_similarity(
        self,
        query: str,
        content: str,
    ) -> float:
        query_tokens = self._tokenize(query)
        content_tokens = self._tokenize(content)

        if not query_tokens or not content_tokens:
            return 0.0

        matched_query_tokens = 0

        for query_token in query_tokens:
            matched = any(
                query_token in content_token
                or content_token in query_token
                for content_token in content_tokens
            )

            if matched:
                matched_query_tokens += 1

        return (
            matched_query_tokens
            / len(query_tokens)
        )

    # ---------------------------------------------------------
    # Hybrid semantic + keyword memory search
    # ---------------------------------------------------------

    def search_memories(
        self,
        query: str,
        query_embedding: list[float],
        embedding_model: str,
        top_k: int = 3,
        min_similarity: float = 0.30,
        semantic_weight: float = 0.70,
        keyword_weight: float = 0.30,
    ):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    category,
                    content,
                    embedding

                FROM memories

                WHERE embedding IS NOT NULL
                  AND embedding != ''
                  AND embedding_model = ?
                """,
                (embedding_model,),
            ).fetchall()

        scored_memories = []

        for (
            memory_id,
            category,
            content,
            embedding_json,
        ) in rows:
            stored_embedding = json.loads(
                embedding_json
            )

            if len(stored_embedding) != len(
                query_embedding
            ):
                continue

            # Embedding-score
            semantic_score = sum(
                query_value * memory_value
                for query_value, memory_value
                in zip(
                    query_embedding,
                    stored_embedding,
                )
            )

            # Vanlig tekst-/nøkkelordscore
            keyword_score = self._keyword_similarity(
                query,
                content,
            )

            # Kombinert score
            hybrid_score = (
                semantic_weight * semantic_score
                + keyword_weight * keyword_score
            )

            if hybrid_score < min_similarity:
                continue

            scored_memories.append(
                {
                    "id": memory_id,
                    "category": category,
                    "content": content,
                    "semantic_score": semantic_score,
                    "keyword_score": keyword_score,
                    "hybrid_score": hybrid_score,
                }
            )

        scored_memories.sort(
            key=lambda memory: memory["hybrid_score"],
            reverse=True,
        )

        return scored_memories[:top_k]

    # ---------------------------------------------------------
    # Delete memory
    # ---------------------------------------------------------

    def delete_memory(
        self,
        memory_id: int,
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM memories
                WHERE id = ?
                """,
                (memory_id,),
            )

            return cursor.rowcount > 0