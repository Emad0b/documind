# Deployment

Run the full Docker stack locally with `docker compose up --build`, then open http://localhost:8080. PostgreSQL and PDF/model volumes persist independently of containers. First semantic ingestion downloads the embedding model; allow time and disk space for the model and PyTorch.

For public hosting, deploy the frontend nginx container and FastAPI container behind one HTTPS origin, with a managed PostgreSQL database supporting pgvector and a durable private file volume. Configure DATABASE_URL, a private provider key, SECURE_COOKIES=true, and ALLOW_GUEST=false. Do not expose PostgreSQL or mount uploads into a public static directory. Keep proxy Host preservation. Use a single API worker for this version's in-process ingestion.

Public hosting still needs request throttling, per-account storage limits, queued ingestion, operational backups, restore testing, and account recovery. This version's migration is idempotent initial schema setup, not a general schema-upgrade framework. Existing Folio tables/data are retained and are not imported into DocuMind's ownership model.

The current machine has no Docker executable. PostgreSQL integration and browser checks passed in GitHub Actions. The Docker image configuration has not been built on this machine. A public live deployment requires a hosting account/project; the local browser preview is not a public URL.

