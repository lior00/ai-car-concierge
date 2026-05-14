"""
RAG tool: retrieve relevant documentation chunks from ChromaDB
and synthesize an answer using the LLM.
"""
import logging

from backend.rag.retriever import retrieve, format_context

logger = logging.getLogger(__name__)


def search_knowledge_base(query: str) -> dict:
    """
    Search the knowledge base (policy, FAQ, support, maintenance, shipping docs).

    Returns:
        {
            "context": str,          # formatted retrieved chunks
            "sources": list[str],    # source document names
            "chunk_count": int,
        }
    """
    chunks = retrieve(query)

    if not chunks:
        return {
            "context": "No relevant documentation found for this query.",
            "sources": [],
            "chunk_count": 0,
        }

    context = format_context(chunks)
    sources = list({chunk.source for chunk in chunks})

    logger.debug(f"RAG retrieved {len(chunks)} chunks from sources: {sources}")

    return {
        "context": context,
        "sources": sources,
        "chunk_count": len(chunks),
    }
