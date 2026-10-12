import { useState } from "react";
import { post } from "../services/api";
import type { Document, EvaluationCase, EvaluationResult } from "../types";
export function Evaluations({ documents }: { documents: Document[] }) {
  const [question, setQuestion] = useState(""),
    [document, setDocument] = useState(""),
    [page, setPage] = useState("1"),
    [unanswerable, setUnanswerable] = useState(false),
    [cases, setCases] = useState<EvaluationCase[]>([]),
    [result, setResult] = useState<EvaluationResult | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  function add() {
    const id = document || documents.find((d) => d.status === "ready")?.id;
    if (!id || !question.trim()) {
      setError("Choose a ready document and enter a question.");
      return;
    }
    setCases((c) => [
      ...c,
      {
        question: question.trim(),
        document_ids: [id],
        expected: unanswerable
          ? []
          : [{ document_id: id, page: Math.max(1, Number(page) || 1) }],
      },
    ]);
    setQuestion("");
    setResult(null);
    setError("");
  }
  async function run() {
    setBusy(true);
    setError("");
    try {
      setResult(await post<EvaluationResult>("/evaluate", cases));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function download() {
    const a = window.document.createElement("a");
    a.href = URL.createObjectURL(
      new Blob([JSON.stringify({ cases, result }, null, 2)], {
        type: "application/json",
      }),
    );
    a.download = "documind-evaluation.json";
    a.click();
    URL.revokeObjectURL(a.href);
  }
  return (
    <section className="evaluation">
      <div className="eyebrow">MEASURE BEFORE YOU CLAIM</div>
      <h1>Evidence under the microscope.</h1>
      <p>
        Compare vector, keyword, and hybrid retrieval on questions you label.
        Relevant evidence is identified by document and page.
      </p>
      <div className="eval-builder">
        <label>
          Question
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What is the reported training cost?"
          />
        </label>
        <label>
          Document
          <select
            value={document}
            onChange={(e) => setDocument(e.target.value)}
          >
            <option value="">Choose a document</option>
            {documents
              .filter((d) => d.status === "ready")
              .map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          Expected page
          <input
            type="number"
            min="1"
            disabled={unanswerable}
            value={page}
            onChange={(e) => setPage(e.target.value)}
          />
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={unanswerable}
            onChange={(e) => setUnanswerable(e.target.checked)}
          />{" "}
          Intentionally unanswerable
        </label>
        <button className="primary" onClick={add}>
          Add test case
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="eval-cases">
        {cases.map((c, i) => (
          <div key={i}>
            <span>
              {i + 1}. {c.question}
            </span>
            <small>
              {c.expected.length
                ? "Page " + c.expected[0].page
                : "Unanswerable"}
            </small>
            <button
              aria-label="Remove test case"
              onClick={() => {
                setCases((cs) => cs.filter((_, j) => i !== j));
                setResult(null);
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
      <div className="eval-actions">
        <button
          className="primary"
          disabled={!cases.length || busy}
          onClick={run}
        >
          {busy ? "Evaluating…" : "Run three retrieval baselines"}
        </button>
        <button disabled={!cases.length} onClick={download}>
          Export cases and results
        </button>
      </div>
      {result && (
        <>
          <div className="eval-baselines">
            {result.results.map((r) => (
              <article key={r.mode}>
                <h3>{r.mode}</h3>
                <strong>{(r.recall_at_5 * 100).toFixed(1)}%</strong>
                <p>Recall@5</p>
                <strong>{r.mrr_at_10.toFixed(3)}</strong>
                <p>MRR@10</p>
              </article>
            ))}
          </div>
          <p className="eval-note">
            Model: {result.embedding}. {result.note}
          </p>
          {result.results.map((r) => (
            <details key={r.mode}>
              <summary>{r.mode} — inspect errors and evidence</summary>
              {r.cases.map((c, i) => (
                <div className="eval-case-result" key={i}>
                  <strong>{c.question}</strong>
                  <p>
                    {c.latency_ms} ms ·{" "}
                    {c.retrieval_abstained
                      ? "Retrieval abstained"
                      : "Evidence retrieved"}{" "}
                    ·{" "}
                    {c.expected_unanswerable
                      ? "Expected unanswerable"
                      : "Recall: " + c.recall_at_5}
                  </p>
                  {c.sources.map((s) => (
                    <p key={s.id}>
                      {s.name} · page {s.page}: {s.text.slice(0, 180)}…
                    </p>
                  ))}
                </div>
              ))}
            </details>
          ))}
        </>
      )}
    </section>
  );
}
