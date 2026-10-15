"""Command-line entry points, one per stage.

    python -m sahayak.cli generate-world [--seed N] [--out DIR]
    python -m sahayak.cli verify-world [--out DIR]
    python -m sahayak.cli show-samples [--out DIR]
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

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
