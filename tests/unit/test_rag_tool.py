"""Unit tests for rag_tool.py — knowledge base retrieval."""
from unittest.mock import patch, MagicMock
from backend.agent.tools import rag_tool
from backend.rag.retriever import RetrievalResult


class TestSearchKnowledgeBase:
    @patch("backend.agent.tools.rag_tool.retrieve")
    def test_returns_context_when_chunks_found(self, mock_retrieve):
        mock_retrieve.return_value = [
            RetrievalResult(
                text="Only vehicles from 2022 or newer are sold.",
                source="policy",
                distance=0.12,
            )
        ]
        result = rag_tool.search_knowledge_base("what is the sales policy?")
        assert result["chunk_count"] == 1
        assert "policy" in result["sources"]
        assert "2022" in result["context"]

    @patch("backend.agent.tools.rag_tool.retrieve")
    def test_no_results_returns_fallback(self, mock_retrieve):
        mock_retrieve.return_value = []
        result = rag_tool.search_knowledge_base("irrelevant query xyz")
        assert result["chunk_count"] == 0
        assert result["sources"] == []
        assert "No relevant" in result["context"]

    @patch("backend.agent.tools.rag_tool.retrieve")
    def test_deduplicates_sources(self, mock_retrieve):
        mock_retrieve.return_value = [
            RetrievalResult(text="chunk1", source="policy", distance=0.1),
            RetrievalResult(text="chunk2", source="policy", distance=0.15),
        ]
        result = rag_tool.search_knowledge_base("policy?")
        assert result["sources"].count("policy") == 1
