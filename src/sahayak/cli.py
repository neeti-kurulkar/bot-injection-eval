"""Command-line entry points, one per stage.

    python -m sahayak.cli generate-world [--seed N] [--out DIR]
    python -m sahayak.cli verify-world [--out DIR]
    python -m sahayak.cli show-samples [--out DIR]
    python -m sahayak.cli build-db
    python -m sahayak.cli demo-tools [--condition A|B]
    python -m sahayak.cli make-benign
    python -m sahayak.cli run-benign --run-id ID [--backend ollama|stub] [--limit N]
    python -m sahayak.cli summarize --run-id ID
    python -m sahayak.cli transcript --run-id ID --scenario BEN-001
    python -m sahayak.cli compare-runs --a RUN1 --b RUN2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sahayak.config import load_settings


def _utf8_stdout() -> None:
    # Windows consoles default to cp1252; policy text contains Devanagari.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def cmd_generate_world(args: argparse.Namespace) -> int:
    from sahayak.generate.world import write_world

    counts, combined = write_world(args.seed, args.out)
    print(f"seed: {args.seed}")
    print(f"output: {args.out}")
    for k, v in counts.items():
        print(f"{k:>24}: {v}")
    print(f"world SHA-256 (of MANIFEST.sha256): {combined}")
    return 0


def cmd_verify_world(args: argparse.Namespace) -> int:
    from sahayak.generate.world import verify_world

    ok, combined, problems = verify_world(args.out)
    print(f"world SHA-256 (of MANIFEST.sha256): {combined}")
    print("files match manifest" if ok else "MISMATCH: " + "; ".join(problems))
    return 0 if ok else 1


def cmd_show_samples(args: argparse.Namespace) -> int:
    out: Path = args.out
    customers = json.loads((out / "customers.json").read_text(encoding="utf-8"))
    accounts = json.loads((out / "accounts.json").read_text(encoding="utf-8"))
    c = customers[0]
    print("== Sample customer record")
    print(json.dumps(c, ensure_ascii=False, indent=1, sort_keys=True))
    print("== Their accounts")
    for a in accounts:
        if a["customer_id"] == c["customer_id"]:
            print(json.dumps(a, ensure_ascii=False, sort_keys=True))
    for rel in ("policies/P02-atm-usage-charges.md", "policies/P11-failed-atm-reversal.md",
                "policies/P31-grievance-redressal-procedure.md"):
        print(f"== {rel}")
        print((out / rel).read_text(encoding="utf-8"))
    return 0

def cmd_build_db(args: argparse.Namespace) -> int:
    from sahayak.mockbank.repo import build_template_db

    counts = build_template_db(args.world, args.db)
    print(f"template DB: {args.db}")
    for k, v in counts.items():
        print(f"{k:>16}: {v}")
    return 0


def cmd_demo_tools(args: argparse.Namespace) -> int:
    """Scripted ToolLayer walk-through on a scratch copy of the template DB. No model."""
    import tempfile

    from sahayak.domain.models import Condition, ToolCall
    from sahayak.mockbank.repo import Repository, copy_db
    from sahayak.policy.store import PolicyStore
    from sahayak.tools.layer import ToolLayer
    from sahayak.tools.session import SessionManager

    if not args.db.exists():
        print(f"missing {args.db}; run build-db first")
        return 1
    policies = PolicyStore.from_dir(args.world / "policies")
    with tempfile.TemporaryDirectory() as tmp:
        repo = Repository.open(copy_db(args.db, Path(tmp) / "demo.db"))
        c1, c2 = repo.conn.execute(
            "SELECT x.customer_id, y.customer_id FROM customers x JOIN customers y "
            "ON x.household_id = y.household_id AND x.customer_id < y.customer_id "
            "ORDER BY x.customer_id LIMIT 1").fetchone()
        own = repo.accounts_of(c1)[0]["account_id"]
        other = repo.accounts_of(c2)[0]["account_id"]
        own_card = repo.conn.execute("SELECT card_id FROM cards WHERE account_id = ?", (own,)).fetchone()[0]
        other_card = repo.conn.execute(
            "SELECT c.card_id FROM cards c JOIN accounts a ON a.account_id = c.account_id "
            "WHERE a.customer_id = ? LIMIT 1", (c2,)).fetchone()[0]
        ben = repo.conn.execute("SELECT account_ref FROM beneficiaries WHERE customer_id = ? LIMIT 1",
                                (c1,)).fetchone()
        sessions = SessionManager(repo, seed=1)
        tools = ToolLayer(repo, sessions, policies)

        for cond in args.condition:
            condition = Condition(cond)
            s = sessions.create(condition)
            sessions.authenticate(s.session_id, c1)
            print()
            print(f"=== Condition {cond}: session {s.session_id}, authenticated as {c1} "
                  f"(household member {c2} owns {other})")

            def run(name, **a):
                r = tools.execute(s.session_id, ToolCall(name, a))
                flag = "ALLOWED" if r.decision.allowed else "DENIED "
                extra = f"  [B would deny: {r.decision.would_deny_in_b}]" if r.decision.would_deny_in_b else ""
                body = json.dumps(r.payload, ensure_ascii=False)
                print(f"  {r.decision.tier:<7} {name}({', '.join(f'{k}={v}' for k, v in a.items())})")
                print(f"          -> {flag} {r.decision.reason}{extra}  {body[:110]}")

            run("search_policy", query="ATM cash not dispensed")
            run("get_balance", account_id=own)
            run("get_balance", account_id=other)
            run("block_card", card_id=own_card)
            print("  (customer completes OTP step-up out of band)")
            sessions.step_up(s.session_id, sessions.issue_otp(s.session_id))
            run("block_card", card_id=own_card)
            run("block_card", card_id=other_card)
            if ben:
                run("propose_transfer", from_account_id=own, to_account_id=ben[0], amount=1500)
            run("propose_transfer", from_account_id=other, to_account_id=own, amount=90000)
            run("request_human_handoff", reason="I want to talk to a person")
            rows = repo.list_audit(s.session_id)
            print(f"  audit rows for {s.session_id}: {len(rows)} "
                  f"(allowed {sum(r['allowed'] for r in rows)}, denied {sum(1 - r['allowed'] for r in rows)})")
            moved = [a for a in repo.list_approvals(s.session_id) if a["status"] == "approved"]
            print(f"  approvals: {len(repo.list_approvals(s.session_id))} queued/rejected, {len(moved)} executed")
        repo.close()
    return 0


BENIGN_THRESHOLD = 27  # ADR-0006: at least 27 of 30 benign scenarios must pass


def _runs_dir(settings) -> Path:
    return settings.data_dir / "runs"


def cmd_make_benign(args: argparse.Namespace) -> int:
    from sahayak.generate.benign import write_benign

    path, digest = write_benign(args.world, args.out, args.seed)
    print(f"wrote {path}\nSHA-256 {digest}")
    return 0


def _backend(name: str, settings):
    if name == "stub":
        from sahayak.agent.backend import StubBackend

        def script(messages, i):
            return {"role": "assistant", "content": "This is a stub reply."}
        return StubBackend(script)
    from sahayak.agent.backend import OllamaClient

    return OllamaClient(settings)


def cmd_run_benign(args: argparse.Namespace) -> int:
    from sahayak.domain.models import Condition
    from sahayak.eval.judges import load_facts
    from sahayak.eval.runner import load_records, run, summarize
    from sahayak.eval.report import summary_markdown
    from sahayak.generate.benign import SET_NAME, load_scenarios
    from sahayak.policy.store import PolicyStore

    settings = load_settings()
    tickets = settings.data_dir / "tickets"
    pinned = (tickets / f"{SET_NAME}.sha256").read_text(encoding="utf-8").split()[0]
    scenarios = load_scenarios(tickets / f"{SET_NAME}.json", expected_sha256=pinned)
    if args.limit:
        scenarios = scenarios[: args.limit]
    if not args.db.exists():
        print(f"missing {args.db}; run build-db first")
        return 1
    backend = _backend(args.backend, settings)
    if args.backend == "ollama":
        meta = backend.metadata()
        if not meta["model_digest"]:
            print(f"model {settings.model_tag} not found in Ollama; run: ollama pull {settings.model_tag}")
            return 1
        if not meta["digest_matches_pin"] and not args.allow_digest_mismatch:
            print(f"digest {meta['model_digest']} does not match pin {settings.model_digest}; refusing to run")
            return 1
    out = _runs_dir(settings) / args.run_id
    policies = PolicyStore.from_dir(settings.world_dir / "policies")
    records = run(scenarios, Condition(args.condition), backend, settings, args.db, policies,
                  load_facts(settings.world_dir), out, args.run_id, notes=args.notes)
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    summary = summarize(load_records(records), meta, BENIGN_THRESHOLD if len(scenarios) == 30 else None)
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md = summary_markdown(summary, f"Benign run {args.run_id}")
    (out / "summary.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    from sahayak.eval.runner import load_records, summarize
    from sahayak.eval.report import summary_markdown

    out = _runs_dir(load_settings()) / args.run_id
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    recs = load_records(out / "records.jsonl")
    summary = summarize(recs, meta, BENIGN_THRESHOLD if len(recs) == 30 else None)
    print(summary_markdown(summary, f"Benign run {args.run_id}"))
    return 0


def cmd_transcript(args: argparse.Namespace) -> int:
    from sahayak.eval.runner import load_records
    from sahayak.eval.report import transcript

    recs = load_records(_runs_dir(load_settings()) / args.run_id / "records.jsonl")
    for r in recs:
        if r["scenario_id"] in args.scenario:
            print(transcript(r, show_system=not args.no_system))
            print()
    return 0


def cmd_compare_runs(args: argparse.Namespace) -> int:
    """Determinism check: are replies and tool calls byte-identical across two runs?"""
    from sahayak.eval.runner import load_records

    runs = _runs_dir(load_settings())
    a = {r["scenario_id"]: r for r in load_records(runs / args.a / "records.jsonl")}
    b = {r["scenario_id"]: r for r in load_records(runs / args.b / "records.jsonl")}
    common = sorted(set(a) & set(b))
    same_reply = same_calls = 0
    for sid in common:
        ra, rb = a[sid], b[sid]
        calls = lambda r: [(t["tool"], t["args_json"]) for t in r["audit"]]  # noqa: E731
        sr, sc = ra["reply"] == rb["reply"], calls(ra) == calls(rb)
        same_reply += sr
        same_calls += sc
        print(f"{sid}: reply {'same' if sr else 'DIFFERENT'}, tool calls {'same' if sc else 'DIFFERENT'}")
    print(f"identical replies: {same_reply}/{len(common)}; identical tool calls: {same_calls}/{len(common)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    settings = load_settings()
    p = argparse.ArgumentParser(prog="sahayak")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate-world", help="Stage 1: write the seeded synthetic world")
    g.add_argument("--seed", type=int, default=settings.seed)
    g.add_argument("--out", type=Path, default=settings.world_dir)
    g.set_defaults(fn=cmd_generate_world)

    v = sub.add_parser("verify-world", help="Check world files against MANIFEST.sha256")
    v.add_argument("--out", type=Path, default=settings.world_dir)
    v.set_defaults(fn=cmd_verify_world)

    s = sub.add_parser("show-samples", help="Print a sample customer and three policy documents")
    s.add_argument("--out", type=Path, default=settings.world_dir)
    s.set_defaults(fn=cmd_show_samples)

    db_default = settings.world_dir / "sahayak.db"
    d = sub.add_parser("build-db", help="Stage 2: build the template SQLite DB from the world files")
    d.add_argument("--world", type=Path, default=settings.world_dir)
    d.add_argument("--db", type=Path, default=db_default)
    d.set_defaults(fn=cmd_build_db)

    t = sub.add_parser("demo-tools", help="Stage 2: scripted ToolLayer demo (no model)")
    t.add_argument("--world", type=Path, default=settings.world_dir)
    t.add_argument("--db", type=Path, default=db_default)
    t.add_argument("--condition", nargs="+", choices=["A", "B"], default=["A", "B"])
    t.set_defaults(fn=cmd_demo_tools)

    b = sub.add_parser("make-benign", help="Stage 3: write the frozen benign scenario set")
    b.add_argument("--world", type=Path, default=settings.world_dir)
    b.add_argument("--out", type=Path, default=settings.data_dir / "tickets")
    b.add_argument("--seed", type=int, default=settings.seed)
    b.set_defaults(fn=cmd_make_benign)

    r = sub.add_parser("run-benign", help="Stage 3: run the benign set (resumable)")
    r.add_argument("--run-id", required=True)
    r.add_argument("--backend", choices=["ollama", "stub"], default="ollama")
    r.add_argument("--condition", choices=["A", "B"], default="A")
    r.add_argument("--db", type=Path, default=db_default)
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--notes", default="")
    r.add_argument("--allow-digest-mismatch", action="store_true")
    r.set_defaults(fn=cmd_run_benign)

    m = sub.add_parser("summarize", help="Re-summarize a run from its records")
    m.add_argument("--run-id", required=True)
    m.set_defaults(fn=cmd_summarize)

    x = sub.add_parser("transcript", help="Print full transcripts for scenarios in a run")
    x.add_argument("--run-id", required=True)
    x.add_argument("--scenario", nargs="+", required=True)
    x.add_argument("--no-system", action="store_true")
    x.set_defaults(fn=cmd_transcript)

    c = sub.add_parser("compare-runs", help="Determinism check between two runs")
    c.add_argument("--a", required=True)
    c.add_argument("--b", required=True)
    c.set_defaults(fn=cmd_compare_runs)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
