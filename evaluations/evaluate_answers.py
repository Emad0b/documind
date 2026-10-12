"""Score manually reviewed exported answer cases; do not substitute LLM opinions for labels.
Input JSON: [{answer_correct: bool, citation_supported: bool, abstained: bool,
expected_unanswerable: bool}]. Unknown labels must be null, not guessed.
"""

import json, sys

rows = json.load(open(sys.argv[1], encoding="utf-8"))


def labeled_rate(key):
    labeled = [r[key] for r in rows if isinstance(r.get(key), bool)]
    return {
        "labeled": len(labeled),
        "rate": sum(labeled) / len(labeled) if labeled else None,
    }


tp = sum(
    r.get("abstained") is True and r.get("expected_unanswerable") is True for r in rows
)
predicted = sum(r.get("abstained") is True for r in rows)
expected = sum(r.get("expected_unanswerable") is True for r in rows)
print(
    json.dumps(
        {
            "answer_accuracy": labeled_rate("answer_correct"),
            "citation_correctness": labeled_rate("citation_supported"),
            "abstention_precision": tp / predicted if predicted else None,
            "abstention_recall": tp / expected if expected else None,
        },
        indent=2,
    )
)
