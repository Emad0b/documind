import io
import pymupdf
from fastapi.testclient import TestClient
from app.main import app


def pdf(text=None):
    doc = pymupdf.open()
    page = doc.new_page()
    if text:
        page.insert_text((40, 70), text)
    raw = doc.tobytes()
    doc.close()
    return raw


def guest(client):
    assert client.post("/api/auth/guest").status_code == 200


def upload(client, text):
    response = client.post(
        "/api/documents", files={"file": ("evidence.pdf", pdf(text), "application/pdf")}
    )
    assert response.status_code == 202, response.text
    return response.json()["id"]


def test_upload_retrieval_evaluation_history_and_isolation():
    with TestClient(app) as alice, TestClient(app) as bob:
        guest(alice)
        guest(bob)
        did = upload(alice, "Solar panels generated 42 units of renewable electricity.")
        assert alice.get("/api/documents").json()[0]["status"] == "ready"
        assert bob.get("/api/documents").json() == []
        assert bob.get(f"/api/documents/{did}/pdf").status_code == 404
        assert bob.get(f"/api/documents/{did}/chunks").status_code == 404
        assert bob.get(f"/api/documents/{did}/pages/1").status_code == 404
        rendered = alice.get(f"/api/documents/{did}/pages/1")
        assert rendered.status_code == 200 and rendered.content.startswith(b"\x89PNG")
        assert alice.get(f"/api/documents/{did}/pages/99").status_code == 404
        assert bob.delete(f"/api/documents/{did}").status_code == 404
        body = {
            "question": "How much solar electricity was generated?",
            "document_ids": [did],
        }
        assert bob.post("/api/ask", json=body).status_code == 404
        result = alice.post("/api/ask", json=body).json()
        assert result["sources"][0]["page"] == 1
        assert "42 units" in result["answer"]
        cid = result["conversation_id"]
        assert [m["role"] for m in alice.get("/api/conversations/" + cid).json()] == [
            "user",
            "assistant",
        ]
        assert bob.get("/api/conversations/" + cid).status_code == 404
        assert (
            alice.get(f"/api/documents/{did}/pdf").headers["content-type"]
            == "application/pdf"
        )
        cases = [
            {
                "question": "solar electricity",
                "document_ids": [did],
                "expected": [{"document_id": did, "page": 1}],
            }
        ]
        evaluation = alice.post("/api/evaluate", json=cases).json()
        assert {r["mode"] for r in evaluation["results"]} == {
            "vector",
            "keyword",
            "hybrid",
        }
        assert evaluation["results"][2]["recall_at_5"] == 1
        assert bob.post("/api/evaluate", json=cases).status_code == 404
        assert alice.get("/api/usage").json()["questions"] == 1
        assert alice.delete("/api/documents/" + did).status_code == 200
        assert alice.get(f"/api/documents/{did}/chunks").status_code == 404


def test_duplicate_and_scanned_pdf():
    with TestClient(app) as client:
        guest(client)
        raw = pdf("Solar panels generate electricity.")
        first = client.post("/api/documents", files={"file": ("a.pdf", raw)}).json()
        second = client.post("/api/documents", files={"file": ("b.pdf", raw)}).json()
        assert second["duplicate"] and first["id"] == second["id"]
        scanned = client.post(
            "/api/documents", files={"file": ("scan.pdf", pdf())}
        ).json()
        doc = next(
            d for d in client.get("/api/documents").json() if d["id"] == scanned["id"]
        )
        assert doc["status"] == "failed" and "OCR" in doc["error"]
        assert (
            client.post(
                "/api/documents", files={"file": ("bad.pdf", b"not pdf")}
            ).status_code
            == 400
        )


def test_abstention_authentication_and_cross_origin():
    with TestClient(app) as client:
        assert client.get("/api/documents").status_code == 401
        credentials = {"username": "researcher", "password": "strong-password-123"}
        assert client.post("/api/auth/register", json=credentials).status_code == 200
        did = upload(client, "Solar energy is renewable electricity.")
        result = client.post(
            "/api/ask", json={"question": "zzzxq quantum banana", "document_ids": [did]}
        ).json()
        assert result["abstained"]
        assert (
            client.post(
                "/api/ask",
                json={"question": "solar", "document_ids": [did]},
                headers={"origin": "https://evil.example"},
            ).status_code
            == 403
        )
        assert client.post("/api/auth/logout").status_code == 200
        assert client.get("/api/documents").status_code == 401
        assert (
            client.post(
                "/api/auth/login", json={**credentials, "password": "wrong-password"}
            ).status_code
            == 401
        )
        assert client.post("/api/auth/login", json=credentials).status_code == 200
        assert client.get("/api/documents").json()[0]["id"] == did


def test_compare_requires_evidence_from_both_documents():
    with TestClient(app) as client:
        guest(client)
        a = upload(client, "Solar training cost was 42 units.")
        b = upload(client, "Fishing regulations cover rivers and lakes.")
        result = client.post(
            "/api/ask",
            json={
                "question": "solar training cost",
                "document_ids": [a, b],
                "compare": True,
            },
        ).json()
        assert result["abstained"]
