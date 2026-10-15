"""BM25 PolicyStore (ADR-0002). No model needed."""

from __future__ import annotations

import pytest

from sahayak.policy.store import PolicyStore, tokenize
from tests.conftest import corpus_store


def test_tokenizer_keeps_devanagari_words_whole():
    assert tokenize("एटीएम से पैसे नहीं निकले") == ["एटीएम", "पैसे", "नहीं", "निकले"]


@pytest.mark.parametrize("query, doc", [
    ("ATM cash not dispensed refund", "P11"),
    ("एटीएम से पैसे नहीं निकले", "P11"),
    ("card block karo", "P25"),
    ("complaint to RBI ombudsman", "P31"),
    ("branch timing saturday", "P36"),
    ("shikayat helpline number", "P32"),
])
def test_top_hit_per_language(query, doc):
    assert corpus_store().search(query, k=1)[0].doc_id == doc


def test_vague_romanized_complaint_query_known_limitation():
    # "shikayat" is tagged on every dispute and grievance doc, so a vague romanized query ranks
    # the complaints doc second, not first. Recorded as a retrieval limitation (Stage 1/2 gate).
    hits = [h.doc_id for h in corpus_store().search("shikayat kaise karein", k=3)]
    assert "P32" in hits


def test_results_are_deterministic_and_exclude_front_matter():
    a = corpus_store().search("debit card annual fee", k=3)
    b = corpus_store().search("debit card annual fee", k=3)
    assert a == b
    assert all("keywords:" not in h.text and "_Synthetic policy" not in h.text for h in a)


def test_overlay_is_per_search_only():
    store = corpus_store()
    overlay = ("---\ndoc_id: X1\ntitle: Zebra notice\nkeywords: zebra\n---\n# Zebra notice\n\n## Zebra\nzebra zebra",)
    assert store.search("zebra", k=1, overlay=overlay)[0].doc_id == "X1"
    assert store.search("zebra", k=1) == []


def test_from_texts_handles_no_front_matter():
    store = PolicyStore.from_texts(["# Plain\n\n## Section\nrefund rules here"])
    assert store.search("refund", k=1)[0].doc_id == "DOC0"
