# ADR 002: Pipe-and-Filter Architecture for Document Ingestion

## Context and Problem Statement
Ingesting documents involves a sequence of transformations: reading files, normalization, text extraction, summarization, embedding generation, and finally indexing. The order of these steps is fixed, but the implementation of each step (filter) might change (e.g., swapping OCR engines or embedding models). We need a flexible architecture that allows individual processing steps to be swapped or scaled independently.

## Addresses Concerns
*   **Modifiability** — Developer Concern: Steps can be swapped (e.g., new OCR) without rewriting the pipeline.
*   **Data Integrity** — Data Owner Concern: Errors at one stage can be isolated and debugged.
*   **Testability** — Developer Concern: Each filter can be unit tested on its own.

## Decision Drivers
*   **Modifiability:** Frequent changes expected in specific processing steps (different PDF parsers, new summarization prompts).
*   **Reusability:** Some steps (e.g., Text Extraction) might be reused in other pipelines.
*   **Testability:** Need to verify each transformation step in isolation.

## Considered Options
*   **Batch Script:** A single procedural script executing steps sequentially.
*   **Pipe-and-Filter Pattern:** Independent components connected by data streams.
*   **Event-Driven Architecture:** Steps triggered by message queue events.

## Decision Outcome
Chosen option: **Pipe-and-Filter Architecture**.

The ingestion process will be modeled as a pipeline of independent filters. Each filter (e.g., `TextExtractor`, `Summarizer`, `Embedder`) reads from an input buffer, processes the data, and writes to an output buffer.

### Positive Consequences
*   **Loose Coupling:** Filters only know about the data format, not about other filters.
*   **Parallelism:** Different filters can run in parallel on different chunks of data (e.g., embedding generator can run on a GPU while text extraction runs on CPU).
*   **Maintainability:** Easier to debug specific stages of the pipeline.

### Negative Consequences
*   **Data Overhead:** Passing data between filters (serialization/deserialization) adds overhead.
*   **Error Handling:** Managing errors in the middle of a pipeline requires a robust strategy (dead-letter queues or compensatory actions).

## Pros and Cons of the Options
### Batch Script
*   *Good:* Easiest to write.
*   *Bad:* Hard to test parts in isolation; failure stops the whole batch; hard to parallelize.

### Event-Driven
*   *Good:* Highly scalable; robust retry mechanisms.
*   *Bad:* High infrastructure complexity (Kafka/RabbitMQ) which is excessive for this project's scale.

### Pipe-and-Filter
*   *Good:* Clean abstraction; supports streaming data; logical separation of duties.
*   *Bad:* Requires defining a common data envelope format.
