import hashlib, json, secrets, time, uuid, hmac
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Depends,
    Response,
    HTTPException,
    BackgroundTasks,
    Request,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from .core import config
from .core.database import db, sql, initialize, PG
from .core.security import (
    current_user,
    issue_session,
    password_hash,
    authorize_documents,
)
from .ingestion.parser import parse_pdf
from .ingestion.chunker import split_page
from .ingestion.embeddings import encode, model_id
from .retrieval.hybrid import retrieve
from .generation.llm import answer_question


@asynccontextmanager
async def lifespan(app):
    initialize()
    with db() as conn:
        sql(
            conn,
            "UPDATE documents SET status='failed',error='Processing interrupted by restart; delete and upload again' WHERE status IN ('parsing','embedding')",
        )
    yield


app = FastAPI(title="DocuMind — Evaluated Document Intelligence", lifespan=lifespan)


@app.middleware("http")
async def origin_guard(request, call_next):
    from urllib.parse import urlparse
    from fastapi.responses import JSONResponse

    if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get(
        "origin"
    ):
        if urlparse(request.headers["origin"]).netloc != request.headers.get("host"):
            return JSONResponse(
                {"detail": "Cross-origin writes are not allowed"}, status_code=403
            )
    return await call_next(request)


@app.get("/api/health")
def health():
    return dict(
        status="ok",
        storage="PostgreSQL / pgvector" if PG else "SQLite local profile",
        generation=bool(config.LLM_API_KEY),
        embedding=config.EMBEDDING_BACKEND,
        model=model_id(),
    )


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=200)


@app.post("/api/auth/register")
def register(req: Credentials, response: Response):
    uid = str(uuid.uuid4())
    with db() as conn:
        if sql(
            conn, "SELECT id FROM users WHERE username=?", (req.username.lower(),)
        ).fetchone():
            raise HTTPException(409, "Username already exists")
        sql(
            conn,
            "INSERT INTO users VALUES (?,?,?)",
            (uid, req.username.lower(), password_hash(req.password)),
        )
    issue_session(response, uid)
    return dict(id=uid, username=req.username)


@app.post("/api/auth/login")
def login(req: Credentials, response: Response):
    with db() as conn:
        row = sql(
            conn,
            "SELECT id,password FROM users WHERE username=?",
            (req.username.lower(),),
        ).fetchone()
    if (
        not row
        or not row[1]
        or not hmac.compare_digest(
            row[1], password_hash(req.password, row[1].split(":")[0])
        )
    ):
        raise HTTPException(401, "Invalid username or password")
    issue_session(response, row[0])
    return dict(id=row[0], username=req.username)


@app.post("/api/auth/guest")
def guest(response: Response):
    if not config.ALLOW_GUEST:
        raise HTTPException(403, "Guest workspaces disabled")
    uid = str(uuid.uuid4())
    with db() as conn:
        sql(conn, "INSERT INTO users VALUES (?,?,?)", (uid, "guest-" + uid, None))
    issue_session(response, uid)
    return dict(id=uid, username="Guest workspace")


@app.get("/api/auth/me")
def me(owner=Depends(current_user)):
    with db() as conn:
        row = sql(conn, "SELECT username FROM users WHERE id=?", (owner,)).fetchone()
    return dict(id=owner, username=row[0])


@app.post("/api/auth/logout")
def logout(response: Response, request: Request, owner=Depends(current_user)):
    token = request.cookies.get("documind_session", "")
    with db() as conn:
        sql(
            conn,
            "DELETE FROM sessions WHERE token=?",
            (hashlib.sha256(token.encode()).hexdigest(),),
        )
    response.delete_cookie("documind_session")
    return {"ok": True}


def process_document(did, raw):
    try:
        pages = parse_pdf(raw)
        with db() as conn:
            sql(
                conn,
                "UPDATE documents SET status=?,pages=? WHERE id=?",
                ("embedding", len(pages), did),
            )
        parts = [
            (page, position, chunk)
            for page, text in enumerate(pages, 1)
            for position, chunk in enumerate(split_page(text))
        ]
        vectors = encode([part[2] for part in parts])
        with db() as conn:
            for (page, position, text), vector in zip(parts, vectors):
                sql(
                    conn,
                    "INSERT INTO chunks (id,doc,page,position,text,embedding,model) VALUES (?,?,?,?,?,?,?)",
                    (
                        str(uuid.uuid4()),
                        did,
                        page,
                        position,
                        text,
                        json.dumps(vector),
                        model_id(),
                    ),
                )
            sql(conn, "UPDATE documents SET status=? WHERE id=?", ("ready", did))
    except Exception as error:
        message = (
            str(error)
            if isinstance(error, ValueError)
            else "Processing failed. Check server logs and model availability."
        )
        import logging

        logging.exception("Document processing failed: %s", did)
        with db() as conn:
            sql(conn, "DELETE FROM chunks WHERE doc=?", (did,))
            sql(
                conn,
                "UPDATE documents SET status=?,error=? WHERE id=?",
                ("failed", message, did),
            )


@app.get("/api/documents")
def documents(owner=Depends(current_user)):
    with db() as conn:
        rows = sql(
            conn,
            "SELECT id,name,pages,status,error FROM documents WHERE owner=? ORDER BY created DESC",
            (owner,),
        ).fetchall()
    return [dict(id=r[0], name=r[1], pages=r[2], status=r[3], error=r[4]) for r in rows]


@app.post("/api/documents", status_code=202)
async def upload(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    owner=Depends(current_user),
):
    raw = await file.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(413, "Maximum PDF size is 20 MB")
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(400, "Upload a valid PDF")
    digest = hashlib.sha256(raw).hexdigest()
    did = str(uuid.uuid4())
    name = (file.filename or "document.pdf").replace("\\", "/").rsplit("/", 1)[-1][:200]
    with db() as conn:
        previous = sql(
            conn,
            "SELECT id,name,pages,status,error FROM documents WHERE owner=? AND digest=?",
            (owner, digest),
        ).fetchone()
        if previous:
            return dict(
                id=previous[0],
                name=previous[1],
                pages=previous[2],
                status=previous[3],
                error=previous[4],
                duplicate=True,
            )
        sql(
            conn,
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
            (did, owner, name, 0, digest, "parsing", None, time.time()),
        )
    try:
        (config.FILES / (did + ".pdf")).write_bytes(raw)
    except OSError:
        with db() as conn:
            sql(conn, "DELETE FROM documents WHERE id=?", (did,))
        raise HTTPException(500, "Could not store PDF")
    background.add_task(process_document, did, raw)
    return dict(id=did, name=name, pages=0, status="parsing", error=None)


@app.get("/api/documents/{did}/pdf")
def pdf(did: str, owner=Depends(current_user)):
    with db() as conn:
        row = sql(
            conn, "SELECT name FROM documents WHERE id=? AND owner=?", (did, owner)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    path = config.FILES / (did + ".pdf")
    if not path.is_file():
        raise HTTPException(404, "Stored PDF missing")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=row[0],
        content_disposition_type="inline",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@app.get("/api/documents/{did}/chunks")
def chunks(did: str, owner=Depends(current_user)):
    authorize_documents(owner, [did])
    with db() as conn:
        rows = sql(
            conn,
            "SELECT id,page,position,text FROM chunks WHERE doc=? ORDER BY page,position",
            (did,),
        ).fetchall()
    return [dict(id=r[0], page=r[1], position=r[2], text=r[3]) for r in rows]


@app.delete("/api/documents/{did}")
def delete(did: str, owner=Depends(current_user)):
    with db() as conn:
        row = sql(
            conn, "SELECT status FROM documents WHERE id=? AND owner=?", (did, owner)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Document not found")
        if row[0] in ("parsing", "embedding"):
            raise HTTPException(409, "Wait for processing before deleting")
        sql(conn, "DELETE FROM documents WHERE id=? AND owner=?", (did, owner))
    (config.FILES / (did + ".pdf")).unlink(missing_ok=True)
    return dict(deleted=True)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] = Field(min_length=1, max_length=20)
    conversation_id: str | None = None
    compare: bool = False
    retrieval_mode: str = Field(default="hybrid", pattern="^(hybrid|vector|keyword)$")


@app.get("/api/conversations")
def conversations(owner=Depends(current_user)):
    with db() as conn:
        rows = sql(
            conn,
            "SELECT id,title,created FROM conversations WHERE owner=? ORDER BY created DESC",
            (owner,),
        ).fetchall()
    return [dict(id=r[0], title=r[1], created=r[2]) for r in rows]


@app.get("/api/conversations/{cid}")
def history(cid: str, owner=Depends(current_user)):
    with db() as conn:
        if not sql(
            conn, "SELECT id FROM conversations WHERE id=? AND owner=?", (cid, owner)
        ).fetchone():
            raise HTTPException(404, "Conversation not found")
        rows = sql(
            conn,
            "SELECT role,payload FROM messages WHERE conversation=? ORDER BY created,id",
            (cid,),
        ).fetchall()
    return [dict(role=r[0], **json.loads(r[1])) for r in rows]


@app.post("/api/ask")
async def ask(req: Question, owner=Depends(current_user)):
    start = time.perf_counter()
    authorize_documents(owner, req.document_ids)
    if req.compare and len(set(req.document_ids)) != 2:
        raise HTTPException(400, "Compare exactly two documents")
    cid = req.conversation_id or str(uuid.uuid4())
    prior = history(cid, owner) if req.conversation_id else []
    if req.compare:
        sources = []
        for did in req.document_ids:
            sources += await run_in_threadpool(
                retrieve, req.question, [did], owner, 3, req.retrieval_mode
            )
        if len({s["document_id"] for s in sources}) < 2:
            sources = []
    else:
        sources = await run_in_threadpool(
            retrieve, req.question, req.document_ids, owner, 5, req.retrieval_mode
        )
    try:
        result = await answer_question(
            req.question,
            sources,
            req.compare,
            [
                {"role": m["role"], "text": m.get("text", m.get("answer", ""))[:2000]}
                for m in prior[-6:]
            ],
        )
    except Exception:
        import logging

        logging.exception("Generation failed")
        raise HTTPException(
            502, "Answer provider failed. Check the server configuration."
        )
    result.update(
        conversation_id=cid, latency_ms=round((time.perf_counter() - start) * 1000, 1)
    )
    with db() as conn:
        if not req.conversation_id:
            sql(
                conn,
                "INSERT INTO conversations VALUES (?,?,?,?)",
                (cid, owner, req.question[:70], time.time()),
            )
        sql(
            conn,
            "INSERT INTO messages VALUES (?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                cid,
                "user",
                json.dumps({"text": req.question}),
                time.time(),
            ),
        )
        sql(
            conn,
            "INSERT INTO messages VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), cid, "assistant", json.dumps(result), time.time()),
        )
        sql(
            conn,
            "INSERT INTO usage VALUES (?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                owner,
                result["latency_ms"],
                result["input_tokens"],
                result["output_tokens"],
                result["cost"],
                time.time(),
            ),
        )
    return result


class Evidence(BaseModel):
    document_id: str
    page: int = Field(ge=1)


class EvalCase(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] = Field(min_length=1, max_length=20)
    expected: list[Evidence]


@app.post("/api/evaluate")
def evaluate(cases: list[EvalCase], owner=Depends(current_user)):
    if not 1 <= len(cases) <= 100:
        raise HTTPException(400, "Provide 1–100 evaluation cases")
    for case in cases:
        authorize_documents(owner, case.document_ids)
    results = []
    for mode in ("vector", "keyword", "hybrid"):
        details = []
        for case in cases:
            start = time.perf_counter()
            sources = retrieve(case.question, case.document_ids, owner, 10, mode)
            expected = {(e.document_id, e.page) for e in case.expected}
            found = [(s["document_id"], s["page"]) for s in sources]
            details.append(
                dict(
                    question=case.question,
                    recall_at_5=len(set(found[:5]) & expected) / len(expected)
                    if expected
                    else None,
                    mrr_at_10=next(
                        (1 / (i + 1) for i, key in enumerate(found) if key in expected),
                        0,
                    )
                    if expected
                    else None,
                    expected_unanswerable=not expected,
                    retrieval_abstained=not sources,
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                    sources=sources,
                )
            )
        answerable = [d for d in details if d["recall_at_5"] is not None]
        results.append(
            dict(
                mode=mode,
                recall_at_5=sum(d["recall_at_5"] for d in answerable)
                / max(1, len(answerable)),
                mrr_at_10=sum(d["mrr_at_10"] for d in answerable)
                / max(1, len(answerable)),
                cases=details,
            )
        )
    return dict(
        results=results,
        embedding=model_id(),
        note="Retrieval abstention is a proxy, not generated-answer accuracy or citation entailment.",
    )


@app.get("/api/usage")
def usage(owner=Depends(current_user)):
    with db() as conn:
        rows = sql(
            conn,
            "SELECT latency,input_tokens,output_tokens,cost FROM usage WHERE owner=?",
            (owner,),
        ).fetchall()
    latency = sorted(r[0] for r in rows)

    def percentile(p):
        return (
            latency[min(len(latency) - 1, int((len(latency) - 1) * p))]
            if latency
            else 0
        )

    return dict(
        questions=len(rows),
        input_tokens=sum(r[1] for r in rows),
        output_tokens=sum(r[2] for r in rows),
        cost=sum(r[3] for r in rows)
        if rows and all(r[3] is not None for r in rows)
        else None,
        p50_ms=percentile(0.5),
        p95_ms=percentile(0.95),
    )
