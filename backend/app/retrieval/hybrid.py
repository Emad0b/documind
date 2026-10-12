import json, math
from collections import Counter
from ..core.database import db, sql, PG
from ..core.config import RRF_K, MIN_SIMILARITY
from ..ingestion.chunker import tokens
from ..ingestion.embeddings import encode, model_id

STOPWORDS = set(
    "a an the is are was were be been being what which who where when how why did do does of for to in on at with and or this that these those it its as by from reported report experiment experiments units benchmark".split()
)


def fuse(rankings, k=RRF_K):
    scores = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            scores[item] = scores.get(item, 0) + 1 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True), scores


def retrieve(question, ids, owner, limit=5, mode="hybrid"):
    qv = encode([question])[0]
    model = model_id()
    args = [owner, *ids, model]
    where = (
        "d.owner=? AND c.doc IN ("
        + ",".join("?" for _ in ids)
        + ") AND c.model=? AND d.status='ready'"
    )
    select = (
        "SELECT c.id,c.doc,c.page,c.text,d.name,c.embedding FROM chunks c JOIN documents d ON d.id=c.doc WHERE "
        + where
    )
    with db() as conn:
        if PG:
            vr = sql(
                conn,
                select + " ORDER BY c.embedding <=> ?::vector LIMIT 30",
                (*args, json.dumps(qv)),
            ).fetchall()
            kr = sql(
                conn,
                select
                + " AND c.search @@ websearch_to_tsquery('english',?) ORDER BY ts_rank_cd(c.search,websearch_to_tsquery('english',?)) DESC LIMIT 30",
                (*args, question, question),
            ).fetchall()
            rows = {r[0]: r for r in [*vr, *kr]}
            dense = []
            similarity = {}
            for r in vr:
                value = sum(a * b for a, b in zip(qv, json.loads(str(r[5]))))
                similarity[r[0]] = value
                if value >= MIN_SIMILARITY:
                    dense.append(r[0])
            lexical = [r[0] for r in kr]
        else:
            allrows = sql(conn, select, args).fetchall()
            rows = {r[0]: r for r in allrows}
            query = set(tokens(question)) - STOPWORDS
            df = Counter(t for r in allrows for t in set(tokens(r[3])))
            avg = sum(len(tokens(r[3])) for r in allrows) / max(1, len(allrows))
            lex = []
            vec = []
            similarity = {}
            for r in allrows:
                ts = tokens(r[3])
                counts = Counter(ts)
                bm = sum(
                    math.log(1 + (len(allrows) - df[t] + 0.5) / (df[t] + 0.5))
                    * counts[t]
                    * 2.2
                    / (counts[t] + 1.2 * (0.25 + 0.75 * len(ts) / max(avg, 1)))
                    for t in query
                    if counts[t]
                )
                sim = sum(a * b for a, b in zip(qv, json.loads(r[5])))
                similarity[r[0]] = sim
                if bm > 0:
                    lex.append((bm, r[0]))
                if sim >= MIN_SIMILARITY:
                    vec.append((sim, r[0]))
            lexical = [cid for _, cid in sorted(lex, reverse=True)[:30]]
            dense = [cid for _, cid in sorted(vec, reverse=True)[:30]]
    ranking, scores = fuse(
        [dense]
        if mode == "vector"
        else [lexical]
        if mode == "keyword"
        else [dense, lexical]
    )
    return [
        dict(
            id=cid,
            document_id=rows[cid][1],
            page=rows[cid][2],
            text=rows[cid][3],
            name=rows[cid][4],
            score=scores[cid],
            similarity=similarity.get(cid, 0),
        )
        for cid in ranking[:limit]
    ]
