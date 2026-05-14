import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# LLM
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-sonnet-4-6")

# Embeddings
EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

# Cohere (free embeddings API — no local model needed)
COHERE_API_KEY: str | None = os.getenv("COHERE_API_KEY")

# Email
EMAIL_FROM: str = os.getenv("EMAIL_FROM", "concierge@premiumdealership.com")

# Mailtrap SMTP (sandbox — no domain verification needed)
MAILTRAP_USERNAME: str | None = os.getenv("MAILTRAP_USERNAME")
MAILTRAP_PASSWORD: str | None = os.getenv("MAILTRAP_PASSWORD")

# Database
DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "data" / "inventory.db"))
INVENTORY_SQL_PATH: str = str(BASE_DIR / "data" / "inventory.sql")

# ChromaDB
CHROMA_PATH: str = os.getenv("CHROMA_PATH", str(BASE_DIR / "data" / "chroma_db"))
CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "car_concierge_kb")

# Knowledge base
KNOWLEDGE_BASE_PATH: str = str(BASE_DIR / "data" / "knowledge_base")

# App
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
PORT: int = int(os.getenv("PORT", "8000"))

# Policy constants — single source of truth
MINIMUM_SALE_YEAR: int = 2022
PENDING_DELISTING_LABEL: str = "Pending De-listing"
