# Evaluation and error analysis

The checked-in dataset contains 74 self-authored synthetic cases: 64 direct factual questions, eight unrelated questions, one cross-document comparison, and one ambiguous question. Four fictional experiment reports each contain 16 pages. Reference evidence is labeled as a document/page pair, preventing page-number collisions between documents.

Run the same corpus through vector-only, keyword-only, and hybrid retrieval. Recall@5 measures relevant page coverage; MRR@10 measures the first relevant hit. Unanswerable cases are excluded from those denominators. Abstention precision/recall score retrieval returning no evidence, not an LLM's final decision. Latencies include query embedding and retrieval, exclude ingestion/model download, and use nearest-rank positions in the sorted observations.

## Actual local run

`results-semantic.json` records the measured Sentence Transformers all-MiniLM-L6-v2 run on the SQLite profile. All three baselines reached Recall@5 1.0 and MRR@10 1.0 on this deliberately simple dataset. Hybrid retrieval had abstention precision 1.0 and recall 0.889, with p50 10.43 ms and p95 16.77 ms. These figures are smoke-test results, not general accuracy claims or PostgreSQL benchmarks.

The first run is retained in `results-before-keyword-fix.json`. Hybrid abstention recall was only 0.111 because SQLite BM25 ranked common words in irrelevant documents. Removing common query terms increased it to 0.889 on the unchanged corpus. One ambiguous question still retrieves plausible passages even though evidence cannot establish an answer. The generation prompt must refuse unsupported conclusions; that behavior requires a configured provider and separate answer-level evaluation.

## What remains unmeasured

- Accuracy and citation entailment on real research papers.
- Real-provider prompt-injection resistance and final-answer abstention.
- PostgreSQL latency and concurrent-load performance.
- Cost per generated question without configured provider pricing.

Use `evaluate_answers.py` with manually reviewed labels to measure answer correctness and citation support. Unknown labels must remain null. Do not convert exact quote validation into a claim of hallucination detection.

## Reproduce

From `backend`, run:

```sh
python ../evaluations/create_dataset.py
python ../evaluations/evaluate_retrieval.py --semantic
```

For the lightweight lexical development profile, omit `--semantic`; it is not a semantic baseline. The benchmark creates isolated temporary storage and never uses an existing user's uploads. Extend the corpus with openly licensed papers, paraphrased questions, exact technical identifiers, contradictory evidence, numerical comparisons, and malicious document text before drawing conclusions about production performance.
