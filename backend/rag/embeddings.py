"""
Shared embedding function factory.
Single source of truth — used by both ingest.py and retriever.py.
If the model or provider changes here, both automatically stay in sync.
"""
from chromadb.utils import embedding_functions
from backend.config import EMBEDDING_PROVIDER, OPENAI_API_KEY, COHERE_API_KEY


def get_embedding_function():
    if EMBEDDING_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY required when EMBEDDING_PROVIDER=openai")
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name="text-embedding-3-small",
        )
    if EMBEDDING_PROVIDER == "cohere":
        if not COHERE_API_KEY:
            raise ValueError("COHERE_API_KEY required when EMBEDDING_PROVIDER=cohere")
        return embedding_functions.CohereEmbeddingFunction(
            api_key=COHERE_API_KEY,
            model_name="embed-english-light-v3.0",
        )
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
