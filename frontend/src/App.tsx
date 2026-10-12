import { useState, useEffect, useRef } from "react";
import {
  FileText,
  Plus,
  ArrowUp,
  ArrowUpRight,
  Search,
  Layers,
  MessageSquare,
  PanelLeft,
  Check,
  Trash2,
  Upload,
  ChevronRight,
  BookOpen,
  Sparkles,
  X,
  LoaderCircle,
  ChartNoAxesCombined,
  LogOut,
} from "lucide-react";
import { api, post } from "./services/api";
import { Evaluations } from "./components/Evaluations";
import type {
  Document,
  Message,
  Source,
  Answer,
  Conversation,
  Health,
  User,
} from "./types";

export default function App() {
  const [docs, setDocs] = useState<Document[]>([]),
    [selected, setSelected] = useState<string[]>([]),
    [messages, setMessages] = useState<Message[]>([]),
    [question, setQuestion] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [source, setSource] = useState<(Source & { index: number }) | null>(null),
    [compare, setCompare] = useState(false),
    [health, setHealth] = useState<Health | null>(null),
    [filter, setFilter] = useState(""),
    [mobile, setMobile] = useState(false),
    [user, setUser] = useState<User | null>(null),
    [checking, setChecking] = useState(true),
    [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [register, setRegister] = useState(false),
    [view, setView] = useState<"chat" | "evaluation">("chat"),
    [conversations, setConversations] = useState<Conversation[]>([]),
    [cid, setCid] = useState<string | null>(null),
    [usage, setUsage] = useState<{
      questions: number;
      p50_ms: number;
      p95_ms: number;
      input_tokens: number;
      output_tokens: number;
      cost: number | null;
    } | null>(null);
  const upload = useRef<HTMLInputElement>(null),
    bottom = useRef<HTMLDivElement>(null);
  async function refresh() {
    setDocs(await api<Document[]>("/documents"));
    setHealth(await api<Health>("/health"));
    setConversations(await api<Conversation[]>("/conversations"));
    setUsage(await api("/usage"));
  }
  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setChecking(false));
  }, []);
  useEffect(() => {
    if (user) {
      refresh().catch((e) => setError(e.message));
      const timer = setInterval(() => refresh().catch(() => {}), 2500);
      return () => clearInterval(timer);
    }
  }, [user]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);
  async function authenticate(guest = false) {
    setError("");
    setBusy(true);
    try {
      setUser(
        await post<User>(
          guest ? "/auth/guest" : register ? "/auth/register" : "/auth/login",
          guest ? {} : { username, password },
        ),
      );
      setPassword("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function add(files: FileList | null) {
    if (!files) return;
    setError("");
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        const body = new FormData();
        body.append("file", file);
        const doc = await api<Document>("/documents", { method: "POST", body });
        setSelected((s) => Array.from(new Set([...s, doc.id])));
      }
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function ask(text = question) {
    if (!text.trim() || busy) return;
    const ready = selected.filter(
      (id) => docs.find((d) => d.id === id)?.status === "ready",
    );
    if (!ready.length) {
      setError("Select a document that has finished processing.");
      return;
    }
    if (compare && ready.length !== 2) {
      setError("Select exactly two ready documents to compare.");
      return;
    }
    setError("");
    setQuestion("");
    setMessages((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      const r = await post<Answer>("/ask", {
        question: text,
        document_ids: ready,
        compare,
        conversation_id: cid,
      });
      setCid(r.conversation_id);
      setMessages((m) => [...m, { role: "assistant", ...r }]);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove(id: string) {
    try {
      await api("/documents/" + id, { method: "DELETE" });
      setSelected((s) => s.filter((x) => x !== id));
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function openConversation(id: string) {
    try {
      const saved = await api<Message[]>("/conversations/" + id);
      setMessages(saved);
      setSelected(
        Array.from(
          new Set(
            saved.flatMap((m) =>
              m.role === "assistant" ? m.sources.map((s) => s.document_id) : [],
            ),
          ),
        ),
      );
      setCid(id);
      setView("chat");
      setMobile(false);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const prompts = [
    ["Find the big picture", "What are the main findings and conclusions?"],
    ["Follow the evidence", "What evidence supports the main claims?"],
    ["Explore the details", "What limitations and risks are discussed?"],
  ];
  if (checking)
    return (
      <div className="auth">
        <LoaderCircle className="spin" /> Opening your workspace…
      </div>
    );
  if (!user)
    return (
      <div className="auth">
        <div className="auth-card">
          <div className="brand">
            <span className="logo">
              <Layers size={21} />
            </span>
            DocuMind
          </div>
          <h1>
            Your evidence.
            <br />
            <em>Your workspace.</em>
          </h1>
          <p>
            Read deeply. Ask better questions. Follow every answer to its
            source.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              authenticate();
            }}
          >
            <label>
              Username
              <input
                autoComplete="username"
                minLength={3}
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                minLength={10}
                autoComplete={register ? "new-password" : "current-password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <button className="primary" disabled={busy}>
              {register ? "Create account" : "Sign in"}
            </button>
          </form>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button onClick={() => setRegister(!register)}>
            {register
              ? "Already have an account? Sign in"
              : "Create a persistent account"}
          </button>
          <button
            className="guest"
            disabled={busy}
            onClick={() => authenticate(true)}
          >
            Try an isolated guest workspace <ArrowUpRight size={14} />
          </button>
          <small>
            Guest sessions last 7 days. Create an account to retain access.
          </small>
        </div>
      </div>
    );
  return (
    <div className="app">
      <aside className={mobile ? "sidebar open" : "sidebar"}>
        <a className="brand" href="#">
          <span className="logo">
            <Layers size={21} />
          </span>
          DocuMind
        </a>
        <div className="workspace">
          <span className="avatar">{user.username[0].toUpperCase()}</span>
          <div>
            {user.username.startsWith("guest-")
              ? "Guest workspace"
              : user.username}
            <small>Your knowledge, connected</small>
          </div>
        </div>
        <button
          className="new-chat"
          disabled={busy}
          onClick={() => {
            setMessages([]);
            setCid(null);
            setSource(null);
            setMobile(false);
            setView("chat");
          }}
        >
          <Plus size={17} /> New conversation <span>↗</span>
        </button>
        <div className="section-label">WORKSPACE</div>
        <button
          className={"nav " + (view === "chat" ? "active" : "")}
          onClick={() => {
            setView("chat");
            setMobile(false);
          }}
        >
          <MessageSquare size={17} /> Document chat{" "}
          <span className="badge">{conversations.length}</span>
        </button>
        <button
          className={"nav " + (compare ? "active" : "")}
          onClick={() => {
            setCompare(!compare);
            setView("chat");
          }}
        >
          <Layers size={17} /> Compare documents
        </button>
        <button
          className={"nav " + (view === "evaluation" ? "active" : "")}
          onClick={() => {
            setView("evaluation");
            setMobile(false);
          }}
        >
          <ChartNoAxesCombined size={17} /> Retrieval evaluation
        </button>
        {conversations.length > 0 && (
          <details className="history-list">
            <summary>Recent conversations</summary>
            {conversations.slice(0, 8).map((c) => (
              <button key={c.id} onClick={() => openConversation(c.id)}>
                {c.title}
              </button>
            ))}
          </details>
        )}
        <div className="section-label library-label">
          YOUR LIBRARY{" "}
          <button title="Upload PDFs" onClick={() => upload.current?.click()}>
            <Plus size={16} />
          </button>
        </div>
        <div className="search">
          <Search size={14} />
          <input
            aria-label="Search documents"
            placeholder="Search documents"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <div className="documents">
          {docs
            .filter((d) => d.name.toLowerCase().includes(filter.toLowerCase()))
            .map((d) => (
              <div
                className={
                  "document " + (selected.includes(d.id) ? "chosen" : "")
                }
                key={d.id}
              >
                <button
                  className="doc-select"
                  title={d.error || d.name}
                  onClick={() =>
                    setSelected((s) =>
                      s.includes(d.id)
                        ? s.filter((x) => x !== d.id)
                        : [...s, d.id],
                    )
                  }
                >
                  <FileText size={19} />
                  <span>
                    {d.name}
                    <small>
                      {d.status === "ready"
                        ? `${d.pages} pages · Ready`
                        : d.status === "failed"
                          ? d.error
                          : d.status + "…"}
                    </small>
                  </span>
                  {selected.includes(d.id) && <Check size={14} />}
                </button>
                <button
                  className="delete"
                  disabled={d.status === "parsing" || d.status === "embedding"}
                  aria-label={"Delete " + d.name}
                  onClick={() => remove(d.id)}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          {!docs.length && (
            <p className="library-empty">
              A little space for your next big discovery. Add your first PDF
              below.
            </p>
          )}
        </div>
        <button
          className="upload-card"
          disabled={busy}
          onClick={() => upload.current?.click()}
        >
          <Upload size={19} />
          <strong>Add to your library</strong>
          <small>PDF files · up to 20 MB</small>
        </button>
        <div className="sidebar-footer">
          <span className="avatar small">D</span>
          <div>
            Private workspace
            <small>
              {usage?.questions || 0} questions · p95{" "}
              {usage?.p95_ms?.toFixed(0) || 0} ms
            </small>
          </div>
          <button
            aria-label="Sign out"
            onClick={async () => {
              await post("/auth/logout", {});
              setUser(null);
              setDocs([]);
              setMessages([]);
              setSelected([]);
              setCid(null);
              setSource(null);
            }}
          >
            <LogOut size={15} />
          </button>
        </div>
      </aside>
      <main>
        <header>
          <button
            className="mobile-toggle"
            aria-label="Toggle library"
            onClick={() => setMobile(!mobile)}
          >
            <PanelLeft size={19} />
          </button>
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />{" "}
            <span>
              {view === "evaluation"
                ? "Retrieval evaluation"
                : compare
                  ? "Document comparison"
                  : "Document chat"}
            </span>
          </div>
          <span className="private">
            <span className="status-dot" />{" "}
            {health?.embedding === "sentence-transformers"
              ? "Semantic retrieval"
              : "Lexical development mode"}
          </span>
        </header>
        <div className="chat-scroll">
          {view === "evaluation" ? (
            <Evaluations documents={docs} />
          ) : !messages.length ? (
            <section className="welcome">
              <div className="eyebrow">
                <span /> A CLEARER WAY TO UNDERSTAND
              </div>
              <h1>
                Your documents.
                <br />
                <em>A whole new perspective.</em>
              </h1>
              <p>
                Turn pages of information into answers you can inspect.
                <br />
                Ask, explore, and connect the dots—with sources at every step.
              </p>
              <div
                className="dropzone"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  add(e.dataTransfer.files);
                }}
              >
                <div className="paper-stack">
                  <FileText size={29} />
                </div>
                <h3>Start with a document</h3>
                <p>Drop your PDF here, or browse your files</p>
                <button onClick={() => upload.current?.click()} disabled={busy}>
                  <Plus size={16} /> Upload document
                </button>
                <small>Text-based PDFs · Maximum 20 MB per file</small>
              </div>
              <div className="prompt-heading">A FEW WAYS TO GET CURIOUS</div>
              <div className="prompts">
                {prompts.map(([title, q], i) => (
                  <button key={title} disabled={busy} onClick={() => ask(q)}>
                    <span className="prompt-icon">
                      {i === 0 ? (
                        <BookOpen size={17} />
                      ) : i === 1 ? (
                        <Search size={17} />
                      ) : (
                        <Sparkles size={17} />
                      )}
                    </span>
                    <strong>{title}</strong>
                    <span>{q}</span>
                    <ArrowUpRight size={15} className="prompt-arrow" />
                  </button>
                ))}
              </div>
              <div className="trust">
                <Check size={13} /> Page-level citations <span>·</span>{" "}
                Multi-document search <span>·</span> Evidence you can inspect
              </div>
            </section>
          ) : (
            <section className="conversation">
              {messages.map((m, i) => (
                <article className={"message " + m.role} key={i}>
                  <div className="message-avatar">
                    {m.role === "user" ? "You" : <Layers size={17} />}
                  </div>
                  <div>
                    <strong>
                      {m.role === "user" ? "You" : "DocuMind"}
                      {m.role === "assistant" && (
                        <small>
                          {m.mode === "extractive"
                            ? "Source excerpts"
                            : m.abstained
                              ? "Insufficient evidence"
                              : "Grounded answer"}
                        </small>
                      )}
                    </strong>
                    <div className="answer">
                      {m.role === "user" ? m.text : m.answer}
                    </div>
                    {m.role === "assistant" && m.sources?.length > 0 && (
                      <div className="sources">
                        {m.sources.map((s, j) => (
                          <button
                            key={s.id}
                            onClick={() => setSource({ ...s, index: j + 1 })}
                          >
                            <span>{j + 1}</span>
                            <FileText size={13} />
                            {s.name} <b>p. {s.page}</b>
                          </button>
                        ))}
                      </div>
                    )}
                    {m.role === "assistant" && (
                      <>
                        <div className="citation-note">
                          <Check size={12} />
                          {m.citation_check}
                        </div>
                        <div className="citation-note">
                          {m.latency_ms} ms · {m.input_tokens + m.output_tokens}{" "}
                          tokens ·{" "}
                          {m.cost === null
                            ? "Cost rates not configured"
                            : "$" + m.cost.toFixed(6)}
                        </div>
                      </>
                    )}
                  </div>
                </article>
              ))}
              {busy && (
                <div className="thinking">
                  <LoaderCircle size={16} className="spin" /> Reading your
                  documents…
                </div>
              )}
              <div ref={bottom} />
            </section>
          )}
        </div>
        {view === "chat" && (
          <div className="composer-wrap">
            {error && (
              <div className="error" role="alert">
                {error}
                <button aria-label="Dismiss" onClick={() => setError("")}>
                  <X size={14} />
                </button>
              </div>
            )}
            <div className="composer">
              <div className="context">
                <FileText size={13} />
                {selected.length
                  ? `${selected.length} documents selected`
                  : "Add a document to begin"}
                <button
                  onClick={() => setCompare(!compare)}
                  className={compare ? "mode selected" : "mode"}
                >
                  <Layers size={12} />
                  {compare ? "Comparison on" : "Compare"}
                </button>
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  ask();
                }}
              >
                <input
                  aria-label="Ask about your documents"
                  placeholder={
                    compare
                      ? "Ask what changed between your documents…"
                      : "Ask anything about your documents…"
                  }
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                />
                <button
                  className="send"
                  aria-label="Send question"
                  disabled={busy || !question.trim()}
                >
                  {busy ? (
                    <LoaderCircle size={19} className="spin" />
                  ) : (
                    <ArrowUp size={19} />
                  )}
                </button>
              </form>
            </div>
            <div className="composer-note">
              {health?.generation
                ? "Review quoted evidence. Valid citations do not guarantee factual accuracy."
                : "Extractive mode · Configure a server LLM key for generated answers."}
            </div>
          </div>
        )}
      </main>
      {source && (
        <aside className="source-panel">
          <div>
            <strong>Source evidence</strong>
            <button aria-label="Close source" onClick={() => setSource(null)}>
              <X size={18} />
            </button>
          </div>
          <span className="source-tag">CITATION {source.index}</span>
          <h3>{source.name}</h3>
          <p className="page-label">Page {source.page}</p>
          <a
            className="primary pdf-link"
            href={`/api/documents/${source.document_id}/pdf#page=${source.page}`}
            target="_blank"
            rel="noreferrer"
          >
            Open cited PDF page <ArrowUpRight size={14} />
          </a>
          <a
            href={`/api/documents/${source.document_id}/pages/${source.page}?chunk_id=${source.id}`}
            target="_blank"
            rel="noreferrer"
            title="View rendered page at full size"
          >
            <img
              alt={`Cited PDF page ${source.page} with highlighted evidence`}
              src={`/api/documents/${source.document_id}/pages/${source.page}?chunk_id=${source.id}`}
              className="pdf-preview"
            />
          </a>
          <blockquote>{source.text}</blockquote>
          <p className="source-foot">
            Retrieved passage · similarity {source.similarity.toFixed(3)}. Check
            the original page for full context.
          </p>
        </aside>
      )}
      <input
        ref={upload}
        type="file"
        accept="application/pdf"
        multiple
        hidden
        onChange={(e) => {
          add(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
