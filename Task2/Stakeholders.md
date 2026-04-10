# Stakeholders & Concerns (IEEE 42010)

## 1. Introduction
This section identifies the system stakeholders and their concerns, adhering to the IEEE 42010 standard for architecture description. A **stakeholder** is an individual, team, or organization with an interest in the system. A **concern** is an interest in the system relevant to one or more of its stakeholders.

## 2. Stakeholders and Concerns

### 2.1 End Users (Researchers / Students)
*   **Role:** The primary consumers of the system who submit queries to retrieve information from the document corpus.
*   **Concerns:**
    *   **Precision & Relevance:** Users are concerned that the system provides accurate and contextually relevant answers (avoiding hallucinations).
    *   **Performance (Latency):** Users are concerned with the time taken to receive a response; it must be interactive (<15s).
    *   **Usability:** Users are concerned with the ease of formulating queries and navigating results.
    *   **Trustworthiness:** Users are concerned with the ability to verify the sources of the information provided (citations).

### 2.2 System Administrators
*   **Role:** Responsible for deploying, configuring, and maintaining the AAMSIR operational environment.
*   **Concerns:**
    *   **Deployability:** Admins are concerned with the ease of installation and configuration (e.g., containerization).
    *   **Availability & Stability:** Admins are concerned with system uptime and handling of crashes.
    *   **Resource Efficiency:** Admins are concerned with the computational cost (CPU/GPU, Memory) required to run the system.
    *   **Observability:** Admins are concerned with the ability to monitor system health and logs.

### 2.3 Course Instructors & Evaluators (Academic Staff)
*   **Role:** Evaluating the project for grading based on software engineering principles (e.g., Karthik Vaidhyanathan).
*   **Concerns:**
    *   **Compliance to Standards:** Evaluators are concerned with the adherence to architectural best practices and documentation standards (like IEEE 42010).
    *   **Modularity & Coupling:** Evaluators are concerned with the quality of the software design (low coupling, high cohesion).
    *   **Correctness of Design Patterns:** Evaluators are concerned with the appropriate application of patterns (Strategy, Factory, etc.).

### 2.4 Developers / Maintenance Team
*   **Role:** The engineering team (Author: Arihant) building and refining the codebase.
*   **Concerns:**
    *   **Modifiability (Extensibility):** Developers are concerned with the ease of adding new features (e.g., new retrieval strategies) without breaking existing code.
    *   **Testability:** Developers are concerned with the ability to verify components in isolation.
    *   **Maintainability:** Developers are concerned with code readability and managing technical debt.

### 2.5 Data Owners / Content Providers
*   **Role:** The entities providing the documents (PDFs, Markdown files) to be ingested.
*   **Concerns:**
    *   **Data Integrity:** Owners are concerned that their documents are preserved and represented accurately after ingestion.
    *   **Confidentiality:** Owners are concerned that sensitive documents are not exposed to unauthorized users (if applicable).

## 3. Viewpoints and Views (IEEE 42010)

IEEE 42010 requires that each concern be addressed by one or more **viewpoints** (conventions for constructing a view) and the corresponding **views** (instances of those conventions applied to the system). Four viewpoints are used in AAMSIR.

---

### Viewpoint 1: Functional / Logical Viewpoint

**Concerns Addressed:** Precision & Relevance (End Users), Usability (End Users), Correctness of Design Patterns (Instructors)

**Convention:** Describes what the system does and how its logical components collaborate, expressed through UML class and sequence diagrams.

**View — Retrieval Engine Logic:**
The system exposes a single `Orchestrator` facade to the API layer. The Orchestrator holds a registry of `RetrievalStrategy` plugins (Syntactic, Semantic, Agentic). On each query, it invokes all active strategies, aggregates their results via `ContextAggregator` (Reciprocal Rank Fusion), enriches the top chunks from the database, and passes the context to the `FinalAnswerModel`. This view is realised in the Strategy Pattern class diagram in [Task3/ImplementationPatterns.md](../Task3/ImplementationPatterns.md) and the architecture diagram in [Task1/SystemOverview.md](../Task1/SystemOverview.md).

---

### Viewpoint 2: Development / Module Viewpoint

**Concerns Addressed:** Modifiability (Developers), Testability (Developers), Modularity & Coupling (Instructors)

**Convention:** Describes how the system is decomposed into modules and packages, expressed as a package/layer diagram and interface contracts.

**View — Module Decomposition:**

```text
aamsir/
├── api/           # Facade — routes.py exposes HTTP endpoints
├── ingestion/     # Pipe-and-Filter — pipeline.py, extractors.py
├── retrieval/     # Microkernel — orchestrator.py (host), strategy.py (interface)
│   ├── syntactic.py   # BM25 plugin
│   ├── semantic.py    # ChromaDB vector plugin
│   └── agentic.py     # SLM tool-use plugin
├── database.py    # SQLAlchemy models (DocumentRecord, QueryLog, FeedbackRecord)
└── config.py      # Centralised configuration
```

Each retrieval plugin depends only on the `RetrievalStrategy` interface (`strategy.py`), not on each other or on the Orchestrator internals. This enforces the Dependency Inversion Principle and ensures plugins can be unit-tested in isolation with mock corpora.

---

### Viewpoint 3: Deployment / Operational Viewpoint

**Concerns Addressed:** Deployability (SysAdmins), Availability & Stability (SysAdmins), Resource Efficiency (SysAdmins), Observability (SysAdmins)

**Convention:** Describes how software artefacts are mapped to physical or virtual infrastructure nodes, expressed as a deployment diagram.

**View — Deployment Topology:**

```text
┌─────────────────────── Institution Network (on-premise) ────────────────────────┐
│                                                                                  │
│  ┌──────────────────┐      HTTP/SSE      ┌───────────────────────────────────┐  │
│  │  User Browser    │ ◄────────────────► │  Next.js Frontend  (Node process) │  │
│  └──────────────────┘                   └───────────────┬───────────────────┘  │
│                                                          │ REST + SSE           │
│                                          ┌───────────────▼───────────────────┐  │
│                                          │  FastAPI Backend  (Uvicorn)        │  │
│                                          │  ├─ Orchestrator                  │  │
│                                          │  ├─ Ingestion Pipeline            │  │
│                                          │  └─ /api/* routes                 │  │
│                                          └───┬───────────┬───────────────────┘  │
│                                              │           │                       │
│                           ┌──────────────────▼─┐   ┌────▼──────────────────┐   │
│                           │  SQLite (aamsir.db) │   │  ChromaDB (chroma/)   │   │
│                           └────────────────────┘   └───────────────────────┘   │
│                                              │                                   │
│                           ┌──────────────────▼───────────────┐                  │
│                           │  Ollama  (localhost:11434)        │                  │
│                           │  Model: gemma4:e2b (on-premise)   │                  │
│                           └──────────────────────────────────┘                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

All inference remains within the institution boundary. No user query or document content traverses an external network, directly satisfying NFR-06 (Data Security / on-premise constraint).

---

### Viewpoint 4: Information / Data Viewpoint

**Concerns Addressed:** Data Integrity (Data Owners), Confidentiality (Data Owners), Trustworthiness / Citations (End Users)

**Convention:** Describes how data is structured, stored, and flows through the system, expressed as an entity and data-flow description.

**View — Data Lifecycle:**

A document transitions through three representations:

| Stage | Store | Format |
| :--- | :--- | :--- |
| Raw upload | `data/uploads/` (filesystem) | Original file (PDF, TXT, MD, etc.) |
| Structured record | SQLite `documents` table | `DocumentRecord` (id, title, content, summary, chunk_count, …) |
| Vector index | ChromaDB `data/chroma/` | Embedding vectors keyed by `doc_id` + chunk offset |

At query time, retrieved chunk `doc_id` values are used to fetch the original `DocumentRecord` from SQLite, guaranteeing citations always trace back to a specific, auditable source document. No external service touches this data at any stage.

---

## 4. Stakeholder Power/Interest Matrix
(Supplementary Analysis for Project Management)

| Stakeholder | Power | Interest | Management Strategy |
| :--- | :--- | :--- | :--- |
| **End Users** | High | High | **Manage Closely:** Their satisfaction with *Precision* and *Performance* defines success. |
| **Course Instructors** | High | High | **Manage Closely:** Their evaluation of *Compliance* and *Design Quality* determines the grade. |
| **Developers** | Medium | High | **Keep Informed:** Vital for maintaining *Modifiability*. |
| **SysAdmins** | Medium | Medium | **Keep Satisfied:** Crucial for *Deployability* and *Availability*. |
| **Data Owners** | Low | Low | **Monitor:** Ensure *Integrity* of their data. |
