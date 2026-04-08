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
| LLM (Optional) | Ollama (llama3.2:1b) |
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| PDF Extraction | pdfplumber |

---

## 2. Task 1: Requirements and Subsystems

### 2.1 Functional Requirements

| ID | Requirement | Architectural Significance |
|----|------------|---------------------------|
| FR-01 | Query Interface Dashboard | Drives the Facade pattern (single API entry point) |
| FR-02 | Result Exploration with source snippets | Requires chunked storage and metadata tracking |
| FR-03 | User Feedback Module (helpful/not helpful) | Requires persistence layer and analytics |
| FR-04 | Multi-Modal Retrieval (Syntactic, Semantic, Agentic) | Drives Strategy Pattern and Microkernel |
| FR-05 | Retrieval Configuration Panel | Drives runtime strategy switching |
| FR-06 | Document Management Module | Drives Pipe-and-Filter ingestion pipeline |

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

The `Orchestrator` manages three retrieval plugins:

- **SyntacticRetriever:** Rebuilds a BM25 index over paragraph-level chunks and scores query tokens. Average latency: ~2ms.
- **SemanticRetriever:** Implements Chain of Responsibility with three handlers (TitleMatch → SummarySim → ContentSim) using ChromaDB and sentence-transformers. Average latency: ~72ms.
- **CachingAgenticProxy:** Wraps `AgenticRetriever` (Ollama-based LLM reasoning) with an LRU cache. Cache hits return in <1ms.

Each plugin is invoked inside an exception boundary (Tactic 3). If a plugin crashes or times out, the Orchestrator returns partial results from healthy plugins.

#### 5.2.3 Context Aggregation

The `ContextAggregator` merges results from all strategies using **Reciprocal Rank Fusion (RRF)** with constant k=60. This produces a unified ranking that balances the strengths of different strategies without requiring score normalization.

#### 5.2.4 Frontend

The Next.js frontend provides three pages:
- **Query Dashboard:** Chatbot-style interface with strategy toggles, source citation expansion, and feedback buttons
- **Document Management:** Drag-and-drop upload, document listing with search, delete functionality
- **Settings & Analytics:** Strategy enable/disable cards, model configuration, real-time usage statistics

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

**Conclusion:** The Microkernel + Strategy architecture is the correct choice because extensibility (ASR-01) is the primary quality driver, and fault isolation (ASR-04) prevents the unreliable agentic retriever from degrading the overall system.

### 5.4 Design Patterns Summary

| Pattern | File | Purpose |
|---------|------|---------|
| Strategy | `retrieval/strategy.py` | Polymorphic retrieval algorithms |
| Microkernel | `retrieval/orchestrator.py` | Plugin-based engine with fault isolation |
| Factory | `retrieval/factory.py` | Decoupled strategy instantiation |
| Chain of Responsibility | `retrieval/semantic.py` | Cascading semantic filters |
| Adapter | `ingestion/extractors.py` | Uniform document format extraction |
| Proxy (Caching) | `retrieval/agentic.py` | LRU cache for agentic retrieval |
| Pipe-and-Filter | `ingestion/pipeline.py` | Linear ingestion pipeline |
| Facade | `api/routes.py` | Single API entry point |
| Singleton | `ingestion/pipeline.py` | Embedding model reuse |

---

## 6. Reflections and Lessons Learned

### 6.1 Architectural Decisions

The decision to use a Microkernel architecture proved valuable. When Ollama is unavailable, the system gracefully degrades to syntactic + semantic retrieval without any special error handling — the fault isolation boundary handles it automatically.

### 6.2 Technology Choices

- **ChromaDB** was an excellent choice for the vector store: embedded, zero-config, and supports metadata filtering
- **sentence-transformers** with `all-MiniLM-L6-v2` provides good semantic quality at minimal computational cost
- **uv** significantly improved Python dependency management speed compared to pip
- **pdfplumber** handles PDF text extraction well, with graceful table fallback

### 6.3 Challenges

- Balancing the Chain of Responsibility thresholds required tuning to avoid discarding relevant documents at early stages
- The BM25 index rebuild on every query is acceptable for the current document count but would need an event-driven approach for production scale
- Agentic retrieval quality depends heavily on the SLM's reasoning capability — smaller models sometimes produce unreliable document rankings

### 6.4 Future Improvements

- **OCR support** for image-based PDF pages
- **Event-driven BM25 index updates** instead of rebuild-on-query
- **WebSocket streaming** for real-time answer generation
- **Role-based access control** for admin vs. user distinction
- **Graph RAG** as a fourth retrieval strategy to demonstrate extensibility

---

## 7. Individual Contributions

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

**GitHub Repository:** [Link to be added]

**Submission Format:** Project3_5.pdf
