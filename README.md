# AAMSIR — Adaptive Architecture for Multi-Strategy Information Retrieval

## Team 5 | S26CS6.401 — Software Engineering | Project 3

AAMSIR is an on-premise, privacy-safe document retrieval system that lets users ask natural-language questions over private document corpora and receive grounded answers with cited sources. It combines three interchangeable retrieval strategies — syntactic (BM25), semantic (vector similarity), and agentic (LLM-driven) — all running locally.

**GitHub Repository:** [https://github.com/Arihant25/aamsir](https://github.com/Arihant25/aamsir)

---

## Repository Structure

```text
aamsir/
├── Task1/                    # Requirements and Subsystems
│   ├── Requirements.md       # Functional & non-functional requirements, ASRs
│   ├── SystemOverview.md     # Subsystem descriptions and diagrams
│   ├── archView.png          # High-level architecture diagram
│   └── classDiagram.png      # UML class diagram
│
├── Task2/                    # Architecture Framework
│   ├── Stakeholders.md       # IEEE 42010 stakeholders, viewpoints, views
│   └── ADRs/                 # Architecture Decision Records (Nygard template)
│       ├── ADR001-Microkernel-for-Retrieval-Engine.md
│       ├── ADR002-Pipe-Filter-Ingestion.md
│       ├── ADR003-Strategy-Pattern.md
│       └── ADR004-Broker-Scheduler.md
│
├── Task3/                    # Architectural Tactics and Patterns
│   ├── ArchitecturalTactics.md   # 5 tactics mapped to NFRs
│   └── ImplementationPatterns.md # Strategy Pattern + Chain of Responsibility
│
├── Task4/                    # Prototype Implementation and Analysis
│   ├── README.md             # Setup instructions (see below)
│   ├── backend/              # FastAPI + Python retrieval engine
│   ├── frontend/             # Next.js web dashboard
│   └── analysis/             # Architecture analysis (Microkernel vs Monolithic)
│
├── technical_report.tex      # LaTeX source for submission PDF
└── technical_report.pdf      # Compiled report (Project3_5.pdf)
```

## Quick Start (Prototype)

See [`Task4/README.md`](Task4/README.md) for detailed setup instructions. In short:

**Terminal 1 — Backend:**

```bash
cd Task4/backend && uv sync && uv run python seed.py && uv run uvicorn src.aamsir.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**

```bash
cd Task4/frontend && npm install && npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).

### Prerequisites

| Tool    | Version | Purpose                 |
| ------- | ------- | ----------------------- |
| Python  | 3.11+   | Backend runtime         |
| uv      | latest  | Python dependencies     |
| Node.js | 18+     | Frontend runtime        |
| Ollama  | latest  | Optional — LLM features |

## Team Members

| Name                | Roll Number |
| ------------------- | ----------- |
| Arihant Tripathy    | 2023111026  |
| Aviral Gupta        | 2023111023  |
| Inesh Dheer         | 2023111010  |
| Mohit Kumar Singh   | 2023111021  |
| Sreemaee Akshathala | 2025701028  |
