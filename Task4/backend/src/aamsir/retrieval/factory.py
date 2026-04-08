"""
Strategy Factory (Proposal: StrategyFactory.create(type)).

Decouples strategy instantiation from the Orchestrator.
"""

from __future__ import annotations

from ..config import OLLAMA_BASE_URL, OLLAMA_MODEL
from .agentic import AgenticRetriever, CachingAgenticProxy
from .semantic import SemanticRetriever
from .strategy import RetrievalStrategy
from .syntactic import SyntacticRetriever


class StrategyFactory:
    """Factory that creates retrieval strategy instances by name."""

    @staticmethod
    def create(strategy_type: str) -> RetrievalStrategy:
        match strategy_type:
            case "syntactic":
                return SyntacticRetriever()
            case "semantic":
                return SemanticRetriever()
            case "agentic":
                raw = AgenticRetriever(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)
                return CachingAgenticProxy(raw)
            case _:
                raise ValueError(f"Unknown strategy type: {strategy_type}")

    @staticmethod
    def available_types() -> list[str]:
        return ["syntactic", "semantic", "agentic"]
