import os
from pathlib import Path

DATA = Path(os.getenv("DATA_DIR", "./data")).resolve()
DATA.mkdir(parents=True, exist_ok=True)
FILES = DATA / "pdfs"
FILES.mkdir(exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL")
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "sentence-transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DIMENSIONS = 384
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "180"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "35"))
if not 0 <= CHUNK_OVERLAP < CHUNK_SIZE:
    raise ValueError("Chunk overlap must be smaller than chunk size")
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.35"))
RRF_K = int(os.getenv("RRF_K", "60"))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
SECURE_COOKIES = os.getenv("SECURE_COOKIES", "false").lower() == "true"
ALLOW_GUEST = os.getenv("ALLOW_GUEST", "true").lower() == "true"
