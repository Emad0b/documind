"""Self-authored synthetic facts. No external copyrighted papers or private files."""

import json
from pathlib import Path

root = Path(__file__).parent / "datasets"
root.mkdir(exist_ok=True)
documents = []
cases = []
topics = [
    "training cost",
    "batch size",
    "GPU count",
    "training duration",
    "parameter count",
    "dataset size",
    "learning rate",
    "context length",
    "energy use",
    "memory use",
    "evaluation score",
    "inference latency",
    "checkpoint count",
    "warmup steps",
    "dropout rate",
    "carbon footprint",
]
for index, name in enumerate(["Cedar", "Maple", "Willow", "Birch"]):
    pages = []
    for j, topic in enumerate(topics):
        value = (index + 1) * 100 + j + 1
        pages.append(
            f"{name} Experiment Report. Section: {topic}.\nThe {topic} for the {name} experiment was {value} benchmark units.\nThis is a fictional self-authored benchmark, not an actual research result."
        )
        cases.append(
            {
                "question": f"What {topic} did the {name} experiment report?",
                "documents": [name],
                "expected": [{"document": name, "page": j + 1}],
                "reference_answer": str(value),
                "category": "factual",
            }
        )
    documents.append({"name": name, "pages": pages})
for index in range(8):
    cases.append(
        {
            "question": [
                "Who won the national football championship?",
                "What is the mayor’s home address?",
                "Which restaurant has the cheapest lunch?",
                "What is tomorrow’s weather forecast?",
                "Who composed the opera?",
                "What is the mountain hiking permit price?",
                "Which ocean fish lives longest?",
                "What is the train departure platform?",
            ][index],
            "documents": ["Cedar", "Maple"],
            "expected": [],
            "reference_answer": None,
            "category": "unanswerable",
        }
    )
cases.append(
    {
        "question": "Compare the reported training cost of Cedar and Maple.",
        "documents": ["Cedar", "Maple"],
        "expected": [
            {"document": "Cedar", "page": 1},
            {"document": "Maple", "page": 1},
        ],
        "reference_answer": "101 versus 201 benchmark units",
        "category": "comparison",
    }
)
cases.append(
    {
        "question": "Which experiment is better?",
        "documents": ["Cedar", "Maple"],
        "expected": [],
        "reference_answer": None,
        "category": "ambiguous",
    }
)
(root / "synthetic.json").write_text(
    json.dumps(
        {
            "description": "74 self-authored synthetic cases: 64 factual, 8 unrelated, 1 comparison, 1 ambiguous. Smoke benchmark, not real-paper validation.",
            "documents": documents,
            "cases": cases,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print("Created", len(cases), "cases")
