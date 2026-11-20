# Local AI Assistant

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-black)](https://ollama.com/)
[![LLM](https://img.shields.io/badge/LLM-Gemma_3_4B-4285F4)](https://ollama.com/library/gemma3)
[![RAG](https://img.shields.io/badge/RAG-Document_Retrieval-7A1FA2)](#document-rag)
[![SQLite](https://img.shields.io/badge/SQLite-Persistent_Memory-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/torbjorc-web/local-ai-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/torbjorc-web/local-ai-assistant/actions/workflows/tests.yml)

A privacy-focused local AI assistant built with Python, Ollama, Gemma, SQLite, embeddings, hybrid retrieval, persistent memory, document RAG, PDF processing, and OCR.

The project explores how the main building blocks behind modern AI assistants can be implemented locally and combined into one understandable Python application.

---

## Highlights

- Local LLM through Ollama
- Gemma 3 4B for chat
- EmbeddingGemma for vector embeddings
- Persistent conversations in SQLite
- Persistent long-term memory
- Semantic memory search
- Hybrid semantic + keyword retrieval
- Conversation loading and resuming
- Local document indexing
- Markdown and text document support
- PDF document support
- Page-aware PDF retrieval
- OCR fallback for scanned PDFs
- Source-grounded RAG responses
- Local-first architecture
- No hosted LLM API required for the core application

---

## Why this project?

The goal is not simply to create another chatbot.

The project is designed to explore the engineering components behind a modern AI assistant:

```text
Local LLM
+
Conversation history
+
Persistent memory
+
Embeddings
+
Semantic search
+
Hybrid retrieval
+
Document processing
+
RAG
+
PDF extraction
+
OCR
+
SQLite
```

The architecture is deliberately modular so that individual components can be understood, tested, replaced, and improved independently.

---

# Architecture

```text
                         User
                           |
                           v
                      Python CLI
                           |
                           v
                        Chatbot
                           |
             +-------------+-------------+
             |                           |
             v                           v
      Long-term memory              Document RAG
             |                           |
             v                           v
          SQLite                 TXT / Markdown / PDF
             |                           |
             v                           v
      Hybrid retrieval               Extraction
             |                           |
             |                      +----+----+
             |                      |         |
             |                      v         v
             |                    Text       OCR
             |                      |         |
             |                      +----+----+
             |                           |
             |                           v
             |                        Chunking
             |                           |
             +-------------+-------------+
                           |
                           v
                    EmbeddingGemma
                           |
                           v
                     Vector search
                           |
                           v
                       Gemma 3 4B
                           |
                           v
                  Grounded AI response
```

---

# Technology stack

## AI

- Ollama
- Gemma 3 4B
- EmbeddingGemma

## Backend

- Python
- SQLite

## Retrieval

- vector embeddings
- semantic similarity
- keyword matching
- hybrid ranking
- similarity thresholds
- Top-K retrieval
- Retrieval-Augmented Generation

## Documents

- Markdown
- text files
- PDF
- PyMuPDF
- Tesseract OCR
- pytesseract
- Pillow

## Development

- Visual Studio Code
- Git
- GitHub
- Python virtual environments

---

# Features

## Local AI

The assistant runs Gemma 3 locally through Ollama.

Current chat model:

```text
gemma3:4b
```

Embedding model:

```text
embeddinggemma
```

The architecture keeps the core LLM workflow local.

---

# Conversation management

Each conversation receives a unique UUID.

Example:

```text
Conversation ID:
4673292a-5551-4796-974e-eb8e75c1baff
```

Conversation messages are stored in SQLite.

The assistant can:

- start conversations
- store messages
- list previous conversations
- load previous conversations
- resume previous conversations
- remove empty conversations

A conversation is created lazily when the first real message is sent, avoiding empty database records.

---

# Persistent long-term memory

Conversation history and long-term memory are intentionally separate.

For example:

```text
remember Favorittspillet mitt er Zelda.
```

stores a persistent memory.

Later:

```text
clear
```

followed by:

```text
Hva er favorittspillet mitt?
```

can still produce:

```text
AI: Zelda.
```

The memory persists even if the application is closed and restarted.

---

# Semantic memory search

Long-term memories are embedded using EmbeddingGemma.

The current embedding vectors contain:

```text
768 dimensions
```

This allows retrieval by meaning rather than only exact string matching.

Example:

```text
search-memory Hva vet du om programmeringsinteressene mine?
```

---

# Hybrid memory retrieval

Semantic similarity alone is not always enough.

The assistant therefore combines:

```text
70% semantic similarity
30% keyword similarity
```

This gives direct textual matches additional influence while preserving semantic retrieval.

Example:

```text
search-memory Hvilke spill liker jeg?
```

Example output:

```text
Hybride minner:

ID: 7
Kategori: general
Semantisk: 0.746
Nøkkelord: 1.000
Hybrid: 0.822
Minne: Jeg liker Zelda-spillene.

ID: 8
Kategori: general
Semantisk: 0.703
Nøkkelord: 1.000
Hybrid: 0.792
Minne: Jeg liker strategispillet Civilization.
```

This provides a simple hybrid retrieval system that combines conceptual similarity with direct term matching.

---

# Document RAG

The assistant includes a local Retrieval-Augmented Generation pipeline.

Supported formats:

```text
.txt
.md
.pdf
```

Documents are placed in:

```text
data/documents/
```

Example:

```text
data/
└── documents/
    ├── python_notes.md
    ├── azure_notes.txt
    ├── powerbi_notes.md
    └── machine_learning.pdf
```

---

# RAG pipeline

```text
Document
   |
   v
Text extraction
   |
   v
Chunking
   |
   v
EmbeddingGemma
   |
   v
Vector embeddings
   |
   v
SQLite
   |
   v
Semantic retrieval
   |
   v
Relevant chunks
   |
   v
Gemma 3
   |
   v
Grounded response
```

Instead of sending an entire document to the language model, the system retrieves the document chunks that are most relevant to the current question.

---

# Document chunking

Documents are divided into overlapping chunks before embeddings are generated.

Default configuration:

```text
Chunk size:    700 characters
Chunk overlap: 100 characters
```

Overlap helps preserve information around chunk boundaries.

---

# Document indexing

Documents can be indexed from the CLI:

```text
index-documents
```

Example:

```text
Indeksering ferdig:
- python_notes.md: 1 chunks
- azure_notes.txt: 2 chunks
- machine_learning.pdf: 8 chunks
```

The generated embeddings and chunk metadata are stored locally in SQLite.

---

# Document search

Retrieval can be tested without invoking the chat model.

Example:

```text
search-docs Hva bruker jeg Python til?
```

Example result:

```text
Dokumenttreff:

Fil: python_notes.md
Del: 0
Likhet: 0.708

Tekst:
Python er et programmeringsspråk ...
Jeg bruker Python til dataanalyse,
automatisering, maskinlæring og AI.
```

This makes the retrieval layer independently testable.

---

# RAG chat

Normal chat automatically searches indexed documents before generating the response.

Example:

```text
Du: Hva bruker jeg Python til?
```

Example response:

```text
AI: Basert på konteksten jeg har, bruker du Python
til dataanalyse, automatisering, maskinlæring og AI.

Dokumentkilder:
- python_notes.md (del 0, likhet 0.708)
```

This means the final response is grounded using retrieved local document content.

---

# PDF support

PDF files can be indexed together with Markdown and plain text files.

PDF text is extracted page by page.

Metadata associated with a PDF retrieval result can include:

```text
file name
page number
chunk number
similarity score
```

A source can therefore be displayed as:

```text
architecture.pdf
side 4
del 7
likhet 0.742
```

This makes retrieved PDF information traceable back to its source page.

---

# OCR support

Scanned PDFs may contain images rather than directly extractable text.

The OCR pipeline uses Tesseract as a fallback:

```text
PDF page
   |
   v
Normal text extraction
   |
   v
Enough text?
   |
   +------ Yes ------> Chunking
   |
   No
   |
   v
Render page
   |
   v
Tesseract OCR
   |
   v
OCR text
   |
   v
Chunking
   |
   v
EmbeddingGemma
   |
   v
RAG index
```

OCR is triggered when the normal PDF extraction returns too little usable text.

OCR languages are configurable.

Example:

```python
OCR_LANGUAGES = "eng"
```

With Norwegian language data installed:

```python
OCR_LANGUAGES = "nor+eng"
```

---

# CLI commands

## General

### Help

```text
help
```

Displays available commands.

### Exit

```text
exit
```

Exits the assistant.

---

## Conversations

### List conversations

```text
list
```

### Load a previous conversation

```text
load <conversation-id>
```

### Start a new conversation

```text
clear
```

### Remove empty conversations

```text
cleanup
```

---

## Long-term memory

### Save memory

```text
remember <text>
```

Example:

```text
remember Jeg liker Python.
```

### List memories

```text
memories
```

### Delete memory

```text
forget <id>
```

Example:

```text
forget 3
```

### Hybrid memory search

```text
search-memory <query>
```

Example:

```text
search-memory Hvilke spill liker jeg?
```

### Reindex older memories

```text
reindex-memory
```

Generates embeddings for memories created before embedding support was enabled.

---

## Documents

### List indexed documents

```text
documents
```

### Index documents

```text
index-documents
```

Indexes supported files under:

```text
data/documents/
```

### Search documents

```text
search-docs <query>
```

Example:

```text
search-docs Hva bruker jeg Python til?
```

### Delete a document from the RAG index

```text
delete-document <id>
```

This removes the document and associated chunks from SQLite.

It does not delete the original document file.

---

# Project structure

```text
local-ai-assistant/
│
├── data/
│   ├── assistant.db
│   └── documents/
│       └── .gitkeep
│
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── chatbot.py
│   ├── config.py
│   ├── memory.py
│   ├── embeddings.py
│   ├── document_store.py
│   └── rag.py
│
├── tests/
│
├── models/
│
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

---

# Database design

The project uses SQLite for persistence.

## `conversations`

Stores:

```text
conversation ID
creation timestamp
```

## `messages`

Stores:

```text
message ID
conversation ID
role
content
creation timestamp
```

## `memories`

Stores:

```text
memory ID
category
content
embedding
embedding model
creation timestamp
```

## `documents`

Stores metadata about indexed documents.

## `document_chunks`

Stores:

```text
document ID
chunk index
page number
content
embedding
embedding model
```

---

# Design principles

The project keeps three forms of context separate:

```text
Conversation history
       !=
Long-term memory
       !=
Document knowledge
```

### Conversation history

Represents what happened during a specific conversation.

### Long-term memory

Represents persistent information explicitly stored for use across conversations.

### Document knowledge

Represents retrievable knowledge from indexed local files.

This separation makes the architecture easier to understand, debug, test, and extend.

---

# Installation

## Requirements

- Python 3.13
- Ollama
- Git
- Optional: Tesseract OCR for scanned PDFs

---

## 1. Clone the repository

```bash
git clone https://github.com/torbjorc-web/local-ai-assistant.git
cd local-ai-assistant
```

---

## 2. Create a Python virtual environment

### Windows PowerShell

```powershell
python -m venv .venv
```

If PowerShell blocks activation scripts for the current process:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

Activate:

```powershell
.\.venv\Scripts\Activate.ps1
```

Verify:

```powershell
python -c "import sys; print(sys.executable)"
```

---

## 3. Install Python dependencies

```powershell
pip install -r requirements.txt
```

---

## 4. Install Ollama

After installing Ollama, verify:

```powershell
ollama --version
```

---

## 5. Download the models

Chat model:

```powershell
ollama pull gemma3:4b
```

Embedding model:

```powershell
ollama pull embeddinggemma
```

Verify:

```powershell
ollama list
```

---

# OCR installation

OCR is optional and only required for scanned PDFs.

The current Windows configuration expects Tesseract at:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Verify installation:

```powershell
tesseract --version
```

List available OCR languages:

```powershell
tesseract --list-langs
```

Example:

```text
eng
nor
osd
```

Configure languages in:

```text
src/config.py
```

For English:

```python
OCR_LANGUAGES = "eng"
```

For Norwegian and English:

```python
OCR_LANGUAGES = "nor+eng"
```

---

# Running

From the repository root:

```powershell
python -m src.main
```

Example:

```text
Local AI Assistant
Model: gemma3:4b
Conversation ID: ingen aktiv samtale
Skriv 'help' for å vise kommandoene.

Du:
```

---

# Privacy

The project is designed around local processing.

Sensitive local data should never be committed to Git.

This includes:

- conversation databases
- personal documents
- `.env` files
- API keys
- passwords
- locally downloaded models
- personal RAG data

Recommended `.gitignore` rules:

```gitignore
# Python
.venv/
__pycache__/
*.py[cod]

# Secrets
.env
.env.*

# VS Code
.vscode/

# Local databases
data/*.db
*.db

# Private RAG documents
*ata/doc*ments/*

# Preserve directory
!data/documents/.gitkeep

# Local models
models/

# Test output
.pytest_cache/
.coverage

# OS files
Thumbs.db
.DS_Store
```

---

# Current limitations

- CLI-only interface
- SQLite-based vector storage
- Vector comparison runs in Python
- No dedicated vector database
- OCR quality depends on installed Tesseract language models
- Complex PDF layouts may require improved layout-aware extraction
- OCR has not yet been fully evaluated against a larger scanned-document test set
- No authentication or multi-user support
- No web UI
- Limited automated testing
- Embedding and retrieval settings are currently configured in Python

---

# Roadmap

## AI and memory

- [x] Local LLM
- [x] Conversation context
- [x] SQLite conversation storage
- [x] Conversation IDs
- [x] Conversation resume
- [x] Persistent long-term memory
- [x] Semantic memory search
- [x] Hybrid semantic + keyword retrieval
- [ ] Automatic memory extraction
- [ ] Memory categories and filters
- [ ] Memory evaluation

## RAG

- [x] Markdown indexing
- [x] Text indexing
- [x] PDF text extraction
- [x] Chunking
- [x] Embeddings
- [x] Semantic document retrieval
- [x] Source-aware responses
- [x] PDF page metadata
- [ ] Complete OCR validation with scanned PDFs
- [ ] Improved PDF layout processing
- [ ] Smarter chunking strategies
- [ ] Automatic document change detection
- [ ] Retrieval evaluation dataset

## Application

- [x] CLI
- [ ] FastAPI backend
- [ ] Web interface
- [ ] Streaming responses
- [ ] Docker
- [ ] Environment-based configuration
- [ ] Structured logging

## Quality

- [ ] pytest test suite
- [ ] GitHub Actions
- [ ] Type checking
- [ ] Retrieval regression tests
- [ ] Error logging
- [ ] Configuration validation

## Machine Learning

Future development will include a traditional machine-learning component using scikit-learn.

Possible areas include:

- text classification
- relevance prediction
- job-description analysis
- similarity evaluation
- model training and validation
- comparison between classical ML and LLM-assisted analysis

The long-term goal is to demonstrate how three different approaches can work together:

```text
Traditional Machine Learning
          +
Embeddings / Retrieval
          +
Generative AI
```

---

# Security

Never commit sensitive information.

Before making the repository public, verify that Git does not track:

```text
.env
assistant.db
data/documents/*
.venv/
private credentials
API keys
```

Use:

```powershell
git status
```

before every public commit containing significant changes.

---

# License

This project is licensed under the MIT License.

See [LICENSE](LICENSE) for details.

---

# Author

**Torbjørn Carlsen**

GitHub: [torbjorc-web](https://github.com/torbjorc-web)