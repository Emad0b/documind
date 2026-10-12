"""Run from backend: python ../evaluations/evaluate_retrieval.py [--semantic]."""

import os, sys, json, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DATA_DIR"] = tempfile.mkdtemp(
    prefix="documind-benchmark-", dir=ROOT / "backend"
)
os.environ["EMBEDDING_BACKEND"] = (
    "sentence-transformers" if "--semantic" in sys.argv else "lexical"
)
os.environ.pop("DATABASE_URL", None)
os.environ.pop("LLM_API_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)
import pymupdf
from fastapi.testclient import TestClient
from app.main import app

dataset = json.loads((ROOT / "evaluations/datasets/synthetic.json").read_text())
with TestClient(app) as client:
    client.post("/api/auth/guest")
    mapping = {}
    for d in dataset["documents"]:
        pdf = pymupdf.open()
        for text in d["pages"]:
            pdf.new_page().insert_textbox((40, 40, 555, 790), text, fontsize=12)
        r = client.post(
            "/api/documents",
            files={"file": (d["name"] + ".pdf", pdf.tobytes(), "application/pdf")},
        )
        pdf.close()
        if r.status_code != 202:
            raise RuntimeError(r.text)
        mapping[d["name"]] = r.json()["id"]
    documents = client.get("/api/documents").json()
    if any(d["status"] != "ready" for d in documents):
        raise RuntimeError(str(documents))
    cases = [
        dict(
            question=c["question"],
            document_ids=[mapping[n] for n in c["documents"]],
            expected=[
                dict(document_id=mapping[e["document"]], page=e["page"])
                for e in c["expected"]
            ],
        )
        for c in dataset["cases"]
    ]
    r = client.post("/api/evaluate", json=cases)
    if r.status_code != 200:
        raise RuntimeError(r.text)
    result = r.json()
    result.update(
        dataset=dataset["description"],
        storage="SQLite local profile",
        generated_answers_evaluated=False,
    )
    for baseline in result["results"]:
        cases = baseline["cases"]
        times = sorted(c["latency_ms"] for c in cases)
        tp = sum(c["retrieval_abstained"] and c["expected_unanswerable"] for c in cases)
        predicted = sum(c["retrieval_abstained"] for c in cases)
        expected = sum(c["expected_unanswerable"] for c in cases)
        baseline.update(
            abstention_precision=tp / predicted if predicted else None,
            abstention_recall=tp / expected if expected else None,
            p50_ms=times[int((len(times) - 1) * 0.5)],
            p95_ms=times[int((len(times) - 1) * 0.95)],
        )
    path = (
        ROOT
        / "evaluations"
        / (
            "results-semantic.json"
            if "--semantic" in sys.argv
            else "results-lexical.json"
        )
    )
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "file": str(path),
                "model": result["embedding"],
                "baselines": [
                    {k: v for k, v in r.items() if k != "cases"}
                    for r in result["results"]
                ],
            },
            indent=2,
        )
    )
