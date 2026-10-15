"""Scenario setup shared by all runs: injects a scenario's overlay (attacker-written ticket or
account note) into the per-scenario DB copy. Policy-document overlays are passed to the
PolicyStore per search and never written anywhere."""

from __future__ import annotations

from sahayak.mockbank.repo import Repository


def apply_overlay(repo: Repository, scenario: dict) -> dict:
    """Insert overlay tickets and notes. Returns the IDs created, for the run record."""
    overlay = scenario.get("overlay") or {}
    created = {"tickets": [], "notes": []}
    for i, t in enumerate(overlay.get("tickets", []), 1):
        tid = f"TKX{i:05d}"
        repo.conn.execute(
            "INSERT INTO tickets (ticket_id, customer_id, created_at, category, language, subject, body, status) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (tid, t["customer_id"], t["created_at"], t["category"], t["language"], t["subject"], t["body"], t["status"]))
        created["tickets"].append(tid)
    for i, n in enumerate(overlay.get("notes", []), 1):
        nid = f"NX{i:04d}"
        repo.conn.execute("INSERT INTO account_notes (note_id, account_id, author, created_at, body) VALUES (?,?,?,?,?)",
                          (nid, n["account_id"], n["author"], n["created_at"], n["body"]))
        created["notes"].append(nid)
    repo.conn.commit()
    return created


def policy_overlay(scenario: dict) -> tuple[str, ...]:
    return tuple((scenario.get("overlay") or {}).get("policy_docs", ()))
