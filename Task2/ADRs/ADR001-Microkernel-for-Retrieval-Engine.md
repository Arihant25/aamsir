# ADR 001: Microkernel Architecture for Retrieval Engine

## Context and Problem Statement
The retrieval engine needs to support multiple, distinct retrieval strategies (Syntactic, Semantic, Agentic) today, with likely additions in the future (e.g., Graph RAG). These strategies evolve independently and have different dependencies (syntactic uses simple indexes, semantic uses large vector DBs, agentic uses SLMs + tools). A monolithic design would tightly couple the orchestrator to specific implementations, making it hard to add or remove strategies without code modification.

## Addresses Concerns
*   **Modifiability (Extensibility)** — Developer Concern: New strategies can be added easily.
*   **Availability & Stability** — SysAdmin Concern: Plugin failure shouldn't crash the host.
*   **Compliance to Standards** — Instructor Concern: Demonstrates advanced architectural patterns.

## Decision Drivers
*   **Extensibility:** Need to add new retrieval methods without modifying the core logic.
*   **Isolation:** Failure in one retriever (e.g., SLM timeout) should not crash the others.
*   **Modularity:** Different teams/developers might work on different retrieval modules.

## Considered Options
*   **Monolithic Controller:** Hardcoded logic in the orchestrator (`if type == 'semantic'...`).
*   **Microkernel (Plugin) Architecture:** A core system that manages a registry of plugins.
*   **Microservices:** Each retriever as a separate deployable service.

## Decision Outcome
Chosen option: **Microkernel Architecture**.

We will design the Query Orchestrator as a "Microkernel" that defines a standard `RetrieverPlugin` interface. The specific strategies (Syntactic, Semantic, Agentic) will be implemented as plugins that register themselves with the kernel at startup.

### Positive Consequences
*   **Open/Closed Principle:** New retrievers can be added as new plugins without touching the orchestrator code.
*   **Fault Tolerance:** The kernel can catch exceptions from a misbehaving plugin and still return results from others.
*   **Simplified Testing:** Each plugin can be tested in isolation.

### Negative Consequences
*   **Complexity:** Requires designing a robust plugin interface and registration mechanism.
*   **Performance Overhead:** Slight overhead in dynamic dispatch compared to direct calls.

## Pros and Cons of the Options
### Monolithic Controller
*   *Good:* Simple to implement initially.
*   *Bad:* Violates OCP; huge conditional blocks; hard to maintain.

### Microservices
*   *Good:* complete isolation; independent scaling.
*   *Bad:* Network latency overhead for every query; operational complexity of managing multiple services is overkill for this scope.

### Microkernel
*   *Good:* Balance of modularity and performance (in-process calls).
*   *Bad:* Requires upfront design of the plugin contract.
