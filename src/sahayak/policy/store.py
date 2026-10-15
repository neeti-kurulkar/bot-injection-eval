"""PolicyStore: Okapi BM25 over policy chunks (ADR-0002). Standard library only.

Chunks are the markdown sections of each document. The front-matter title and
keywords (which carry Hindi / Hinglish aliases) are indexed with every chunk
but not returned as text. A per-search overlay of extra documents supports the
poisoned-policy surface without mutating the base index.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

K1 = 1.5
B = 0.75
TOKEN = re.compile(r"[\wऀ-ॿ]+")
STOPWORDS = frozenset(
    "a an and are as at be by can for from has have how i if in is it its me my of on or our "
    "the their this to was what when which who why will with you your "
    "ka ki ke ko hai hain se me mein kya kab kaise aur "
    "का की के को है हैं से में क्या कब कैसे और".split()
)


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).lower()
    return [t for t in TOKEN.findall(text) if t not in STOPWORDS]


@dataclass(frozen=True)
class PolicyChunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    index_text: str


@dataclass(frozen=True)
class PolicyHit:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    score: float


def parse_policy(markdown: str, source: str = "") -> list[PolicyChunk]:
    """Split one policy document (front matter + markdown) into section chunks."""
    meta: dict[str, str] = {}
    body = markdown
    if markdown.startswith("---\n"):
        _, fm, body = markdown.split("---\n", 2)
        for line in fm.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    doc_id = meta.get("doc_id", source or "OVERLAY")
    title = meta.get("title", doc_id)
    keywords = meta.get("keywords", "")
    sections = [s for s in re.split(r"\n(?=## )", body) if s.strip()]
    chunks = []
    n = 0
    for sec in sections:
        sec = sec.strip()
        if sec.startswith("# ") and "\n" not in sec:
            continue  # bare title line
        if sec.startswith("# "):
            sec = sec.split("\n", 1)[1].strip()
        if sec.startswith("_Synthetic policy"):
            continue
        sec = sec.split("\n\n_Synthetic policy")[0].strip()
        n += 1
        chunks.append(PolicyChunk(f"{doc_id}#{n}", doc_id, title, sec, f"{title}\n{keywords}\n{sec}"))
    return chunks


class _Index:
    def __init__(self, chunks: list[PolicyChunk]):
        self.chunks = chunks
        self.tfs = [Counter(tokenize(c.index_text)) for c in chunks]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = (sum(self.lens) / len(self.lens)) if self.lens else 0.0
        df: Counter = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query: str, k: int) -> list[PolicyHit]:
        q = tokenize(query)
        scored = []
        for c, tf, dl in zip(self.chunks, self.tfs, self.lens):
            s = 0.0
            for t in q:
                f = tf.get(t, 0)
                if f:
                    s += self.idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / self.avgdl))
            if s > 0:
                scored.append((s, c))
        scored.sort(key=lambda x: (-x[0], x[1].chunk_id))
        return [PolicyHit(c.chunk_id, c.doc_id, c.title, c.text, round(s, 4)) for s, c in scored[:k]]


class PolicyStore:
    def __init__(self, chunks: list[PolicyChunk]):
        self._chunks = chunks
        self._index = _Index(chunks)

    @classmethod
    def from_dir(cls, policies_dir: Path) -> PolicyStore:
        chunks: list[PolicyChunk] = []
        for p in sorted(policies_dir.glob("*.md")):
            chunks.extend(parse_policy(p.read_text(encoding="utf-8"), p.stem))
        return cls(chunks)

    @classmethod
    def from_texts(cls, texts: list[str]) -> PolicyStore:
        chunks: list[PolicyChunk] = []
        for i, t in enumerate(texts):
            chunks.extend(parse_policy(t, f"DOC{i}"))
        return cls(chunks)

    def search(self, query: str, k: int = 3, overlay: tuple[str, ...] = ()) -> list[PolicyHit]:
        if not overlay:
            return self._index.search(query, k)
        extra: list[PolicyChunk] = []
        for i, t in enumerate(overlay):
            extra.extend(parse_policy(t, f"OVERLAY{i}"))
        return _Index(self._chunks + extra).search(query, k)
