"""
Agentic Retriever — Tool-use based retrieval with SLM (FR-04.3).

The SLM is given three filesystem-like tools (ls_docs, grep_doc, cat_doc)
and runs an agentic loop — multiple Ollama inference rounds — until it has
explored the corpus and identified the most relevant documents.

Tools operate on extracted text stored in SQLite (not raw disk files, which
may be binary PDFs/images) so the SLM always sees clean, searchable text.

Wrapped in a CachingAgenticProxy for performance (Tactic 1).
Falls back gracefully if Ollama is not available.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import OrderedDict

from sqlalchemy import select

from ..database import DocumentRecord, SessionLocal
from .strategy import RetrievalStrategy, RetrievedChunk

logger = logging.getLogger(__name__)

_MAX_ITER = 10  # Maximum agentic tool-call rounds before forcing a final answer

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ls_docs",
            "description": "List all available document filenames in the corpus.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_doc",
            "description": (
                "Search for a text pattern within a document's content. "
                "Returns up to 20 matching lines (case-insensitive)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Document filename as returned by ls_docs.",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Case-insensitive text pattern to search for.",
                    },
                },
                "required": ["filename", "pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cat_doc",
            "description": "Read the text content of a document (first 1000 characters).",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Document filename as returned by ls_docs.",
                    },
                },
                "required": ["filename"],
            },
        },
    },
]

_SYSTEM_PROMPT = (
    "You are a document retrieval agent. You have access to tools to explore a document corpus:\n"
    "- ls_docs: list all available document filenames\n"
    "- grep_doc: search for a text pattern within a specific document\n"
    "- cat_doc: read the first 1000 characters of a document\n\n"
    "Use these tools to explore documents and find those most relevant to the user's query. "
    "When you are confident in your findings, respond with exactly this format on its own line:\n"
    "RELEVANT_FILES: <comma-separated filenames in order of relevance, best first>"
)


class AgenticRetriever(RetrievalStrategy):
    """SLM-powered retrieval using Ollama tool-calling.

    The retriever runs an agentic loop where the SLM can call ls_docs,
    grep_doc, and cat_doc across multiple inference rounds to explore the
    corpus before naming the most relevant documents.
    """

    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url
        self._last_tool_calls: list[dict] = []

    def is_available(self) -> bool:
        """Check Ollama availability on every call (no caching).

        Ollama may be started/stopped at any time, so we probe on each
        request to support dynamic availability.
        """
        try:
            import ollama
            client = ollama.Client(host=self._base_url)
            client.list()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Tool implementations (virtual filesystem over SQLite content)
    # ------------------------------------------------------------------

    def _exec_ls(self, docs: list[DocumentRecord]) -> str:
        names = [d.original_name for d in docs]
        return "\n".join(names) if names else "No documents available."

    def _exec_grep(self, filename: str, pattern: str, docs: list[DocumentRecord]) -> str:
        doc = next((d for d in docs if d.original_name == filename), None)
        if not doc:
            return f"File not found: {filename}"
        lines = (doc.content or "").splitlines()
        hits = [line for line in lines if pattern.lower() in line.lower()]
        if not hits:
            return f"No matches for '{pattern}' in {filename}."
        return "\n".join(hits[:20])

    def _exec_cat(self, filename: str, docs: list[DocumentRecord]) -> str:
        doc = next((d for d in docs if d.original_name == filename), None)
        if not doc:
            return f"File not found: {filename}"
        body = (doc.content or "")[:1000]
        suffix = "..." if len(doc.content or "") > 1000 else ""
        return body + suffix

    def _dispatch_tool(self, name: str, args: dict, docs: list[DocumentRecord]) -> str:
        if name == "ls_docs":
            return self._exec_ls(docs)
        if name == "grep_doc":
            return self._exec_grep(args.get("filename", ""), args.get("pattern", ""), docs)
        if name == "cat_doc":
            return self._exec_cat(args.get("filename", ""), docs)
        return f"Unknown tool: {name}"

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if not self.is_available():
            return []

        import ollama
        client = ollama.Client(host=self._base_url)

        db = SessionLocal()
        try:
            docs = db.execute(
                select(DocumentRecord).where(DocumentRecord.is_indexed == True)
            ).scalars().all()

            if not docs:
                return []

            self._last_tool_calls = []

            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Find the top {top_k} documents most relevant to: {query}"},
            ]

            final_text = ""

            for iteration in range(_MAX_ITER):
                response = client.chat(
                    model=self._model,
                    messages=messages,
                    tools=_TOOLS,
                )
                assistant_msg = response["message"]
                messages.append(assistant_msg)

                tool_calls = assistant_msg.get("tool_calls") or []

                if not tool_calls:
                    # No tool calls — treat this as the final answer
                    final_text = assistant_msg.get("content", "")
                    break

                # Execute each requested tool and feed results back
                for call in tool_calls:
                    fn = call["function"]
                    tool_name = fn["name"]
                    tool_args = fn.get("arguments") or {}
                    result = self._dispatch_tool(tool_name, tool_args, docs)
                    logger.debug("Tool %s(%s) → %s", tool_name, tool_args, result[:80])
                    self._last_tool_calls.append({
                        "name": tool_name,
                        "args": tool_args,
                        "result": result,
                    })
                    messages.append({"role": "tool", "content": result})

                # Inform the model how many turns it has left
                remaining = _MAX_ITER - iteration - 1
                if remaining > 0:
                    messages.append({
                        "role": "user",
                        "content": (
                            f"[Turn {iteration + 1}/{_MAX_ITER} complete. "
                            f"{remaining} turn{'s' if remaining != 1 else ''} remaining. "
                            "Continue exploring or output RELEVANT_FILES if ready.]"
                        ),
                    })

            else:
                # Hit iteration cap — ask for a final answer with no tools available
                messages.append({
                    "role": "user",
                    "content": (
                        f"Based on your exploration, list the top {top_k} relevant filenames now. "
                        "Respond with: RELEVANT_FILES: <comma-separated filenames>"
                    ),
                })
                response = client.chat(model=self._model, messages=messages)
                final_text = response["message"].get("content", "")

            return self._parse_results(final_text, docs, top_k)

        except Exception as e:
            logger.error("Agentic retrieval failed: %s", e)
            return []
        finally:
            db.close()

    def _parse_results(
        self, final_text: str, docs: list[DocumentRecord], top_k: int
    ) -> list[RetrievedChunk]:
        """Extract filenames from the SLM's final response and map to RetrievedChunks."""
        filenames: list[str] = []

        match = re.search(r"RELEVANT_FILES:\s*(.+)", final_text, re.IGNORECASE)
        if match:
            filenames = [f.strip() for f in match.group(1).split(",") if f.strip()]

        # Fallback: check if any known filename appears anywhere in the response
        if not filenames:
            known = {d.original_name for d in docs}
            filenames = [name for name in known if name in final_text]

        filenames = filenames[:top_k]
        name_map = {d.original_name: d for d in docs}

        results = []
        for rank, filename in enumerate(filenames):
            doc = name_map.get(filename)
            if doc:
                results.append(RetrievedChunk(
                    doc_id=doc.id,
                    title=doc.title or doc.original_name,
                    filename=doc.original_name,
                    content=(doc.content or "")[:500],
                    score=1.0 - rank * 0.1,
                    strategy="agentic",
                ))
        return results

    def get_name(self) -> str:
        return "agentic"


class CachingAgenticProxy(RetrievalStrategy):
    """Caching Proxy wrapping the AgenticRetriever (Tactic 1).

    LRU cache keyed on normalized query string. Cache hits return
    in <1ms instead of the 5-30s agentic retrieval time.

    Tool calls are cached alongside results so the frontend can always
    display what the agent did, even for repeated queries.
    """

    def __init__(self, delegate: AgenticRetriever, max_cache_size: int = 128):
        self._delegate = delegate
        self._cache: OrderedDict[str, tuple[list[RetrievedChunk], list[dict]]] = OrderedDict()
        self._max_size = max_cache_size
        self._last_tool_calls: list[dict] = []

    def _cache_key(self, query: str) -> str:
        normalized = " ".join(query.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        key = self._cache_key(query)

        if key in self._cache:
            logger.info("Agentic cache HIT for query: %s...", query[:50])
            self._cache.move_to_end(key)
            results, tool_calls = self._cache[key]
            self._last_tool_calls = tool_calls
            return results

        results = self._delegate.retrieve(query, top_k)
        self._last_tool_calls = self._delegate._last_tool_calls

        self._cache[key] = (results, self._last_tool_calls)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

        return results

    def is_available(self) -> bool:
        return self._delegate.is_available()

    def get_name(self) -> str:
        return "agentic"
