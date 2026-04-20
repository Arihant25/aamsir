# AAMSIR — Adaptive Architecture for Multi-Strategy Information Retrieval

## Team 5 | S26CS6.401 — Software Engineering | Project 3

AAMSIR is an on-premise, privacy-safe document retrieval system that lets users ask natural-language questions over private document corpora and receive grounded answers with cited sources. It combines three interchangeable retrieval strategies — syntactic (BM25), semantic (vector similarity), and agentic (LLM-driven) — all running locally.

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                   Next.js Frontend (Port 3000)              │
│   Query Dashboard │ Document Management │ Settings/Analytics│
└───────────────────────────┬─────────────────────────────────┘
                            │ REST API
┌───────────────────────────▼─────────────────────────────────┐
│                FastAPI Backend (Port 8000)                  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Orchestrator (Microkernel)              │   │
│  │  ┌────────────┐ ┌──────────────┐ ┌────────────────┐  │   │
│  │  │ Syntactic  │ │  Semantic    │ │   Agentic      │  │   │
│  │  │ (BM25)     │ │  (ChromaDB)  │ │   (Ollama)     │  │   │
│  │  └────────────┘ └──────────────┘ └────────────────┘  │   │
│  │              Context Aggregator (RRF)                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │     Ingestion Pipeline (Pipe-and-Filter)             │   │
│  │   Extract → Summarize → Chunk → Embed → Index        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│      ┌──────────────┐         ┌──────────────┐              │
│      │   SQLite     │         │   ChromaDB   │              │
│      │ (metadata)   │         │  (vectors)   │              │
│      └──────────────┘         └──────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

| Tool    | Version           | Install                                            |
| ------- | ----------------- | -------------------------------------------------- |
| Python  | 3.11+             | [python.org](https://www.python.org/)              |
| uv      | latest            | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 18+               | [nodejs.org](https://nodejs.org/)                  |
| npm     | 8+                | Bundled with Node.js                               |
| Ollama  | latest (optional) | `brew install ollama`                              |

## Quick Start

> All commands assume you start from the **repository root** (`aamsir/`).

### Step 1 — Install backend dependencies

```bash
cd Task4/backend
uv sync
```

### Step 2 — Seed sample documents

```bash
cd Task4/backend
uv run python seed.py
```

This ingests 5 sample university policy documents (leave policy, travel reimbursement, graduation requirements, IT security, research funding) into SQLite + ChromaDB.

### Step 3 — Start the backend server

```bash
cd Task4/backend
uv run uvicorn src.aamsir.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be running at [http://localhost:8000](http://localhost:8000). Interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs).

### Step 4 — Install frontend dependencies (new terminal)

```bash
cd Task4/frontend
npm install
```

### Step 5 — Start the frontend

```bash
cd Task4/frontend
npm run dev
```

Frontend will be running at [http://localhost:3000](http://localhost:3000).

### Step 6 (Optional) — Enable LLM features with Ollama

```bash
brew install ollama
ollama pull qwen2.5:7b
ollama serve
```

Then restart the backend. With Ollama running, AAMSIR will:

- Enable the **Agentic** retrieval strategy (LLM-powered document reasoning)
- Generate natural-language answers (instead of extractive summaries)
- Perform **conversational query rewriting** — follow-up queries are rewritten into standalone search queries using conversation history before retrieval

---

## One-Liner (Copy-Paste)

**Terminal 1 — Backend:**

```bash
cd Task4/backend && uv sync && uv run python seed.py && uv run uvicorn src.aamsir.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Note:** Without Ollama the system still works fully — syntactic and semantic retrieval run locally without any LLM. Ollama is only needed for the Agentic strategy, LLM-generated answers, and conversational query rewriting.

**Terminal 2 — Frontend:**

```bash
cd Task4/frontend && npm install && npm run dev
```

Then open [http://localhost:3000](http://localhost:3000) in your browser.

---

## API Endpoints

| Method     | Endpoint                       | Description                                                  |
| ---------- | ------------------------------ | ------------------------------------------------------------ |
| `GET`      | `/api/health`                  | Health check and available strategies                        |
| `POST`     | `/api/query`                   | Submit a query (blocking, returns complete response)         |
| `POST`     | `/api/query/stream`            | SSE streaming — emits rewrite, sources, token, done events   |
| `POST`     | `/api/documents/upload`        | Upload a document for ingestion                              |
| `GET`      | `/api/documents`               | List all ingested documents                                  |
| `GET`      | `/api/documents/{id}`          | Get document details and full content                        |
| `GET`      | `/api/documents/{id}/download` | Serve original file inline (PDF/TXT/MD preview)              |
| `DELETE`   | `/api/documents/{id}`          | Remove a document and its vectors                            |
| `POST`     | `/api/feedback`                | Submit user feedback (helpful / not helpful)                 |
| `GET`      | `/api/config`                  | Get current configuration                                    |
| `PUT`      | `/api/config`                  | Update enabled strategies                                    |
| `GET`      | `/api/stats`                   | System analytics and usage statistics                        |

## Project Structure

```text
Task4/
├── README.md                          # This file
├── .gitignore
│
├── backend/
│   ├── pyproject.toml                 # Python dependencies (uv)
│   ├── seed.py                        # Sample document seeder
│   ├── benchmark.py                   # Latency/throughput benchmarking
│   ├── data/
│   │   └── sample_docs/              # 5 bundled university policy docs
│   └── src/aamsir/
│       ├── main.py                    # FastAPI app entry point
│       ├── config.py                  # Centralized configuration
│       ├── database.py               # SQLAlchemy models (SQLite)
│       ├── models.py                 # Pydantic request/response schemas
│       ├── api/
│       │   └── routes.py             # REST API endpoints (Facade)
│       ├── ingestion/
│       │   ├── extractors.py         # Text extractors (Adapter Pattern)
│       │   └── pipeline.py           # Ingestion pipeline (Pipe-and-Filter)
│       └── retrieval/
│           ├── strategy.py           # RetrievalStrategy interface
│           ├── syntactic.py          # BM25 keyword retriever
│           ├── semantic.py           # Vector similarity + Chain of Resp.
│           ├── agentic.py            # LLM retriever + Caching Proxy
│           ├── factory.py            # StrategyFactory
│           └── orchestrator.py       # Microkernel Orchestrator + RRF
│
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx              # Query chatbot interface
│       │   ├── documents/page.tsx    # Document management (upload/delete)
│       │   └── settings/page.tsx     # Strategy config + analytics
│       ├── components/
│       │   └── Sidebar.tsx           # Navigation sidebar
│       └── lib/
│           └── api.ts               # Backend API client
│
└── analysis/
    └── architecture_analysis.md      # Microkernel vs Monolithic comparison
```

## Design Patterns Implemented

| Pattern                     | File                        | Purpose                                   |
| --------------------------- | --------------------------- | ----------------------------------------- |
| **Strategy**                | `retrieval/strategy.py`     | Polymorphic retrieval algorithm selection |
| **Microkernel**             | `retrieval/orchestrator.py` | Plugin-based engine with fault isolation  |
| **Factory**                 | `retrieval/factory.py`      | Decoupled strategy instantiation          |
| **Chain of Responsibility** | `retrieval/semantic.py`     | Cascading semantic filter pipeline        |
| **Adapter**                 | `ingestion/extractors.py`   | Uniform document format extraction        |
| **Proxy (Caching)**         | `retrieval/agentic.py`      | LRU cache for expensive agentic retrieval |
| **Pipe-and-Filter**         | `ingestion/pipeline.py`     | Linear document ingestion pipeline        |
| **Facade**                  | `api/routes.py`             | Single API entry point                    |
| **Singleton**               | `ingestion/pipeline.py`     | Embedding model loaded once, reused       |

## Running Benchmarks

```bash
cd Task4/backend
uv run python benchmark.py
```

Runs 20 queries across strategy configurations and reports P50/P95/P99 latency and throughput.

## Supported Document Formats

| Extension | Handler              | Notes                                                  |
| --------- | -------------------- | ------------------------------------------------------ |
| `.pdf`    | `PdfExtractor`       | Text layer + table fallback; warns on image-only pages |
| `.txt`    | `PlainTextExtractor` | UTF-8 plain text                                       |
| `.md`     | `MarkdownExtractor`  | Markdown (headings preserved)                          |

New formats: implement `TextExtractor` in `ingestion/extractors.py` and register with `ExtractorRegistry`.
