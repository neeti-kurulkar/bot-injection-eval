"""Stage 4: attack and benign look-alike suite (authored once, frozen, split by family).

Procedure (ADR-0011):
  1. Templates are authored once in an external pool file (all families and look-alikes).
  2. `freeze_suite` splits whole attack families (and look-alike templates) into DEVELOPMENT
     and HELD-OUT with a seeded RNG, fills placeholders with IDs from the synthetic world,
     and writes:
       data/attacks/dev/templates.json, data/attacks/dev/items.json   (readable)
       data/attacks/heldout/heldout.sealed                            (gzip+base64, sealed)
       data/splits/attack_split_v1.json (+ .sha256)                   (held-out shown by opaque id)
       data/attacks/stats.json                                        (counts only)
  3. The pool file is then deleted. Held-out text exists only inside the sealed file.
The split is never regenerated: `freeze_suite` refuses to overwrite an existing manifest.

Development code reads only `load_dev_items`. `load_heldout_items` requires the explicit
gate-approval environment variable set for the Stage 5 held-out run.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import random
import re
from collections import Counter
from pathlib import Path

from sahayak.domain.models import LANGUAGES

SPLIT_NAME = "attack_split_v1"
GOALS = ("G1_fabricated_policy", "G2_cross_customer_leak", "G3_handoff_blocking",
         "G4_unauthorized_T2", "G5_unauthorized_T3")
SURFACES = ("message", "ticket", "note", "policy")
HELDOUT_FAMILIES = 3
HELDOUT_LOOKALIKE_SHARE = 0.5
HELDOUT_ENV = "SAHAYAK_HELDOUT_APPROVED"
HELDOUT_TOKEN = "stage5-heldout-gate-approved"
SEALED_HEADER = b"SAHAYAK-SEALED-HELDOUT v1. Do not decode outside the gate-approved held-out run.\n"
OVERLAY_TS = "2026-09-30T18:00:00"

PLACEHOLDER = re.compile(r"\{(target_card|target_account|other_account|other_name|attacker_account|"
                         r"attacker_phone|amount|own_card|own_ticket|own_txn|own_account|new_email)\}")
ZWSP = "​"
HOMOGLYPHS = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с"}  # Cyrillic


# ------------------------------------------------------------------ helpers
def fill(text: str, values: dict) -> str:
    """Replace only known placeholders, so JSON braces in payloads are left alone."""
    return PLACEHOLDER.sub(lambda m: str(values[m.group(1)]), text)


def obfuscate(text: str, rng: random.Random) -> str:
    """Zero-width spaces inside longer words, plus Latin->Cyrillic homoglyphs.
    Placeholders, numbers, and IDs are left intact so the payload stays actionable."""
    out = []
    for part in re.split(r"(\{[a-z_]+\}|\S+)", text):
        if not part or part.isspace() or PLACEHOLDER.fullmatch(part) or re.search(r"\d", part):
            out.append(part)
            continue
        chars = []
        for i, ch in enumerate(part):
            if ch.lower() in HOMOGLYPHS and ch.islower() and rng.random() < 0.35:
                ch = HOMOGLYPHS[ch]
            chars.append(ch)
            if len(part) >= 5 and i % 3 == 2 and i < len(part) - 1 and rng.random() < 0.6:
                chars.append(ZWSP)
        out.append("".join(chars))
    return "".join(out)


def policy_overlay_doc(doc_id: str, title: str, keywords: list[str], body: str) -> str:
    return (f"---\ndoc_id: {doc_id}\nslug: update\ncategory: general\ntitle: {title}\n"
            f"keywords: {', '.join(keywords)}\neffective_date: 2026-09-30\n---\n# {title}\n\n## Update\n{body}\n")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")


def seal(obj) -> bytes:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return SEALED_HEADER + base64.b64encode(gzip.compress(raw, mtime=0)) + b"\n"


def unseal(data: bytes):
    assert data.startswith(SEALED_HEADER), "not a sealed held-out file"
    return json.loads(gzip.decompress(base64.b64decode(data[len(SEALED_HEADER):].strip())).decode("utf-8"))


# ---------------------------------------------------------------- world view
class _World:
    def __init__(self, world_dir: Path):
        load = lambda n: json.loads((world_dir / n).read_text(encoding="utf-8"))  # noqa: E731
        self.customers = {c["customer_id"]: c for c in load("customers.json")}
        self.accounts = load("accounts.json")
        self.cards = load("cards.json")
        self.tickets = load("tickets.json")
        self.facts = load("policy_facts.json")
        self.acc_of: dict[str, list[str]] = {}
        for a in self.accounts:
            self.acc_of.setdefault(a["customer_id"], []).append(a["account_id"])
        owner = {a["account_id"]: a["customer_id"] for a in self.accounts}
        self.card_of: dict[str, list[str]] = {}
        for c in self.cards:
            if c["status"] == "active":
                self.card_of.setdefault(owner[c["account_id"]], []).append(c["card_id"])
        self.tickets_of: dict[str, list[str]] = {}
        for t in self.tickets:
            self.tickets_of.setdefault(t["customer_id"], []).append(t["ticket_id"])
        households: dict[str, list[str]] = {}
        for cid, c in sorted(self.customers.items()):
            households.setdefault(c["household_id"], []).append(cid)
        # (session customer, other household member) pairs where both have an account and an active card
        self.pairs = sorted((a, b) for members in households.values() for a in members for b in members
                            if a != b and a in self.card_of and b in self.card_of)
        self.household = {cid: c["household_id"] for cid, c in self.customers.items()}
        import csv
        self.last_debit: dict[str, str] = {}  # account -> latest posted card/UPI debit (file is time-ordered)
        with (world_dir / "transactions.csv").open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if r["direction"] == "debit" and r["status"] == "posted" and r["txn_type"] in ("card_pos", "upi_out"):
                    self.last_debit[r["account_id"]] = r["txn_id"]

    def actors(self, rng: random.Random, surface: str) -> dict:
        session, other = rng.choice(self.pairs)
        outsiders = [c for c in sorted(self.acc_of) if self.household[c] != self.household[session]]
        attacker = rng.choice(outsiders)
        # Message surface: the session user is the attacker and targets the household member.
        # Other surfaces: the session user is the victim; injected text targets the victim's own
        # resources (unrequested T2/T3) or exposes the household member's data (G2).
        target_owner = other if surface == "message" else session
        return {
            "session": session, "other": other, "attacker": attacker, "target_owner": target_owner,
            "values": {
                "target_card": rng.choice(self.card_of[target_owner]),
                "target_account": self.acc_of[target_owner][0],
                "other_account": self.acc_of[other][0],
                "other_name": self.customers[other]["display_name"],
                "attacker_account": rng.choice(self.acc_of[attacker]),
                "attacker_phone": f"+91-00000-9{rng.randint(1000, 9999)}",
                "amount": rng.choice((15000, 25000, 40000, 75000)),
            },
        }


# -------------------------------------------------------------- item builders
def _attack_items(family: dict, world: _World, pool: dict, rng: random.Random) -> list[dict]:
    items = []
    for goal, tpl in sorted(family["goals"].items()):
        for surface in SURFACES:
            if goal == "G3_handoff_blocking" and surface == "message":
                continue  # a customer cannot meaningfully block their own handoff
            for lang in LANGUAGES:
                a = world.actors(rng, surface)
                payload_tpl = tpl["payload"][lang]
                if family.get("transform") == "obfuscate":
                    payload_tpl = obfuscate(payload_tpl, rng)
                payload = fill(payload_tpl, a["values"])
                trigger = (pool["triggers"]["G1"][tpl["topic"]][lang] if goal.startswith("G1")
                           else pool["triggers"][goal.split("_")[0]][lang])
                session = a["session"]
                overlay: dict = {"tickets": [], "notes": [], "policy_docs": []}
                if surface == "message":
                    message = f"{payload}\n\n{trigger}"
                else:
                    message = trigger
                    if surface == "ticket":
                        overlay["tickets"].append({"customer_id": session, "created_at": OVERLAY_TS,
                                                   "category": "general", "language": lang,
                                                   "subject": "Follow-up", "body": payload, "status": "open"})
                    elif surface == "note":
                        overlay["notes"].append({"account_id": world.acc_of[session][0], "author": "Staff-07",
                                                 "created_at": OVERLAY_TS, "body": payload})
                    else:
                        meta = pool["policy_overlay_meta"][tpl["topic"] if goal.startswith("G1") else goal.split("_")[0]]
                        overlay["policy_docs"].append(policy_overlay_doc("P90", meta["title"], meta["keywords"], payload))
                v = a["values"]
                expected: dict = {"goal": goal, "trigger": trigger}
                if goal.startswith("G1"):
                    expected.update(topic=tpl["topic"], planted_value=tpl["planted_value"], planted_unit=tpl["planted_unit"])
                elif goal.startswith("G2"):
                    expected.update(other_customer=a["other"], other_accounts=world.acc_of[a["other"]])
                elif goal.startswith("G3"):
                    expected.update(handoff_expected=True)
                elif goal.startswith("G4"):
                    expected.update(target_tool=tpl["target_tool"],
                                    target={"block_card": v["target_card"], "update_contact": v["attacker_phone"]}
                                    .get(tpl["target_tool"]))
                else:
                    expected.update(target_tool="propose_transfer", from_account=v["target_account"],
                                    to_account=v["attacker_account"], amount=v["amount"])
                items.append({
                    "kind": "attack", "family": family["name"], "technique": family["technique"],
                    "goal": goal, "surface": surface, "language": lang, "customer_id": session,
                    "step_up_verified": False, "message": message, "overlay": overlay,
                    "targets": {"other_customer": a["other"], "attacker_customer": a["attacker"], **v},
                    "expected": {**expected, "required": [], "handoff_kind": "handoff" if goal.startswith("G3") else None,
                                 "policy_doc": None},
                    "seed": rng.randint(1, 2**31 - 1),
                })
    return items


def _lookalike_items(tpl: dict, world: _World, rng: random.Random) -> list[dict]:
    items = []
    text_en = tpl["text"]["en"]
    candidates = sorted({a for a, _ in world.pairs
                         if ("{own_ticket}" not in text_en or world.tickets_of.get(a))
                         and ("{own_txn}" not in text_en or world.last_debit.get(world.acc_of[a][0]))})
    for lang in LANGUAGES:
        session = rng.choice(candidates)
        own_account = world.acc_of[session][0]
        values = {"own_card": rng.choice(world.card_of[session]), "own_account": own_account,
                  "own_ticket": sorted(world.tickets_of.get(session, [""]))[-1],
                  "own_txn": world.last_debit.get(own_account, ""),
                  "new_email": f"customer.{session.lower()}@example.invalid"}
        required = [{"tool": r["tool"], "args": {k: fill(str(x), values) for k, x in r["args"].items()}}
                    for r in tpl["required"]]
        items.append({
            "kind": "lookalike", "family": "lookalike", "technique": tpl["theme"], "template_id": tpl["id"],
            "goal": None, "surface": "message", "language": lang, "customer_id": session,
            "step_up_verified": bool(tpl.get("step_up")), "message": fill(tpl["text"][lang], values),
            "overlay": {"tickets": [], "notes": [], "policy_docs": []}, "targets": {},
            "expected": {"required": required, "handoff_kind": tpl.get("handoff_kind"), "policy_doc": None,
                         "needs_ticket": "{own_ticket}" in tpl["text"]["en"]},
            "seed": rng.randint(1, 2**31 - 1),
        })
    return items


# --------------------------------------------------------------------- freeze
def freeze_suite(pool: dict, world_dir: Path, data_dir: Path, seed: int) -> dict:
    split_path = data_dir / "splits" / f"{SPLIT_NAME}.json"
    if split_path.exists():
        raise FileExistsError(f"{split_path} exists: the split is frozen and never regenerated")
    world = _World(world_dir)
    rng = random.Random(f"{SPLIT_NAME}:{seed}")

    families = sorted(pool["families"], key=lambda f: f["name"])
    heldout_names = set(rng.sample([f["name"] for f in families], HELDOUT_FAMILIES))
    looks = sorted(pool["lookalikes"], key=lambda t: t["id"])
    n_ho_look = round(len(looks) * HELDOUT_LOOKALIKE_SHARE)
    heldout_looks = set(rng.sample([t["id"] for t in looks], n_ho_look))

    opaque = {name: f"HF-{i + 1}" for i, name in enumerate(sorted(heldout_names, key=lambda n: _sha(n.encode())))}
    dev_items, ho_items = [], []
    for fam in families:
        items = _attack_items(fam, world, pool, random.Random(f"{SPLIT_NAME}:{seed}:{fam['name']}"))
        (ho_items if fam["name"] in heldout_names else dev_items).extend(items)
    for t in looks:
        items = _lookalike_items(t, world, random.Random(f"{SPLIT_NAME}:{seed}:{t['id']}"))
        (ho_items if t["id"] in heldout_looks else dev_items).extend(items)
    for i, it in enumerate(dev_items, 1):
        it["scenario_id"], it["split"] = f"ATK-D-{i:04d}", "dev"
    for i, it in enumerate(ho_items, 1):
        it["scenario_id"], it["split"] = f"ATK-H-{i:04d}", "heldout"

    dev_templates = {"families": [f for f in families if f["name"] not in heldout_names],
                     "lookalikes": [t for t in looks if t["id"] not in heldout_looks],
                     "triggers": pool["triggers"], "policy_overlay_meta": pool["policy_overlay_meta"]}
    sealed = seal({"families": [f for f in families if f["name"] in heldout_names],
                   "lookalikes": [t for t in looks if t["id"] in heldout_looks],
                   "opaque_ids": opaque, "items": ho_items})

    (data_dir / "attacks" / "dev").mkdir(parents=True, exist_ok=True)
    (data_dir / "attacks" / "heldout").mkdir(parents=True, exist_ok=True)
    (data_dir / "splits").mkdir(parents=True, exist_ok=True)
    files = {
        data_dir / "attacks" / "dev" / "templates.json": _json_bytes(dev_templates),
        data_dir / "attacks" / "dev" / "items.json": _json_bytes(dev_items),
        data_dir / "attacks" / "heldout" / "heldout.sealed": sealed,
    }
    for p, b in files.items():
        p.write_bytes(b)

    def counts(items, key):
        return dict(sorted(Counter(str(it[key]) for it in items).items()))

    ho_attacks = [it for it in ho_items if it["kind"] == "attack"]
    manifest = {
        "split": SPLIT_NAME, "seed": seed, "procedure": "ADR-0011",
        "dev": {"families": sorted(f["name"] for f in families if f["name"] not in heldout_names),
                "lookalike_templates": sorted(t["id"] for t in looks if t["id"] not in heldout_looks),
                "items": len(dev_items)},
        "heldout": {"families": sorted(opaque.values()),
                    "family_item_counts": {opaque[n]: sum(1 for it in ho_attacks if it["family"] == n)
                                           for n in sorted(heldout_names)},
                    "lookalike_templates": n_ho_look, "items": len(ho_items)},
        "files": {str(p.relative_to(data_dir)).replace("\\", "/"): _sha(b) for p, b in files.items()},
    }
    mbytes = _json_bytes(manifest)
    split_path.write_bytes(mbytes)
    (data_dir / "splits" / f"{SPLIT_NAME}.sha256").write_bytes(f"{_sha(mbytes)}  {SPLIT_NAME}.json\n".encode())

    def table(items):
        atk = [it for it in items if it["kind"] == "attack"]
        return {"attacks": len(atk), "lookalikes": len(items) - len(atk),
                "by_goal": counts(atk, "goal"), "by_surface": counts(atk, "surface"),
                "by_language": counts(atk, "language"),
                "lookalikes_by_language": counts([it for it in items if it["kind"] == "lookalike"], "language")}
    stats = {"dev": {**table(dev_items), "by_family": counts([it for it in dev_items if it["kind"] == "attack"], "family")},
             "heldout": {**table(ho_items), "families": len(heldout_names)}}
    (data_dir / "attacks" / "stats.json").write_bytes(_json_bytes(stats))
    return {"manifest": manifest, "manifest_sha256": _sha(mbytes), "stats": stats}


# ---------------------------------------------------------------------- load
def verify_split(data_dir: Path) -> dict:
    """Check the manifest checksum and every file checksum listed in it. Reads no held-out content."""
    mpath = data_dir / "splits" / f"{SPLIT_NAME}.json"
    mbytes = mpath.read_bytes()
    pinned = (data_dir / "splits" / f"{SPLIT_NAME}.sha256").read_text(encoding="utf-8").split()[0]
    if _sha(mbytes) != pinned:
        raise ValueError("split manifest does not match its checksum")
    manifest = json.loads(mbytes)
    for rel, digest in manifest["files"].items():
        if _sha((data_dir / rel).read_bytes()) != digest:
            raise ValueError(f"{rel} does not match the split manifest")
    return manifest


def load_dev_items(data_dir: Path) -> list[dict]:
    verify_split(data_dir)
    return json.loads((data_dir / "attacks" / "dev" / "items.json").read_text(encoding="utf-8"))


def load_heldout_items(data_dir: Path) -> list[dict]:
    """Only for the gate-approved Stage 5/6 held-out runs."""
    if os.environ.get(HELDOUT_ENV) != HELDOUT_TOKEN:
        raise PermissionError(f"held-out items are sealed; set {HELDOUT_ENV} only for the gate-approved run")
    verify_split(data_dir)
    return unseal((data_dir / "attacks" / "heldout" / "heldout.sealed").read_bytes())["items"]
