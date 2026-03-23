# ADR 003: Strategy Pattern for Retrieval Component Implementation

## Context and Problem Statement
Within the Retrieval Engine, we need to implement different algorithms for fetching documents (BM25 for syntactic, Cosine Similarity for semantic, Tool-use for agentic). The orchestrator needs to invoke these algorithms interchangeably. Using `if-else` or `switch` statements to select the algorithm breaks the Open/Closed Principle and makes the orchestrator class rigid and hard to test.

## Addresses Concerns
*   **Maintainability** — Developer Concern: Avoids complex conditional logic (clean code).
*   **Testability** — Developer Concern: Strategies are testable in isolation.
*   **Correctness of Design Patterns** — Instructor Concern: Proper application of GoF patterns.

## Decision Drivers
*   **Interchangeability:** The ability to swap algorithms at runtime (e.g., based on user preference or A/B testing).
*   **Isolation of Algorithms:** Each retrieval logic is complex and should be encapsulated.
*   **Extensibility:** Adding a new algorithm (e.g., a hybrid approach) should be easy.

## Considered Options
*   **Conditional Logic:** `if type == 'semantic' then do_semantic_search()`.
*   **Strategy Pattern:** Define a common interface and implement concrete strategy classes.
*   **Template Method:** Define a skeleton algorithm in a base class and override steps.

## Decision Outcome
Chosen option: **Strategy Pattern**.

We will define a `RetrievalStrategy` interface with a method like `retrieve(query: str) -> List[Document]`. Concrete classes `SyntacticRetriever`, `SemanticRetriever`, and `AgenticRetriever` will implement this interface. The Orchestrator will hold a collection of these strategies.

### Positive Consequences
*   **Clean Code:** Eliminates complex conditional statements in the Orchestrator.
*   **Separation of Concerns:** Algorithmic logic is separated from the execution context.
*   **Testability:** Strategies can comprise their own unit tests; the Orchestrator can be tested with mock strategies.

### Negative Consequences
*   **Class Explosion:** Increases the number of classes in the application.
*   **Communication Overhead:** All strategies must return data in identical formats, which might require adapters for disparate data sources.

## Pros and Cons of the Options
### Conditional Logic
*   *Good:* Minimal boilerplate.
*   *Bad:* Hard to maintain; modification requires changing the client code; prone to bugs.

### Template Method
*   *Good:* Useful if algorithms share a lot of structure.
*   *Bad:* Retrievers here are vastly different (SQL vs Vector vs Tool use), so they don't share much structure to generalize.

### Strategy Pattern
*   *Good:* Decouples algorithm definition from usage; perfect for interchangeable algorithms.
*   *Bad:* Clients must be aware of the strategies (or they must be injected).
