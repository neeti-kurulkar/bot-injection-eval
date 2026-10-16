"""Stage 7 final checks (spec §6 Stage 7): no real data, no runnable attack catalogue outside data/attacks,
no hosted-API keys or endpoints, and no 'secure' / 'resistant' / 'protected' / 'compliant' claims."""

from __future__ import annotations

import json
import re
import subprocess

import pytest

from sahayak.config import REPO_ROOT

OVERCLAIM = re.compile(r"\b(secure|resistant|protected|compliant)\b", re.I)
NEGATION = re.compile(r"\b(not|neither|never|no|nothing|nor)\b", re.I)
KEY_PATTERNS = (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), re.compile(r"AKIA[0-9A-Z]{16}"), re.compile(r"ghp_[A-Za-z0-9]{30,}"),
                re.compile(r"(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", re.I))
HOSTED = re.compile(r"api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis|api\.groq\.com|"
                    r"api\.together\.|api\.mistral\.ai|api\.sarvam\.ai", re.I)
# ADR-0013: the one module allowed to name hosted endpoints (comparison study only).
HOSTED_ALLOWLIST = ("src/sahayak/agent/hosted.py",)
EMAIL = re.compile(r"[\w.+-]+@([\w-]+\.)+[\w-]+")
ALLOWED_EMAIL_DOMAINS = ("example.invalid", "sahayak.example", "anthropic.com")


def tracked(*suffixes: str) -> list:
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True).stdout.split()
    extra = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=REPO_ROOT,
                           capture_output=True, text=True).stdout.split()
    return [REPO_ROOT / p for p in out + extra if p.endswith(suffixes) and (REPO_ROOT / p).exists()]


def test_no_overclaiming_words_except_in_negations():
    offenders = []
    for path in tracked(".md", ".py", ".ps1"):
        if "data/attacks" in path.as_posix() or path.name == "test_repo_hygiene.py":
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if OVERCLAIM.search(line) and not NEGATION.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{i}: {line.strip()[:100]}")
    assert not offenders, "\n".join(offenders)


def test_no_attack_payload_text_outside_data_attacks():
    items = json.loads((REPO_ROOT / "data" / "attacks" / "dev" / "items.json").read_text(encoding="utf-8"))
    snippets = set()
    for d in items:
        if d["kind"] != "attack":
            continue
        # The payload is the message only on the message surface; elsewhere the message is a benign trigger.
        bodies = ([d["message"]] if d["surface"] == "message" else []) + \
                 [x["body"] for x in d["overlay"]["tickets"] + d["overlay"]["notes"]]
        for b in bodies:
            first = b.splitlines()[0].strip()
            if len(first) >= 40:
                snippets.add(first[:40])
    docs = [p for p in tracked(".md", ".py", ".ps1", ".json") if "data/" not in p.relative_to(REPO_ROOT).as_posix()]
    found = [(p.name, s) for p in docs for s in snippets if s in p.read_text(encoding="utf-8", errors="ignore")]
    assert not found, found[:5]


def test_no_api_keys_or_hosted_endpoints():
    for path in tracked(".py", ".ps1", ".md", ".json", ".toml"):
        if path.name == "test_repo_hygiene.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # The held-out gate phrase is a documented approval string (README), not a credential.
        text = text.replace('HELDOUT_TOKEN = "stage5-heldout-gate-approved"', "")
        assert not any(p.search(text) for p in KEY_PATTERNS), path
        rel = path.relative_to(REPO_ROOT).as_posix()
        if path.suffix in (".py", ".ps1", ".toml") and rel not in HOSTED_ALLOWLIST:
            assert not HOSTED.search(text), path


def test_hosted_endpoints_only_in_the_allowlisted_module():
    hits = [p.relative_to(REPO_ROOT).as_posix() for p in tracked(".py")
            if p.name != "test_repo_hygiene.py" and HOSTED.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert hits == list(HOSTED_ALLOWLIST), hits


@pytest.mark.parametrize("folder", ["data/world", "data/tickets", "docs"])
def test_only_synthetic_email_domains(folder):
    for path in (REPO_ROOT / folder).rglob("*"):
        if path.is_file() and path.suffix in (".json", ".md", ".csv"):
            for m in EMAIL.finditer(path.read_text(encoding="utf-8", errors="ignore")):
                assert m.group(0).lower().endswith(ALLOWED_EMAIL_DOMAINS), (path, m.group(0))


def test_world_phone_numbers_are_synthetic():
    customers = json.loads((REPO_ROOT / "data" / "world" / "customers.json").read_text(encoding="utf-8"))
    assert all(c["phone"].startswith("+91-00000-") for c in customers)
