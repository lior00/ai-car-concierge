"""
Shared embedding function factory.
Single source of truth — used by both ingest.py and retriever.py.
If the model or provider changes here, both automatically stay in sync.
"""
from chromadb import EmbeddingFunction, Documents, Embeddings
from chromadb.utils import embedding_functions
from backend.config import EMBEDDING_PROVIDER, OPENAI_API_KEY, COHERE_API_KEY


class _CohereEmbeddingFunction(EmbeddingFunction[Documents]):
    """Custom Cohere embedding function — handles v3 models that require input_type."""
    def __init__(self, api_key: str):
        import cohere
        self._co = cohere.ClientV2(api_key)

    def __call__(self, input: Documents) -> Embeddings:
        resp = self._co.embed(
            texts=list(input),
            model="embed-english-light-v3.0",
            input_type="search_document",
            embedding_types=["float"],
        )
        return resp.embeddings.float_


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
        return _CohereEmbeddingFunction(api_key=COHERE_API_KEY)
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
