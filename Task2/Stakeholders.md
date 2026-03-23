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

## 3. Stakeholder Power/Interest Matrix
(Supplementary Analysis for Project Management)

| Stakeholder | Power | Interest | Management Strategy |
| :--- | :--- | :--- | :--- |
| **End Users** | High | High | **Manage Closely:** Their satisfaction with *Precision* and *Performance* defines success. |
| **Course Instructors** | High | High | **Manage Closely:** Their evaluation of *Compliance* and *Design Quality* determines the grade. |
| **Developers** | Medium | High | **Keep Informed:** Vital for maintaining *Modifiability*. |
| **SysAdmins** | Medium | Medium | **Keep Satisfied:** Crucial for *Deployability* and *Availability*. |
| **Data Owners** | Low | Low | **Monitor:** Ensure *Integrity* of their data. |
