from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    application: str


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=10_000,
    )

    conversation_id: str | None = None


class DocumentSourceResponse(BaseModel):
    file_name: str
    chunk_index: int
    page_number: int | None
    similarity: float


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: list[DocumentSourceResponse]


class ConversationResponse(BaseModel):
    id: str
    created_at: str
    message_count: int
    first_message: str


class MessageResponse(BaseModel):
    role: str
    content: str


class MemoryCreateRequest(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=5_000,
    )

    category: str = Field(
        default="general",
        min_length=1,
        max_length=100,
    )


class MemoryResponse(BaseModel):
    id: int
    category: str
    content: str
    created_at: str


class DeleteResponse(BaseModel):
    deleted: bool


class DocumentResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    chunk_count: int
    updated_at: str


class DocumentSearchResponse(BaseModel):
    file_name: str
    file_path: str
    chunk_index: int
    page_number: int | None
    content: str
    similarity: float


class DocumentIndexResult(BaseModel):
    file_name: str
    chunk_count: int
    status: str
    used_ocr: bool = False
    error: str | None = None