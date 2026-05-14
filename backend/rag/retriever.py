"""
Query ChromaDB and return top-k relevant chunks for a given query.
"""
import logging
from dataclasses import dataclass

import chromadb

from backend.config import CHROMA_PATH, CHROMA_COLLECTION, EMBEDDING_PROVIDER
from backend.rag.embeddings import get_embedding_function

logger = logging.getLogger(__name__)

TOP_K = 4
# Cohere distances for relevant matches are typically 0.3–0.6; sentence-transformers 0.4–0.7
# Set permissive threshold — too strict = empty results, too loose = noise (LLM handles noise fine)
MIN_RELEVANCE_SCORE = 0.95


@dataclass
class RetrievalResult:
    text: str
    source: str
    distance: float


def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(name=CHROMA_COLLECTION, embedding_function=get_embedding_function())


def retrieve(query: str, top_k: int = TOP_K) -> list[RetrievalResult]:
    """
    Retrieve top-k relevant chunks for the given query.
    Returns empty list if collection is empty or no relevant chunks found.
    """
    try:
        collection = _get_collection()
    except Exception as e:
        logger.warning(f"ChromaDB collection not found — run ingest first. Error: {e}")
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[RetrievalResult] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        if dist <= MIN_RELEVANCE_SCORE:
            chunks.append(RetrievalResult(text=doc, source=meta["source"], distance=dist))

    if not chunks:
        logger.debug(f"No relevant chunks found for query: '{query[:60]}...'")

    return chunks


def format_context(chunks: list[RetrievalResult]) -> str:
    """Format retrieved chunks into a single context string for the LLM."""
    if not chunks:
        return "No relevant documentation found."
    parts = []
    for chunk in chunks:
        parts.append(f"[Source: {chunk.source}.md]\n{chunk.text}")
    return "\n\n---\n\n".join(parts)
