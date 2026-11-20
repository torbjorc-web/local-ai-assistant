import json
from pathlib import Path
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from src.config import (
    DOCUMENTS_PATH,
    MAX_UPLOAD_SIZE,
    SUPPORTED_DOCUMENT_EXTENSIONS,
)
from src.chatbot import Chatbot
from src.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    DeleteResponse,
    DocumentDetailResponse,
    DocumentIndexResult,
    DocumentResponse,
    DocumentSearchResponse,
    DocumentSourceResponse,
    DocumentUploadResponse,
    HealthResponse,
    MemoryCreateRequest,
    MemoryResponse,
    MessageResponse,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"


app = FastAPI(
    title="Local AI Assistant API",
    description=(
        "Local AI assistant API with persistent memory, "
        "hybrid retrieval, document RAG, PDF support, "
        "and OCR."
    ),
    version="0.1.0",
)

app.mount(
    "/web-assets",
    StaticFiles(
        directory=WEB_DIR,
    ),
    name="web-assets",
)


def get_chatbot() -> Chatbot:
    """
    Dependency used by the API.

    A new Chatbot instance is created for each request.
    Persistent state is loaded from SQLite.
    """
    return Chatbot()


ChatbotDependency = Annotated[
    Chatbot,
    Depends(get_chatbot),
]


@app.get(
    "/",
    include_in_schema=False,
)
def web_interface():
    return FileResponse(
        WEB_DIR / "index.html"
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
)
def health():
    return {
        "status": "ok",
        "application": "Local AI Assistant",
    }


@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Chat"],
)
def chat(
    request: ChatRequest,
    chatbot: ChatbotDependency,
):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty.",
        )

    if request.conversation_id is not None:
        loaded = chatbot.load_conversation(
            request.conversation_id
        )

        if not loaded:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )

    try:
        response = chatbot.chat(message)

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The local AI service could not "
                f"complete the request: {error}"
            ),
        ) from error

    sources = [
        DocumentSourceResponse(
            file_name=source["file_name"],
            chunk_index=source["chunk_index"],
            page_number=source.get("page_number"),
            similarity=source["similarity"],
        )
        for source in chatbot.last_document_sources
    ]

    return ChatResponse(
        response=response,
        conversation_id=chatbot.conversation_id,
        sources=sources,
    )


@app.post(
    "/chat/stream",
    tags=["Chat"],
)
def chat_stream(
    request: ChatRequest,
    chatbot: ChatbotDependency,
):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty.",
        )

    if request.conversation_id is not None:
        loaded = chatbot.load_conversation(
            request.conversation_id
        )

        if not loaded:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )

    def event_stream():
        try:
            for content in chatbot.chat_stream(message):
                yield (
                    json.dumps(
                        {
                            "type": "chunk",
                            "content": content,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except Exception as error:
            yield (
                json.dumps(
                    {
                        "type": "error",
                        "conversation_id": chatbot.conversation_id,
                        "detail": (
                            "The local AI service could "
                            f"not complete the request: {error}"
                        ),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            return

        sources = [
            {
                "file_name": source["file_name"],
                "chunk_index": source["chunk_index"],
                "page_number": source.get("page_number"),
                "similarity": source["similarity"],
            }
            for source in chatbot.last_document_sources
        ]
        yield (
            json.dumps(
                {
                    "type": "done",
                    "conversation_id": chatbot.conversation_id,
                    "sources": sources,
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


@app.get(
    "/conversations",
    response_model=list[ConversationResponse],
    tags=["Conversations"],
)
def list_conversations(
    chatbot: ChatbotDependency,
):
    rows = chatbot.list_conversations()

    return [
        ConversationResponse(
            id=conversation_id,
            created_at=created_at,
            message_count=message_count,
            first_message=first_message,
        )
        for (
            conversation_id,
            created_at,
            message_count,
            first_message,
        ) in rows
    ]


@app.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
    tags=["Conversations"],
)
def get_conversation_messages(
    conversation_id: str,
    chatbot: ChatbotDependency,
):
    if not chatbot.memory.conversation_exists(
        conversation_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    messages = chatbot.memory.load_messages(
        conversation_id
    )

    return [
        MessageResponse(
            role=message["role"],
            content=message["content"],
        )
        for message in messages
    ]


@app.post(
    "/conversations/cleanup",
    response_model=dict[str, int],
    tags=["Conversations"],
)
def cleanup_conversations(
    chatbot: ChatbotDependency,
):
    deleted_count = (
        chatbot.cleanup_empty_conversations()
    )

    return {
        "deleted_count": deleted_count,
    }


@app.get(
    "/memories",
    response_model=list[MemoryResponse],
    tags=["Memory"],
)
def list_memories(
    chatbot: ChatbotDependency,
):
    rows = chatbot.list_memories()

    return [
        MemoryResponse(
            id=memory_id,
            category=category,
            content=content,
            created_at=created_at,
        )
        for (
            memory_id,
            category,
            content,
            created_at,
        ) in rows
    ]


@app.post(
    "/memories",
    response_model=dict[str, bool],
    status_code=status.HTTP_201_CREATED,
    tags=["Memory"],
)
def create_memory(
    request: MemoryCreateRequest,
    chatbot: ChatbotDependency,
):
    try:
        saved = chatbot.remember(
            content=request.content.strip(),
            category=request.category.strip(),
        )

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The memory embedding could not "
                f"be created: {error}"
            ),
        ) from error

    if not saved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This memory already exists.",
        )

    return {
        "saved": True,
    }


@app.delete(
    "/memories/{memory_id}",
    response_model=DeleteResponse,
    tags=["Memory"],
)
def delete_memory(
    memory_id: int,
    chatbot: ChatbotDependency,
):
    deleted = chatbot.forget(memory_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found.",
        )

    return DeleteResponse(
        deleted=True,
    )


@app.get(
    "/documents",
    response_model=list[DocumentResponse],
    tags=["Documents"],
)
def list_documents(
    chatbot: ChatbotDependency,
):
    rows = chatbot.list_documents()

    return [
        DocumentResponse(
            id=document_id,
            file_name=file_name,
            file_path=file_path,
            chunk_count=chunk_count,
            updated_at=updated_at,
            page_count=page_count,
            file_size=file_size,
            used_ocr=bool(used_ocr),
            extraction_method=extraction_method,
            ocr_pages=json.loads(ocr_pages),
        )
        for (
            document_id,
            file_name,
            file_path,
            chunk_count,
            updated_at,
            page_count,
            file_size,
            used_ocr,
            extraction_method,
            ocr_pages,
        ) in rows
    ]


@app.post(
    "/documents/index",
    response_model=list[DocumentIndexResult],
    tags=["Documents"],
)
def index_documents(
    chatbot: ChatbotDependency,
):
    try:
        results = chatbot.index_documents()

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Document indexing failed: "
                f"{error}"
            ),
        ) from error

    return [
        DocumentIndexResult(
            file_name=result["file_name"],
            chunk_count=result["chunk_count"],
            status=result["status"],
            used_ocr=result.get(
                "used_ocr",
                False,
            ),
            error=result.get("error"),
        )
        for result in results
    ]


@app.get(
    "/documents/search",
    response_model=list[DocumentSearchResponse],
    tags=["Documents"],
)
def search_documents(
    query: Annotated[
        str,
        Query(
            min_length=1,
            max_length=5_000,
        ),
    ],
    chatbot: ChatbotDependency,
):
    try:
        results = chatbot.search_documents(
            query.strip()
        )

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Document retrieval failed: "
                f"{error}"
            ),
        ) from error

    return [
        DocumentSearchResponse(
            file_name=result["file_name"],
            file_path=result["file_path"],
            chunk_index=result["chunk_index"],
            page_number=result.get("page_number"),
            content=result["content"],
            similarity=result["similarity"],
        )
        for result in results
    ]


@app.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    tags=["Documents"],
)
def get_document(
    document_id: int,
    chatbot: ChatbotDependency,
):
    document = chatbot.get_document(document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return DocumentDetailResponse(**document)


@app.delete(
    "/documents/{document_id}",
    response_model=DeleteResponse,
    tags=["Documents"],
)
def delete_document(
    document_id: int,
    chatbot: ChatbotDependency,
):
    deleted = chatbot.delete_document(
        document_id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return DeleteResponse(
        deleted=True,
    )


@app.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Documents"],
)
async def upload_document(
    file: Annotated[
        UploadFile,
        File(...),
    ],
    chatbot: ChatbotDependency,
):
    original_name = (
        file.filename
        or ""
    ).strip()

    if not original_name:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail="File name is missing.",
        )

    normalized_name = original_name.replace(
        "\\",
        "/",
    )

    safe_name = normalized_name.split("/")[-1]

    if (
        not safe_name
        or safe_name in {".", ".."}
        or "\x00" in safe_name
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail="Invalid file name.",
        )

    extension = Path(
        safe_name
    ).suffix.lower()

    if extension not in (
        SUPPORTED_DOCUMENT_EXTENSIONS
    ):
        supported = ", ".join(
            sorted(
                SUPPORTED_DOCUMENT_EXTENSIONS
            )
        )

        raise HTTPException(
            status_code=(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            ),
            detail=(
                "Unsupported document type. "
                f"Supported types: {supported}"
            ),
        )

    DOCUMENTS_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        DOCUMENTS_PATH / safe_name
    )

    if destination.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A document with this file name "
                "already exists."
            ),
        )

    temporary_destination = (
        DOCUMENTS_PATH
        / f".{safe_name}.uploading"
    )

    total_size = 0

    try:
        with temporary_destination.open(
            "wb"
        ) as output_file:
            while True:
                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=(
                            status.HTTP_413_CONTENT_TOO_LARGE
                        ),
                        detail=(
                            "The uploaded file is "
                            "larger than the allowed limit."
                        ),
                    )

                output_file.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail="The uploaded file is empty.",
            )

        temporary_destination.replace(
            destination
        )

        try:
            chunk_count = (
                chatbot.index_document(
                    destination
                )
            )

        except Exception as error:
            destination.unlink(
                missing_ok=True
            )

            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "The document was uploaded, "
                    "but indexing failed: "
                    f"{error}"
                ),
            ) from error

        return DocumentUploadResponse(
            file_name=safe_name,
            file_size=total_size,
            chunk_count=chunk_count,
            status="indexed",
        )

    finally:
        await file.close()

        temporary_destination.unlink(
            missing_ok=True
        )