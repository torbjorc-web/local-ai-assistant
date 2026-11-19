import ollama

from src.config import EMBEDDING_MODEL


class EmbeddingService:
    def __init__(self):
        self.model = EMBEDDING_MODEL

    def create_embedding(self, text: str) -> list[float]:
        response = ollama.embed(
            model=self.model,
            input=text,
        )

        embeddings = response["embeddings"]

        if not embeddings:
            raise ValueError(
                "Embeddingmodellen returnerte ingen vektor."
            )

        return embeddings[0]