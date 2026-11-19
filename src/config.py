from pathlib import Path


TESSERACT_COMMAND = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
OCR_LANGUAGES = "nor+eng"

MODEL = "gemma3:4b"

EMBEDDING_MODEL = "embeddinggemma"

MEMORY_TOP_K = 3
MEMORY_MIN_SIMILARITY = 0.30

SEMANTIC_WEIGHT = 0.70
KEYWORD_WEIGHT = 0.30

DOCUMENTS_PATH = Path("data/documents")

DOCUMENT_TOP_K = 4
DOCUMENT_MIN_SIMILARITY = 0.35

DOCUMENT_CHUNK_SIZE = 700
DOCUMENT_CHUNK_OVERLAP = 100

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
}

SYSTEM_PROMPT = (
    "Du er en hjelpsom lokal AI-assistent. "
    "Svar på samme språk som brukeren skriver."
)