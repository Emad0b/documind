import os, tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="documind-test-", dir=".")
os.environ["EMBEDDING_BACKEND"] = "lexical"
os.environ["MIN_SIMILARITY"] = "0.35"
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
else:
    os.environ.pop("DATABASE_URL", None)
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("LLM_API_KEY", None)
