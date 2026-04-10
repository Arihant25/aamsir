# ADR 004: Broker Pattern for Scheduler

## Status

Accepted

## Context and Problem Statement
The system relies on various models (SLMs for agentic retrieval and generation, Embedding models). Requests come from multiple users concurrently. Directly coupling the user request handler to specific model instances creates a bottleneck and makes it hard to manage "resources" (e.g., if we have limited GPU slots). We need a way to decouple the request submission from the request execution to improved throughput and reliability.
## Addresses Concerns
*   **Performance (Latency/Throughput)** — End User Concern: Prevents overload during traffic spikes.
*   **Availability** — SysAdmin Concern: Failure in one worker doesn't kill the request handler.
*   **Resource Efficiency** — SysAdmin Concern: Optimized utilization of limited GPU resources.
## Decision Drivers
*   **Decoupling:** Senders (users) should not know which model instance processes their request.
*   **Load Balancing:** Distribute requests across available resources.
*   **Scalability:** Add more model workers without changing the client.

## Considered Options
*   **Direct Sync Calls:** The web handler calls the model inference function directly.
*   **Broker Pattern (Task Queue):** A broker receives requests and distributes them to workers.
*   **Observer Pattern:** Models watch for new requests.

## Decision Outcome
Chosen option: **Broker Pattern**.

We will use a Scheduler component acting as a Broker. User requests are placed into a queue. The Scheduler manages a pool of model workers and dispatches tasks to them as they become available.

### Positive Consequences
*   **Asynchronous Processing:** The web server doesn't block waiting for the model (can return a "processing" status or use websockets).
*   **Load Management:** The broker can implement rate limiting and prioritization.
*   **Resilience:** If a worker crashes, the broker can retry the task on another worker.

### Negative Consequences
*   **Complexity:** Requires managing a queue state and worker lifecycle.
*   **Latency:** Adds a small amount of overhead for queuing/dequeuing.

## Pros and Cons of the Options
### Direct Sync Calls
*   *Good:* Simplest to implement.
*   *Bad:* Blocks the web server; failure in model crashes the request; no load buffering (spike in traffic kills the server).

### Observer Pattern
*   *Good:* Decoupled.
*   *Bad:* Hard to implement load balancing (broadcasts might not be picked up efficiently).

### Broker Pattern
*   *Good:* Standard solution for distributing work; handles spikes gracefully via queue buffering.
*   *Bad:* Setup overhead.
