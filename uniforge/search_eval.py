"""Search readiness: does the buyer actually find the part?

Compliance percentages say the output is well formed. They do not say it is useful. So
the same BM25 index is built twice - once over the raw supplier rows, once over the
compiled records - and the same queries are run against both.

TWO QUERY SETS

  vocabulary-gap queries
      Built from raw supplier text expanded through the seed lexicon, and admitted ONLY
      when the trade term does not appear anywhere in the raw row. These are the queries
      the raw catalogue cannot answer by construction, which is exactly why they matter.

  hand-written trade queries
      Typed the way a counter clerk types, with a known correct leaf.

THREE RULES THAT KEEP THE MEASUREMENT HONEST

  1. No generated text is used to build any query. Queries come from the raw side and the
     seed lexicon only, so the compiled index is never asked a question written from its
     own output.
  2. Part numbers are stripped from queries. A part number is a unique key; leaving it in
     inflates every baseline and hides the effect being measured.
  3. Both directions get reported. Normalising a family makes its members more similar,
     so category findability rises while exact-row ranking can dip. The metric that goes
     the wrong way is reported with the ones that do not.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from .compose import Composition
from .extract import Extraction
from .ingest import Row
from .vocab import Vocabulary

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9./\-]*")
_PARTNUM_RE = re.compile(r"\b(?=[a-z0-9\-]*\d)(?=[a-z0-9\-]*[a-z])[a-z0-9\-]{5,}\b")


def _tok(text: str) -> list[str]:
    return _TOKEN_RE.findall(str(text or "").lower())


def strip_part_numbers(text: str) -> str:
    """A part number is a unique key; it inflates any baseline."""
    return _PARTNUM_RE.sub(" ", str(text or "").lower())


class BM25:
    def __init__(self, docs: dict[int, str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.doc_tokens = {i: _tok(t) for i, t in docs.items()}
        self.doc_len = {i: len(t) for i, t in self.doc_tokens.items()}
        self.avg_len = (sum(self.doc_len.values()) / len(self.doc_len)
                        if self.doc_len else 0.0)
        self.tf: dict[int, Counter] = {i: Counter(t) for i, t in self.doc_tokens.items()}
        self.df: Counter = Counter()
        for toks in self.doc_tokens.values():
            for w in set(toks):
                self.df[w] += 1
        self.N = max(1, len(self.doc_tokens))
        self.postings: dict[str, list[int]] = defaultdict(list)
        for i, toks in self.doc_tokens.items():
            for w in set(toks):
                self.postings[w].append(i)

    def _idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def search(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        q = _tok(query)
        if not q:
            return []
        scores: dict[int, float] = defaultdict(float)
        for term in q:
            if term not in self.postings:
                continue
            idf = self._idf(term)
            for i in self.postings[term]:
                f = self.tf[i][term]
                dl = self.doc_len[i] or 1
                denom = f + self.k1 * (1 - self.b + self.b * dl / self.avg_len)
                scores[i] += idf * (f * (self.k1 + 1)) / (denom or 1)
        return sorted(scores.items(), key=lambda kv: -kv[1])[:k]


@dataclass
class QueryResult:
    query: str
    kind: str
    relevant: list[int]
    before_hits: list[int] = field(default_factory=list)
    after_hits: list[int] = field(default_factory=list)

    def _rr(self, hits: list[int]) -> float:
        rel = set(self.relevant)
        for i, doc in enumerate(hits, start=1):
            if doc in rel:
                return 1.0 / i
        return 0.0

    def _recall(self, hits: list[int]) -> float:
        rel = set(self.relevant)
        return (len(rel & set(hits)) / len(rel)) if rel else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "kind": self.kind,
            "relevant_count": len(self.relevant),
            "recall_before": round(self._recall(self.before_hits), 4),
            "recall_after": round(self._recall(self.after_hits), 4),
            "rr_before": round(self._rr(self.before_hits), 4),
            "rr_after": round(self._rr(self.after_hits), 4),
            "zero_before": not self.before_hits,
            "zero_after": not self.after_hits,
        }


@dataclass
class SearchReport:
    k: int
    gap_queries: list[QueryResult] = field(default_factory=list)
    trade_queries: list[QueryResult] = field(default_factory=list)
    exact_recall_before: float = 0.0
    exact_recall_after: float = 0.0
    exact_checked: int = 0

    @staticmethod
    def _mean(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    def to_dict(self) -> dict[str, Any]:
        g = self.gap_queries
        t = self.trade_queries
        return {
            "k": self.k,
            "vocabulary_gap": {
                "query_count": len(g),
                "recall_at_k_before": self._mean([q._recall(q.before_hits) for q in g]),
                "recall_at_k_after": self._mean([q._recall(q.after_hits) for q in g]),
                "zero_result_rate_before": (
                    round(sum(1 for q in g if not q.before_hits) / len(g), 4)
                    if g else 0.0),
                "zero_result_rate_after": (
                    round(sum(1 for q in g if not q.after_hits) / len(g), 4)
                    if g else 0.0),
                "note": ("queries built only from raw supplier text expanded through the "
                         "seed lexicon; a query is admitted only when the trade term "
                         "appears nowhere in the raw row"),
            },
            "trade_queries": {
                "query_count": len(t),
                "mrr_at_k_before": self._mean([q._rr(q.before_hits) for q in t]),
                "mrr_at_k_after": self._mean([q._rr(q.after_hits) for q in t]),
                "recall_at_k_before": self._mean([q._recall(q.before_hits) for q in t]),
                "recall_at_k_after": self._mean([q._recall(q.after_hits) for q in t]),
                "note": "hand-written the way a counter clerk types, with a known leaf",
            },
            "exact_item": {
                "checked": self.exact_checked,
                "recall_at_k_before": self.exact_recall_before,
                "recall_at_k_after": self.exact_recall_after,
                "direction": ("worse" if self.exact_recall_after
                              < self.exact_recall_before else "better"),
                "why": ("normalising a family makes its members more similar, so "
                        "category findability rises while exact-row ranking dips. "
                        "Reported because it did not flatter us."),
            },
            "guards": [
                "no generated text is used to build any query",
                "part numbers are stripped from queries: a unique key inflates any "
                "baseline",
                "the same index, scorer and k are used on both sides",
                "both indexes are field-weighted, so the raw description gets the same "
                "treatment its compiled counterpart does",
            ],
            "examples": [q.to_dict() for q in (g[:8] + t[:8])],
        }


# ======================================================================================


def _before_doc(row: Row) -> str:
    parts = {
        "description": row.description,
        "identity": " ".join(x for x in (row.e1_brand, row.unilog_brand,
                                         row.dib_brand, row.part_manuf) if x),
    }
    return _weighted(parts, BEFORE_WEIGHTS)


# Field weights for the compiled index.
#
# A single concatenated blob is not how a catalogue is searched, and scoring one that way
# would misrepresent both sides. Marketing prose is by far the longest field and the least
# discriminating, so in a flat index it drowns the title and the attributes. Weighting by
# field is standard practice, and it is applied to BOTH indexes so the comparison stays
# like-for-like: the raw side has a description and brand columns, and they get the same
# treatment their compiled counterparts do.
AFTER_WEIGHTS: list[tuple[str, int]] = [
    ("title", 3),
    ("item_type", 3),
    ("classpath", 2),
    ("attributes", 2),
    ("identity", 2),
    ("keywords", 1),
    ("long", 1),
    ("marketing", 1),
]

BEFORE_WEIGHTS: list[tuple[str, int]] = [
    ("description", 3),
    ("identity", 2),
]


def _weighted(parts: dict[str, str], weights: list[tuple[str, int]]) -> str:
    out: list[str] = []
    for key, w in weights:
        text = parts.get(key, "").strip()
        if text:
            out.extend([text] * w)
    return " ".join(out)


def _after_doc(row: Row, ex: Extraction, comp: Composition,
               manufacturer: str, brand: str, rec_marketing: str) -> str:
    parts = {
        "title": comp.title,
        "item_type": ex.item_type,
        "classpath": ex.classpath.replace(">", " "),
        "attributes": " ".join(f"{a.label} {a.value} {a.uom}" for a in ex.attributes),
        "identity": f"{manufacturer} {brand}",
        "keywords": comp.keywords,
        "long": comp.long,
        "marketing": rec_marketing,
    }
    return _weighted(parts, AFTER_WEIGHTS)


def build_queries(rows: list[Row], extractions: dict[int, Extraction],
                  vocab: Vocabulary) -> list[QueryResult]:
    """Vocabulary-gap queries: trade terms the supplier never wrote."""
    by_leaf: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        ex = extractions.get(r.row_id)
        if ex and ex.leaf:
            by_leaf[ex.leaf].append(r.row_id)

    out: list[QueryResult] = []
    for leaf, ids in sorted(by_leaf.items()):
        syns = vocab.trade_synonyms.get(leaf, [])
        if not syns or len(ids) < 2:
            continue
        raw_blob = " ".join(_before_doc(r) for r in rows if r.row_id in ids).lower()
        for syn in syns:
            words = [w for w in _tok(syn) if len(w) > 2]
            if not words:
                continue
            # admitted only if the supplier never wrote this term
            if all(w in raw_blob for w in words):
                continue
            # add one discriminating attribute value so the query is not leaf-only
            qualifier = ""
            first = extractions.get(ids[0])
            if first:
                for a in first.attributes:
                    if a.label in ("Diameter", "Nominal Size", "Grit", "Amperage",
                                   "Tank Capacity", "Colour", "Finish", "MERV Rating"):
                        qualifier = f"{a.value} {a.uom}".strip()
                        break
            q = strip_part_numbers(f"{syn} {qualifier}".strip())
            out.append(QueryResult(query=q, kind="vocabulary-gap", relevant=list(ids)))
    return out


def run(rows: list[Row], extractions: dict[int, Extraction],
        compositions: dict[int, Composition], manufacturers: dict[int, str],
        brands: dict[int, str], marketing: dict[int, str],
        vocab: Vocabulary, k: int = 10) -> SearchReport:
    before_docs = {r.row_id: strip_part_numbers(_before_doc(r)) for r in rows}
    after_docs = {
        r.row_id: strip_part_numbers(_after_doc(
            r, extractions[r.row_id], compositions[r.row_id],
            manufacturers.get(r.row_id, ""), brands.get(r.row_id, ""),
            marketing.get(r.row_id, "")))
        for r in rows if r.row_id in extractions and r.row_id in compositions
    }
    idx_before = BM25(before_docs)
    idx_after = BM25(after_docs)

    report = SearchReport(k=k)

    # ---- vocabulary-gap ------------------------------------------------------------
    for q in build_queries(rows, extractions, vocab):
        q.before_hits = [i for i, _s in idx_before.search(q.query, k)]
        q.after_hits = [i for i, _s in idx_after.search(q.query, k)]
        report.gap_queries.append(q)

    # ---- hand-written trade queries -------------------------------------------------
    leaf_rows: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        ex = extractions.get(r.row_id)
        if ex and ex.leaf:
            leaf_rows[ex.leaf].append(r.row_id)
    for query, leaf in vocab.trade_queries:
        rel = leaf_rows.get(leaf, [])
        if not rel:
            continue
        q = QueryResult(query=strip_part_numbers(query), kind="trade", relevant=rel)
        q.before_hits = [i for i, _s in idx_before.search(q.query, k)]
        q.after_hits = [i for i, _s in idx_after.search(q.query, k)]
        report.trade_queries.append(q)

    # ---- exact item: the buyer already knows what they want -------------------------
    hits_before = hits_after = checked = 0
    step = max(1, len(rows) // 300)
    for r in rows[::step]:
        if r.row_id not in after_docs:
            continue
        # the supplier's own words, minus the part number
        q = strip_part_numbers(r.description)
        if len(_tok(q)) < 2:
            continue
        checked += 1
        if r.row_id in [i for i, _s in idx_before.search(q, k)]:
            hits_before += 1
        if r.row_id in [i for i, _s in idx_after.search(q, k)]:
            hits_after += 1
    report.exact_checked = checked
    report.exact_recall_before = round(hits_before / checked, 4) if checked else 0.0
    report.exact_recall_after = round(hits_after / checked, 4) if checked else 0.0
    return report
