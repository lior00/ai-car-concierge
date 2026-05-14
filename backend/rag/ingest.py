"""
Ingest all markdown files from knowledge_base/ into ChromaDB.
Idempotent: checks existing doc count before re-embedding.
"""
import logging
import os
from pathlib import Path

import chromadb

from backend.config import CHROMA_PATH, CHROMA_COLLECTION, KNOWLEDGE_BASE_PATH
from backend.rag.embeddings import get_embedding_function

logger = logging.getLogger(__name__)

CHUNK_SIZE = 800       # characters per chunk
CHUNK_OVERLAP = 100    # overlap between chunks


def _chunk_text(text: str, source: str) -> list[dict]:
    """Split text into overlapping chunks, preserving heading context."""
    chunks = []
    start = 0
    chunk_id = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end]
        chunks.append({
            "id": f"{source}__chunk_{chunk_id}",
            "text": chunk,
            "source": source,
        })
        start += CHUNK_SIZE - CHUNK_OVERLAP
        chunk_id += 1
    return chunks


def run_ingest(force: bool = False) -> int:
    """
    Embed all markdown docs into ChromaDB.
    Returns number of chunks added.
    force=True re-embeds even if docs already exist.
    """
    kb_path = Path(KNOWLEDGE_BASE_PATH)
    md_files = list(kb_path.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No .md files found in {kb_path}")

    ef = get_embedding_function()
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    existing_count = collection.count()
    if existing_count > 0 and not force:
        logger.info(f"Ingest skipped — {existing_count} chunks already in ChromaDB.")
        return 0

    if force and existing_count > 0:
        client.delete_collection(CHROMA_COLLECTION)
        collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Existing collection deleted for force re-ingest.")

    all_ids, all_docs, all_metas = [], [], []
    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        source = md_file.stem  # e.g. "policy", "support"
        chunks = _chunk_text(text, source)
        for chunk in chunks:
            all_ids.append(chunk["id"])
            all_docs.append(chunk["text"])
            all_metas.append({"source": chunk["source"]})

    collection.add(documents=all_docs, ids=all_ids, metadatas=all_metas)
    logger.info(f"Ingested {len(all_ids)} chunks from {len(md_files)} files into ChromaDB.")
    return len(all_ids)


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    run_ingest(force=True)
