# AAMSIR Technical Report

**Adaptive Architecture for Multi-Strategy Information Retrieval**

Team 5 | S26CS6.401 — Software Engineering | Project 3

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Task 1: Requirements and Subsystems](#2-task-1-requirements-and-subsystems)
3. [Task 2: Architecture Framework](#3-task-2-architecture-framework)
4. [Task 3: Architectural Tactics and Patterns](#4-task-3-architectural-tactics-and-patterns)
5. [Task 4: Prototype Implementation and Analysis](#5-task-4-prototype-implementation-and-analysis)
6. [Reflections and Lessons Learned](#6-reflections-and-lessons-learned)
7. [Individual Contributions](#7-individual-contributions)
8. [References](#8-references)

---

## 1. Introduction

### 1.1 Problem Statement

Institutions accumulate large volumes of internal documents — policies, SOPs, guidelines, and knowledge bases — that employees frequently need to query. Existing solutions are either too shallow (keyword search misses semantically related content) or privacy-compromising (cloud-hosted LLMs require sensitive documents to leave the organization's network).

### 1.2 Solution: AAMSIR

AAMSIR (Adaptive Architecture for Multi-Strategy Information Retrieval) addresses this gap with a chatbot-style interface backed by three interchangeable retrieval strategies — syntactic, semantic, and agentic — all running on compact, on-premise models to preserve institutional privacy.

### 1.3 Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, uv (package manager) |
| Vector Database | ChromaDB (embedded, on-premise) |
| Relational Database | SQLite (via SQLAlchemy) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Keyword Search | rank_bm25 |
| LLM (Optional) | Ollama (qwen2.5:7b) |
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| PDF Extraction | pdfplumber |

---

## 2. Task 1: Requirements and Subsystems

### 2.1 Functional Requirements

| ID | Requirement | Architectural Significance |
|----|------------|---------------------------|
| FR-01 | Query Interface Dashboard | Drives the Facade pattern (single API entry point) |
| FR-02 | Result Exploration with source snippets and inline document preview | Requires chunked storage, metadata tracking, and file-serving endpoint |
| FR-03 | User Feedback Module (helpful/not helpful) | Requires persistence layer and analytics |
| FR-04 | Multi-Modal Retrieval (Syntactic, Semantic, Agentic) | Drives Strategy Pattern and Microkernel |
| FR-05 | Retrieval Configuration Panel | Drives runtime strategy switching |
| FR-06 | Document Management Module | Drives Pipe-and-Filter ingestion pipeline |
| FR-07 | Conversational Query Refinement | Drives two-phase LLM invocation: rewrite query → retrieve → generate |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|------------|--------|
| NFR-01 | Latency | P95 ≤ 15 seconds |
| NFR-02 | Throughput | ≥ 50 concurrent users |
| NFR-03 | Scalability | 10,000 indexed documents |
| NFR-04 | Availability | ≥ 99% during working hours |
| NFR-05 | Modifiability | New strategies in < 100 person-hours |
| NFR-06 | Data Security | 100% on-premise, AES-256 at rest |

### 2.3 Architecturally Significant Requirements

- **ASR-01 (Extensibility):** Drove adoption of Microkernel + Strategy Pattern
- **ASR-02 (Latency via Context Limitation):** Drove Chain of Responsibility in semantic retrieval
- **ASR-03 (Scalability of Ingestion):** Drove Pipe-and-Filter architecture
- **ASR-04 (Fault Tolerance):** Drove plugin sandboxing in the Microkernel

### 2.4 Subsystem Overview

The system is divided into five subsystems:

1. **Presentation Layer:** Next.js web dashboard with query interface, document management, and settings
2. **Document Ingestion Pipeline:** Pipe-and-Filter architecture for Extract → Summarize → Chunk → Embed → Index
3. **Hybrid Retrieval Engine:** Microkernel with Syntactic, Semantic, and Agentic strategy plugins
4. **Generation & Orchestration Layer:** Orchestrator (Facade), Context Aggregator (RRF), answer generation
5. **Data Persistence Layer:** SQLite for metadata/feedback, ChromaDB for vector embeddings

---

## 3. Task 2: Architecture Framework

### 3.1 Stakeholder Identification (IEEE 42010)

| Stakeholder | Concerns |
|-------------|----------|
| End Users (Researchers/Students) | Precision, Latency, Usability, Trustworthiness |
| System Administrators | Deployability, Availability, Resource Efficiency |
| Course Instructors/Evaluators | Compliance, Modularity, Design Pattern Correctness |
| Developers/Maintenance Team | Modifiability, Testability, Maintainability |
| Data Owners/Content Providers | Data Integrity, Confidentiality |

### 3.2 Architecture Decision Records (ADRs)

**ADR-001: Microkernel for Retrieval Engine**
- *Context:* Multiple evolving retrieval strategies require independent addition/removal
- *Decision:* Adopt Microkernel (Plugin) Architecture
- *Consequences:* Open/Closed Principle satisfied; fault isolation; simplified testing
- *Alternatives Rejected:* Monolithic Controller (violates OCP), Microservices (excessive overhead)

**ADR-002: Pipe-and-Filter for Ingestion**
- *Context:* Document ingestion involves fixed-order transformations that need flexible step swapping
- *Decision:* Implement Pipe-and-Filter Architecture
- *Consequences:* Loose coupling, supports parallelism, maintainability
- *Alternatives Rejected:* Batch Script (monolithic failure), Event-Driven (excessive complexity)

**ADR-003: Strategy Pattern for Retrieval Algorithms**
- *Context:* Three different retrieval algorithms need runtime interchangeability
- *Decision:* Implement Strategy Pattern with `RetrievalStrategy` interface
- *Consequences:* Clean separation, independently testable, OCP compliance
- *Alternatives Rejected:* Conditional Logic (violates OCP), Template Method (algorithms differ too much)

**ADR-004: Broker Pattern with Scheduler**
- *Context:* Multiple concurrent requests competing for limited GPU resources
- *Decision:* Implement Broker Pattern with task queue and worker pool
- *Consequences:* Asynchronous processing, load management, resilience
- *Alternatives Rejected:* Direct Sync Calls (blocking), Observer Pattern (inefficient load balancing)

---

## 4. Task 3: Architectural Tactics and Patterns

### 4.1 Architectural Tactics

| # | Tactic | Category | NFR Addressed |
|---|--------|----------|---------------|
| 1 | Caching Proxy | Performance | NFR-01 (Latency) |
| 2 | Cascading / Progressive Narrowing | Performance | NFR-01 (Latency) |
| 3 | Fault Isolation via Plugin Sandboxing | Availability | NFR-04 (Uptime) |
| 4 | Horizontal Scaling of Stateless Filters | Scalability | NFR-03 (10K docs) |
| 5 | Task Queuing with Resource Pooling | Throughput | NFR-02 (50 users) |

### 4.2 Implementation Patterns

**Pattern 1: Strategy Pattern** — Defines a common `RetrievalStrategy` interface. Concrete implementations (Syntactic, Semantic, Agentic) are registered with the Orchestrator via `StrategyFactory.create()`. The Orchestrator invokes them polymorphically without type checks.

**Pattern 2: Chain of Responsibility** — The `SemanticRetriever` builds a filter chain: `TitleMatchHandler → SummarySimHandler → ContentSimHandler`. Each handler progressively narrows the candidate set using increasingly expensive operations, reducing full-content vector comparisons by ~99%.

---

## 5. Task 4: Prototype Implementation and Analysis

### 5.1 Prototype Overview

The prototype implements a **complete end-to-end query-answer pipeline**:

1. User uploads documents via the web dashboard
2. Documents are ingested through the Pipe-and-Filter pipeline (Extract → Summarize → Chunk → Embed → Index)
3. User submits natural-language queries
4. The Orchestrator invokes selected retrieval strategies in parallel with fault isolation
5. Results are merged using Reciprocal Rank Fusion (RRF)
6. An answer is generated (LLM if Ollama available, extractive otherwise)
7. Sources with citations are displayed
8. User can provide feedback (helpful/not helpful)

### 5.2 Key Implementation Details

#### 5.2.1 Document Ingestion (Pipe-and-Filter + Adapter)

The ingestion pipeline implements ADR-002 as five stateless filter functions operating on a `DocumentEnvelope`:

```
extract_text() → summarize() → chunk_text() → embed_chunks() → index_document()
```

The text extraction filter uses the **Adapter Pattern** (`ExtractorRegistry`) to dynamically select the correct format handler at runtime. Adding support for a new format (e.g., `.docx`) requires only implementing the `TextExtractor` interface and registering it — no pipeline code changes.

#### 5.2.2 Retrieval Engine (Microkernel + Strategy)

The `Orchestrator` manages three retrieval plugins registered via `StrategyFactory`:

- **SyntacticRetriever:** Rebuilds a BM25 index over paragraph-level chunks at query time. Applies a 50%-of-top-score threshold to filter noise before returning results. Average latency: ~2ms.
- **SemanticRetriever:** Adaptive — for corpora under 100 documents it queries ChromaDB directly with a 60%-similarity cutoff; for larger corpora it engages the full Chain of Responsibility pipeline (TitleMatch → SummarySim → ContentSim), reducing candidate sets by ~99% before the expensive vector comparison stage. Average steady-state latency: ~72ms.
- **CachingAgenticProxy:** Wraps `AgenticRetriever` (Ollama `qwen2.5:7b`) with an LRU cache (128 entries, MD5-keyed on normalised query). Cache hits return in <1ms. The `AgenticRetriever` presents the LLM with a document catalogue (id, title, summary) and asks it to rank relevant IDs — a lightweight agentic approach that avoids file-system tool calls while still leveraging LLM reasoning.

Each plugin is invoked inside an exception boundary (Tactic 3 — Fault Isolation). If a plugin crashes or times out, the Orchestrator logs the failure, marks the plugin degraded, and returns partial results from healthy plugins — the user always receives a response.

#### 5.2.3 Context Aggregation and Enrichment

The `ContextAggregator` merges results from all active strategies using **Reciprocal Rank Fusion (RRF)** with constant k=60. RRF avoids score normalisation — each document's aggregated score is the sum of `1/(k + rank)` across strategies, naturally boosting documents that appear highly in multiple strategy results.

After merging, the Orchestrator applies a **relevance filter**: only chunks scoring ≥70% of the top RRF score are sent to the LLM. For each relevant chunk, the full document content (up to 2,000 chars) is fetched from SQLite to provide richer context than the stored snippet alone.

#### 5.2.4 Conversational RAG with Query Rewriting (FR-07)

The Orchestrator implements a two-phase LLM pipeline when conversation history is present:

```
User query + history
       │
       ▼
 rewrite_query()  ─── LLM rewrites follow-up into standalone search query
       │
       ▼
  orch.query()   ─── Retrieval using rewritten query (BM25 + vector)
       │
       ▼
generate_answer_stream()  ─── Generation using original query + history + retrieved context
```

The rewrite step is skipped entirely for first messages (no history), adding zero overhead. For follow-ups, the rewritten query is surfaced to the user via the UI's **RewriteChip** component with hover/tap disclosure — full transparency without cluttering the response.

The streaming endpoint (`POST /api/query/stream`) emits four SSE event types in order:

| Event | Fields | When emitted |
|-------|--------|-------------|
| `rewrite` | `rewritten_query`, `rewrite_time_ms` | After query rewrite (if history present) |
| `sources` | `sources[]`, `strategies_used`, `retrieval_time_ms` | As soon as retrieval completes |
| `token` | `token` | Once per LLM output token |
| `done` | `generation_time_ms` | After last token |

This phased streaming lets the frontend render cited sources immediately while the answer is still generating, giving users actionable information with minimal perceived latency.

#### 5.2.5 LLM Citation Protocol

The generation prompt instructs the LLM to cite sources using `[[doc:ID|Title]]` syntax. The frontend parses this with a regex transform before passing the answer to the Markdown renderer, converting references to clickable links that open the original document inline in a browser tab via the `/api/documents/{id}/download` endpoint.

#### 5.2.6 Frontend

The Next.js frontend provides three pages:
- **Query Dashboard:** Streaming chatbot interface with per-message strategy toggles, expandable source cards (fully clickable, open document preview), RewriteChip hover card showing the rewritten query, and three-phase loading states ("Understanding context…" → "Searching documents…" → "Generating answer…")
- **Document Management:** Upload, document listing with search, delete; each document card opens the original file inline in a new tab
- **Settings & Analytics:** Strategy enable/disable toggles, model configuration, real-time usage statistics (total queries, feedback counts, average response time)

### 5.3 Architecture Analysis

We compared the implemented **Microkernel + Strategy** architecture against a hypothetical **Monolithic Controller** alternative.

#### 5.3.1 NFR-01: Latency (Measured)

| Configuration | Mean | P50 | P95 | Throughput | NFR-01 |
|--------------|------|-----|-----|------------|--------|
| Syntactic only | 2.1ms | 1.9ms | 2.6ms | 487 q/s | PASS |
| Semantic only | 330ms | 72ms | 348ms | 3.0 q/s | PASS |
| Syntactic + Semantic | 72ms | 72ms | 77ms | 13.8 q/s | PASS |

All configurations pass NFR-01 (P95 ≤ 15s) by a wide margin. The monolithic architecture would achieve similar raw latency, but loses the fault isolation benefit: a crash in one retrieval path would fail the entire query.

#### 5.3.2 NFR-05: Modifiability (Quantified)

| Metric | Microkernel + Strategy | Monolithic |
|--------|----------------------|------------|
| Files to modify for new strategy | 1 new + 1 modified | 2-3 modified |
| Lines of code changed | ~63 | ~80-100 |
| OCP compliance | Yes | No |
| Estimated effort | 4-8 person-hours | 16-24 person-hours |
| Isolated unit testing | Yes | No |

#### 5.3.3 Trade-offs

| Attribute | Microkernel | Monolithic |
|-----------|------------|------------|
| Raw latency | Equivalent | Equivalent |
| Fault tolerance | Partial results on crash | Total failure |
| Modifiability | 4-8 hrs (OCP) | 16-24 hrs |
| Testability | Isolated per-strategy | Integration only |
| Initial complexity | Higher | Lower |
| Dispatch overhead | ~2ms | None |

**Conclusion:** The Microkernel + Strategy architecture is the correct choice because extensibility (ASR-01) is the primary quality driver, and fault isolation (ASR-04) prevents the unreliable agentic retriever from degrading the overall system. The SSE streaming endpoint further reduces *perceived* latency: users see retrieved sources within the retrieval window (~72ms) rather than waiting for generation to complete (up to several seconds), making the architecture's separation of retrieval and generation phases directly user-visible.

### 5.4 Design Patterns Summary

| Pattern | File | Purpose |
|---------|------|---------|
| Strategy | `retrieval/strategy.py` | `RetrievalStrategy` ABC; polymorphic retrieval algorithms |
| Microkernel | `retrieval/orchestrator.py` | Plugin registry, fault-isolated dispatch, RRF aggregation |
| Factory | `retrieval/factory.py` | `StrategyFactory.create()` decouples instantiation from Orchestrator |
| Chain of Responsibility | `retrieval/semantic.py` | `TitleMatch → SummarySim → ContentSim` cascade for large corpora |
| Adapter | `ingestion/extractors.py` | `ExtractorRegistry` maps file extensions to `TextExtractor` implementations |
| Proxy (Caching) | `retrieval/agentic.py` | `CachingAgenticProxy` wraps `AgenticRetriever` with MD5-keyed LRU cache |
| Pipe-and-Filter | `ingestion/pipeline.py` | Five stateless filters operating on `DocumentEnvelope` |
| Facade | `api/routes.py` | Single REST entry point hiding retrieval and ingestion internals |
| Singleton | `ingestion/pipeline.py` | `get_embedding_model()` loads `SentenceTransformer` once, cached in module dict |

---

## 6. Reflections and Lessons Learned

### 6.1 Architectural Decisions

The Microkernel architecture proved its value repeatedly during development. When Ollama is unavailable, the system gracefully degrades to syntactic + semantic retrieval without any special error handling — the fault isolation boundary at the Orchestrator level handles it automatically. Adding conversational query rewriting also fit naturally into the Orchestrator without touching any plugin code, confirming that the Facade + Microkernel boundary was drawn at the right level.

The decision to implement the Semantic Retriever with adaptive behaviour — direct ChromaDB query for small corpora, Chain of Responsibility for large ones — was driven by the observation that the cascading filter's heuristics (title overlap, summary similarity) lack statistical power over tiny corpora. The switch point (100 documents) keeps the small-corpus experience accurate without sacrificing the architectural intent of the CoR pattern at scale.

### 6.2 Technology Choices

- **ChromaDB** was an excellent choice for the vector store: embedded, zero-config, persistent, and supports `$in` metadata filtering needed for the Chain of Responsibility's ContentSim stage
- **sentence-transformers** with `all-MiniLM-L6-v2` provides strong semantic quality at minimal computational cost with no GPU requirement
- **uv** significantly improved Python dependency management speed compared to pip
- **pdfplumber** handles PDF text extraction cleanly, with graceful table fallback
- **SSE (Server-Sent Events)** over WebSockets was the right choice for streaming: unidirectional, HTTP/1.1 compatible, no upgrade handshake, and directly supported by FastAPI's `StreamingResponse`

### 6.3 Challenges

- The Chain of Responsibility filter thresholds required careful tuning. An aggressive `TitleMatchHandler` threshold discards relevant documents when the user's phrasing differs from the document title. The current implementation falls through to returning the top candidates by corpus size when no title overlap exists.
- The BM25 index rebuilds from SQLite on every query. This is acceptable for the current corpus size (~5–50 documents) but would need to be replaced with an event-driven incremental update in production.
- Conversational query rewriting adds one full LLM round-trip before retrieval. For long conversations the rewrite prompt grows; capping history to the last 6 messages keeps this bounded.
- Agentic retrieval quality depends on the SLM's instruction-following ability. Smaller models occasionally return non-numeric output instead of document IDs, requiring robust regex parsing as a fallback.

### 6.4 Future Improvements

- **OCR support** for image-based PDF pages (current extraction silently produces empty text for scanned PDFs)
- **Event-driven BM25 index updates** — rebuild incrementally on document upload/delete rather than on every query
- **Role-based access control** — separate admin (upload/delete) from read-only user access
- **Graph RAG** as a fourth retrieval strategy, demonstrating extensibility by adding one new file + one factory line with no Orchestrator changes
- **Persistent conversation storage** — currently conversation history lives only in the browser; persisting it server-side would enable cross-session continuity

---

## 7. Individual Contributions

<!-- TODO: Fill in actual team member names and contributions before submission -->

| Team Member | Contributions |
|-------------|--------------|
| Member 1 | Task 1 (Requirements), Syntactic Retriever, API design |
| Member 2 | Task 2 (Stakeholders, ADRs), Semantic Retriever, Chain of Responsibility |
| Member 3 | Task 3 (Tactics, Patterns), Agentic Retriever, Caching Proxy |
| Member 4 | Task 4 (Prototype), Frontend, Ingestion Pipeline, Architecture Analysis |

---

## 8. References

1. IEEE 42010:2011 — Systems and software engineering — Architecture description
2. M. Nygard, "Architecture Decision Records," 2011
3. L. Bass, P. Clements, R. Kazman, *Software Architecture in Practice*, 4th ed., 2021
4. E. Gamma et al., *Design Patterns: Elements of Reusable Object-Oriented Software*, 1994
5. S. Robertson, N. Walker, "Okapi at TREC-3," NIST Special Publication, 1995 (BM25)
6. N. Reimers, I. Gurevych, "Sentence-BERT," EMNLP 2019
7. ChromaDB Documentation — https://docs.trychroma.com/
8. FastAPI Documentation — https://fastapi.tiangolo.com/

---

**GitHub Repository:** [https://github.com/Arihant25/aamsir](https://github.com/Arihant25/aamsir)

**Submission Format:** Project3_5.pdf
