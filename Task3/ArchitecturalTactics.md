# Architectural Tactics: AAMSIR

## 1. Introduction
Architectural tactics are design decisions that directly influence the achievement of a quality attribute (non-functional requirement). Unlike patterns, which describe complete structural solutions, a tactic is a single focused mechanism applied to meet a measurable quality goal. This document outlines the five primary tactics employed in AAMSIR, each linked to a specific NFR.

---

## Tactic 1: Caching (Proxy)
**Category:** Performance
**Addresses:** NFR-01 (Latency ≤ 15s P95)

### Description
Caching stores the results of expensive computations so that identical future requests can be served from a fast local store rather than recomputing from scratch. A **Caching Proxy** wraps a component behind an interface-compatible facade that intercepts requests, checks a cache, and only delegates to the real component on a cache miss.

### Application in AAMSIR
The `AgenticRetriever` is the most expensive component in the system: an SLM must reason over the file system using tool calls (`ls`, `grep`, `cat`), which involves multiple LLM inference rounds and I/O operations. A `CachingAgenticProxy` wraps the `AgenticRetriever`. When a query arrives, the proxy hashes the normalized query string and checks an in-memory LRU cache. On a hit, the cached `List[Document]` is returned immediately (< 1ms). On a miss, the proxy delegates to the real retriever, stores the result, and returns it.

```
Query --> CachingAgenticProxy --> [cache hit?] --> return cached result
                                      |
                                   [miss]
                                      v
                               AgenticRetriever (SLM + tools)
                                      |
                               store in cache --> return result
```

### Impact
Repeated or near-identical queries (e.g., a user refining their question) hit the cache and reduce P95 latency from potentially 20–30s (raw agentic) to sub-second for those requests, directly supporting NFR-01.

---

## Tactic 2: Cascading / Progressive Narrowing
**Category:** Performance
**Addresses:** NFR-01 (Latency ≤ 15s P95)

### Description
Progressive narrowing means ordering a multi-step filtering process from cheapest to most expensive. Each stage reduces the candidate set before the next, more expensive, stage runs. This limits the number of documents that must undergo costly computation.

### Application in AAMSIR
The `SemanticRetriever` implements a **Chain of Responsibility** pipeline with three handler stages:

| Stage | Operation | Cost | Typical Output |
| :--- | :--- | :--- | :--- |
| `TitleMatchHandler` | Lexical overlap between query tokens and document titles | Very Low (O(n) string ops) | Narrows I → J |
| `SummarySimHandler` | Cosine similarity between query embedding and pre-computed *summary* embeddings | Low (short vectors) | Narrows J → K' |
| `ContentSimHandler` | Cosine similarity against full *content* embeddings | High (large vectors) | Narrows K' → K |

Rather than running full vector search over all 10,000 documents in the content embedding space, the cascade ensures only the most promising candidates (filtered by title and summary) reach the expensive content similarity stage.

### Impact
Reduces the number of full-content vector comparisons from ~10,000 to typically ~50–200, cutting semantic retrieval time significantly and keeping total query latency within the 15s budget (NFR-01).

---

## Tactic 3: Fault Isolation via Plugin Sandboxing
**Category:** Availability
**Addresses:** NFR-04 (Uptime ≥ 99% during working hours)

### Description
Fault isolation prevents a failure in one component from propagating and taking down the entire system. In a plugin architecture, this means wrapping each plugin's execution in an exception boundary so that a crash or timeout in one plugin does not affect the others.

### Application in AAMSIR
The `Orchestrator` (Microkernel host) invokes each `RetrieverPlugin` inside a guarded execution block. If a plugin raises an unhandled exception or exceeds a configurable timeout (e.g., 10s), the kernel:
1. Logs the failure with a stack trace for observability.
2. Marks the plugin as degraded for this request.
3. Continues collecting results from the remaining healthy plugins.
4. Returns a partial result to the user, potentially with a notice that one retriever was unavailable.

The `AgenticRetriever`, being the most failure-prone (SLM hallucinations, file system timeouts), is the primary beneficiary of this tactic.

### Impact
A crash or hang in the `AgenticRetriever` does not kill the query. The user still receives results from the `SyntacticRetriever` and `SemanticRetriever`, maintaining service continuity and supporting NFR-04 (availability).

---

## Tactic 4: Horizontal Scaling of Stateless Filters
**Category:** Scalability
**Addresses:** NFR-03 (Index and search ≤ 10,000 documents without performance degradation)

### Description
Stateless components — those that carry no per-request in-memory state between invocations — can be freely replicated across multiple processes or machines. Load can then be distributed across replicas. This is the primary tactic for horizontal scalability.

### Application in AAMSIR
The ingestion pipeline is designed as a **Pipe-and-Filter** architecture where each filter (`TextExtractor`, `Summarizer`, `Embedder`, `Indexer`) is stateless. A document flows through as a self-contained data envelope (a `DocumentRecord` object with metadata). Because no filter holds state between documents, multiple instances of any filter can run in parallel on different documents simultaneously.

For bulk ingestion of large corpora (approaching the 10,000-document limit), the `Embedder` filter — the most compute-intensive step — can be scaled out to N worker processes (or GPU workers), each consuming documents from a shared queue:

```
Documents --> TextExtractor --> Summarizer --> [Queue] --> Embedder Worker 1 --> Indexer
                                                       --> Embedder Worker 2 --> Indexer
                                                       --> Embedder Worker N --> Indexer
```

### Impact
Ingestion throughput scales linearly with the number of `Embedder` workers, allowing the system to process the full 10,000-document corpus without bottlenecking on a single embedding pass (NFR-03).

---

## Tactic 5: Task Queuing with Resource Pooling
**Category:** Throughput / Performance
**Addresses:** NFR-02 (50 concurrent users without degradation)

### Description
When multiple users submit requests simultaneously, a shared resource (a GPU-bound SLM) becomes a bottleneck. Resource pooling maintains a fixed set of pre-initialized worker instances, and a task queue buffers incoming requests and dispatches them to available workers. This prevents both resource starvation (too few workers) and resource exhaustion (unbounded allocation).

### Application in AAMSIR
The `Scheduler` component acts as the **Broker** between the web-facing `Orchestrator` (which receives user queries) and the underlying model inference workers (which run the `FinalAnswerModel` SLM). Requests are placed into a bounded FIFO queue with optional priority lanes (e.g., cached results get higher priority). The Scheduler maintains a pool of inference workers and dispatches tasks to idle workers.

```
User 1 --|
User 2 --|--> Request Queue --> Scheduler --> [Worker Pool]
  ...    |                                     Worker A (busy)
User 50--|                                     Worker B (idle) <-- dispatched
                                               Worker C (idle) <-- dispatched
```

The web server returns a "processing" status immediately (non-blocking) and pushes the final result via a WebSocket or polling endpoint when ready.

### Impact
Smooths out traffic spikes by absorbing excess requests into the queue rather than crashing. Ensures the 50 concurrent users defined in NFR-02 receive responses without degradation, at the cost of a small additional queuing latency.
