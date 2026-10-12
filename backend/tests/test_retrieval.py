from app.ingestion.chunker import split_page
from app.retrieval.hybrid import fuse


def test_chunk_boundary_overlap():
    chunks = split_page(" ".join(str(i) for i in range(400)), 180, 35)
    assert chunks[0].split()[-35:] == chunks[1].split()[:35]
    assert chunks[-1].split()[-1] == "399"


def test_rrf_favors_evidence_found_by_both_searches():
    ranking, scores = fuse([["a", "b", "c"], ["b", "d", "a"]])
    assert ranking[0] == "b"
    assert scores["b"] > scores["d"]
