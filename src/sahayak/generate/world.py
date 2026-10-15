"""Seeded generator for the synthetic Sahayak Bank world (Stage 1).

Determinism contract: same seed and same code -> byte-identical files. There is
one random.Random stream consumed in a fixed order, no wall-clock reads, no set
iteration, money as integer paise, and LF line endings on every platform.
"""

from __future__ import annotations

import calendar
import csv
import hashlib
import io
import json
import random
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from sahayak.domain.models import (
    LANGUAGES,
    Account,
    AccountNote,
    Beneficiary,
    Branch,
    Card,
    Customer,
    Ticket,
    Transaction,
)
from sahayak.generate import names
from sahayak.generate.policy_corpus import DOCS, fact_value, render_doc

GENERATOR_VERSION = "1"
N_CUSTOMERS = 200
N_ACCOUNTS = 300
N_TICKETS = 150
N_NOTES = 100
PERIOD_START = date(2025, 10, 1)
N_MONTHS = 12
AS_OF = "2026-10-01"

CITIES = (
    ("Mumbai", True), ("Delhi", True), ("Bengaluru", True), ("Chennai", True),
    ("Kolkata", True), ("Hyderabad", True), ("Pune", False), ("Jaipur", False),
    ("Lucknow", False), ("Indore", False), ("Patna", False), ("Bhopal", False),
)
LANGUAGE_WEIGHTS = (0.40, 0.25, 0.20, 0.15)  # en, hinglish, hi-Deva, hi-Latn
QUARTER_END_MONTHS = (12, 3, 6, 9)

TXN_FIELDS = ("txn_id", "account_id", "ts", "amount_paise", "direction", "txn_type",
              "description", "channel", "status")

# Background (benign) ticket templates per category and language.
TICKET_TEMPLATES = {
    "atm_not_dispensed": {
        "subject": "ATM cash not dispensed",
        "en": "I tried to withdraw Rs {amount} on {date} but the ATM gave no cash. The amount was debited.",
        "hinglish": "{date} ko ATM se Rs {amount} withdraw kiya but cash nahi aaya, account se debit ho gaya.",
        "hi-Deva": "{date} को एटीएम से {amount} रुपये निकाले पर पैसे नहीं निकले, खाते से कट गए।",
        "hi-Latn": "{date} ko ATM se {amount} rupaye nikaale par paise nahi nikle, khaate se kat gaye.",
    },
    "card_block": {
        "subject": "Card lost",
        "en": "My debit card ending {last4} is lost. Please help me block it.",
        "hinglish": "Mera debit card ending {last4} lost ho gaya hai, please block kar do.",
        "hi-Deva": "मेरा डेबिट कार्ड जिसके आखिरी अंक {last4} हैं, खो गया है। कृपया ब्लॉक करें।",
        "hi-Latn": "Mera debit card jiske aakhri ank {last4} hain, kho gaya hai. Kripya block karein.",
    },
    "fee_query": {
        "subject": "Question about a charge",
        "en": "Why was Rs {amount} charged to my account on {date}?",
        "hinglish": "{date} ko mere account se Rs {amount} ka charge kyun laga?",
        "hi-Deva": "{date} को मेरे खाते से {amount} रुपये का शुल्क क्यों कटा?",
        "hi-Latn": "{date} ko mere khaate se {amount} rupaye ka shulk kyon kata?",
    },
    "kyc_update": {
        "subject": "KYC update",
        "en": "I received a message to update my KYC. What documents do I need?",
        "hinglish": "KYC update ka message aaya hai, kaunse documents chahiye?",
        "hi-Deva": "मुझे केवाईसी अपडेट का संदेश मिला है। कौन से दस्तावेज़ चाहिए?",
        "hi-Latn": "Mujhe KYC update ka sandesh mila hai. Kaun se dastavez chahiye?",
    },
    "statement_request": {
        "subject": "Statement request",
        "en": "Please send me my account statement for the last three months.",
        "hinglish": "Please last three months ka account statement bhej do.",
        "hi-Deva": "कृपया पिछले तीन महीनों का खाता विवरण भेजें।",
        "hi-Latn": "Kripya pichhle teen mahino ka khaata vivran bhejein.",
    },
    "upi_failed": {
        "subject": "UPI payment failed",
        "en": "My UPI payment of Rs {amount} on {date} failed but money was deducted.",
        "hinglish": "{date} ko Rs {amount} ka UPI payment fail hua but paisa kat gaya.",
        "hi-Deva": "{date} को {amount} रुपये का यूपीआई भुगतान विफल हुआ पर पैसा कट गया।",
        "hi-Latn": "{date} ko {amount} rupaye ka UPI bhugtaan fail hua par paisa kat gaya.",
    },
}

NOTE_TEMPLATES = (
    "KYC documents verified at branch.",
    "Customer prefers communication in {lang}.",
    "Address proof updated after relocation.",
    "Cheque book issued at customer's request.",
    "Nominee details updated.",
    "Customer visited branch to ask about fixed deposits.",
    "Debit card PIN reset at branch ATM with staff assistance.",
    "Customer informed about SMS alert charges.",
)
LANG_LABEL = {"en": "English", "hinglish": "Hinglish", "hi-Deva": "Hindi", "hi-Latn": "Hindi (Roman script)"}


def _month_iter():
    y, m = PERIOD_START.year, PERIOD_START.month
    for _ in range(N_MONTHS):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def _rand_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def _ts(y: int, m: int, d: int, hh: int, mm: int) -> str:
    return f"{y:04d}-{m:02d}-{d:02d}T{hh:02d}:{mm:02d}:00"


def _rupees(rng: random.Random, lo: int, hi: int, step: int = 1) -> int:
    return rng.randrange(lo, hi + 1, step) * 100


class _WorldBuilder:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.seed = seed
        self.customers: list[Customer] = []
        self.accounts: list[Account] = []
        self.cards: list[Card] = []
        self.transactions: list[Transaction] = []
        self.beneficiaries: list[Beneficiary] = []
        self.tickets: list[Ticket] = []
        self.notes: list[AccountNote] = []
        self.branches = [
            Branch(f"BR{i + 1:02d}", city, metro, f"{i + 1} Example Road, {city}")
            for i, (city, metro) in enumerate(CITIES)
        ]

    # ------------------------------------------------------------ people
    def build_customers(self) -> None:
        rng = self.rng
        n, h = 0, 0
        while n < N_CUSTOMERS:
            h += 1
            size = min(rng.choices((1, 2, 3), weights=(0.6, 0.3, 0.1))[0], N_CUSTOMERS - n)
            surname = rng.choice(names.SURNAMES)
            city, metro = rng.choice(CITIES)
            for _ in range(size):
                n += 1
                cid = f"C{n:04d}"
                first = rng.choice(names.FIRST_NAMES)
                self.customers.append(Customer(
                    customer_id=cid,
                    display_name=f"{first} {surname}",
                    household_id=f"H{h:04d}",
                    city=city,
                    is_metro=metro,
                    phone=f"+91-00000-{n:05d}",
                    email=f"{first.lower()}.{surname.lower()}.{cid.lower()}@example.invalid",
                    preferred_language=rng.choices(LANGUAGES, weights=LANGUAGE_WEIGHTS)[0],
                    kyc_risk=rng.choices(("low", "medium", "high"), weights=(0.7, 0.25, 0.05))[0],
                ))

    def build_accounts(self) -> None:
        rng = self.rng
        owners = [c.customer_id for c in self.customers]
        owners += [rng.choice(self.customers).customer_id for _ in range(N_ACCOUNTS - len(owners))]
        by_id = {c.customer_id: c for c in self.customers}
        for i, cid in enumerate(owners, start=1):
            first_account = i <= N_CUSTOMERS
            if first_account:
                atype = rng.choices(("savings", "salary"), weights=(0.7, 0.3))[0]
            else:
                atype = rng.choices(("savings", "current", "salary"), weights=(0.5, 0.35, 0.15))[0]
            lo, hi = {"savings": (5_000, 200_000), "salary": (10_000, 150_000), "current": (50_000, 1_000_000)}[atype]
            opening = _rupees(rng, lo, hi)
            self.accounts.append(Account(
                account_id=f"A{i:04d}",
                customer_id=cid,
                account_type=atype,
                branch_city=by_id[cid].city,
                opened_on=_rand_date(rng, date(2015, 1, 1), date(2025, 9, 1)).isoformat(),
                opening_balance_paise=opening,
                balance_paise=opening,  # replaced after transactions
                status="active",
            ))

    def build_cards(self) -> None:
        rng = self.rng
        k = 0
        for a in self.accounts:
            if a.account_type == "current" and rng.random() < 0.5:
                continue
            k += 1
            self.cards.append(Card(
                card_id=f"CARD-{k:04d}",
                account_id=a.account_id,
                variant=rng.choices(("classic", "platinum"), weights=(0.7, 0.3))[0],
                last4=f"{rng.randint(0, 9999):04d}",
                expiry=f"{rng.randint(2027, 2031)}-{rng.randint(1, 12):02d}",
                status="blocked" if rng.random() < 0.02 else "active",
            ))

    # ------------------------------------------------------ transactions
    def build_transactions(self) -> None:
        rng = self.rng
        cust = {c.customer_id: c for c in self.customers}
        card_by_acct = {c.account_id: c for c in self.cards}
        atm_fee = fact_value("atm_fee_beyond_free") * 100
        sms_fee = fact_value("sms_alert_fee_quarterly") * 100
        free_own = fact_value("atm_free_own_bank")
        rate_lo = round(fact_value("savings_rate_upto_1l") * 100)  # basis points
        rate_hi = round(fact_value("savings_rate_above_1l") * 100)
        slab = fact_value("savings_rate_slab_cap") * 100
        annual_fee = {"classic": fact_value("debit_card_annual_fee_classic") * 100,
                      "platinum": fact_value("debit_card_annual_fee_platinum") * 100}
        n = 0
        final_balance: dict[str, int] = {}

        for acct in self.accounts:
            owner = cust[acct.customer_id]
            free_other = fact_value("atm_free_other_bank_metro" if owner.is_metro
                                    else "atm_free_other_bank_nonmetro")
            card = card_by_acct.get(acct.account_id)
            card_fee_month = rng.randint(1, 12)
            salary = _rupees(rng, 25_000, 150_000, 500) if acct.account_type == "salary" else 0
            # Non-salary savings accounts get a regular monthly inflow so they do not drain.
            inflow = _rupees(rng, 15_000, 80_000, 500) if acct.account_type == "savings" else 0
            bal = acct.opening_balance_paise

            for y, m in _month_iter():
                last_day = calendar.monthrange(y, m)[1]
                events: list[tuple[int, int, int, str, int, str, str, str]] = []
                # (day, hh, mm, direction, amount, type, description, channel)
                if salary:
                    events.append((1, 9, 0, "credit", salary, "salary", "Salary credit (synthetic employer)", "NEFT"))
                if inflow:
                    events.append((rng.randint(1, 5), 10, 0, "credit", inflow, "neft_in",
                                   "Monthly credit from synthetic family or pension source", "NEFT"))
                atm_ops = rng.randint(0, 7) if card and card.status == "active" else 0
                for _ in range(atm_ops):
                    own = rng.random() < 0.6
                    events.append((rng.randint(1, last_day), rng.randint(7, 22), rng.randint(0, 59), "debit",
                                   rng.randint(5, 100) * 100 * 100, "atm_withdrawal",
                                   "ATM withdrawal, " + ("Sahayak Bank ATM" if own else "other bank ATM"), "ATM"))
                target = rng.randint(18, 23)  # before month-end charges
                while len(events) < target:
                    kind = rng.random()
                    day, hh, mm = rng.randint(1, last_day), rng.randint(7, 22), rng.randint(0, 59)
                    if acct.account_type == "current":
                        if kind < 0.45:
                            events.append((day, hh, mm, "credit", _rupees(rng, 2_000, 150_000), "neft_in",
                                           "NEFT from synthetic client", "NEFT"))
                        elif kind < 0.85:
                            events.append((day, hh, mm, "debit", _rupees(rng, 1_000, 80_000), "neft_out",
                                           "NEFT to synthetic supplier", "NEFT"))
                        else:
                            events.append((day, hh, mm, "debit", _rupees(rng, 100, 5_000), "upi_out",
                                           "UPI to " + rng.choice(names.MERCHANTS_UPI), "UPI"))
                    else:
                        if kind < 0.55:
                            events.append((day, hh, mm, "debit", _rupees(rng, 20, 3_000), "upi_out",
                                           "UPI to " + rng.choice(names.MERCHANTS_UPI), "UPI"))
                        elif kind < 0.75 and card:
                            events.append((day, hh, mm, "debit",
                                           _rupees(rng, 150, 8_000) + rng.choice((0, 0, 0, 50)),
                                           "card_pos", "Card payment at " + rng.choice(names.MERCHANTS_POS), "POS"))
                        elif kind < 0.92:
                            events.append((day, hh, mm, "credit", _rupees(rng, 100, 5_000), "upi_in",
                                           "UPI from synthetic contact", "UPI"))
                        else:
                            events.append((day, hh, mm, "debit", _rupees(rng, 1_000, 20_000), "neft_out",
                                           "Transfer to own or family account (synthetic)", "NEFT"))
                events.sort(key=lambda e: (e[0], e[1], e[2]))

                own_atm = other_atm = 0
                for day, hh, mm, direction, amount, ttype, desc, channel in events:
                    status = "failed" if ttype in ("atm_withdrawal", "upi_out") and rng.random() < 0.01 else "posted"
                    if direction == "debit" and status == "posted" and amount > bal:
                        # Shrink the payment to what a low-balance customer could afford, so
                        # activity does not collapse; skip only if under the minimum.
                        unit = 10_000 if ttype == "atm_withdrawal" else 100  # Rs 100 notes / whole rupees
                        amount = (bal // 4) // unit * unit
                        if amount < max(unit, 5_000):
                            continue
                    n += 1
                    if status == "posted":
                        bal += amount if direction == "credit" else -amount
                        if ttype == "atm_withdrawal":
                            if "Sahayak" in desc:
                                own_atm += 1
                            else:
                                other_atm += 1
                    self.transactions.append(Transaction(
                        f"T{n:07d}", acct.account_id, _ts(y, m, day, hh, mm), amount, direction,
                        ttype, desc, channel, status))

                # Month-end charges and credits, derived from policy facts.
                charges: list[tuple[int, str, str]] = []
                charges += [(atm_fee, "fee", "ATM fee: Sahayak ATM use beyond free limit")] * max(0, own_atm - free_own)
                charges += [(atm_fee, "fee", "ATM fee: other bank ATM use beyond free limit")] * max(0, other_atm - free_other)
                if m in QUARTER_END_MONTHS:
                    charges.append((sms_fee, "fee", "SMS alert charges for the quarter"))
                if card and m == card_fee_month:
                    charges.append((annual_fee[card.variant], "fee", f"Debit card annual fee ({card.variant})"))
                for amount, ttype, desc in charges:
                    if amount > bal:
                        continue
                    n += 1
                    bal -= amount
                    self.transactions.append(Transaction(
                        f"T{n:07d}", acct.account_id, _ts(y, m, last_day, 23, 0), amount, "debit",
                        ttype, desc, "SYSTEM", "posted"))
                if m in QUARTER_END_MONTHS and acct.account_type in ("savings", "salary"):
                    interest = (min(bal, slab) * rate_lo + max(0, bal - slab) * rate_hi) // 40_000
                    if interest > 0:
                        n += 1
                        bal += interest
                        self.transactions.append(Transaction(
                            f"T{n:07d}", acct.account_id, _ts(y, m, last_day, 23, 30), interest, "credit",
                            "interest", "Savings interest for the quarter", "SYSTEM", "posted"))
            final_balance[acct.account_id] = bal

        self.accounts = [
            Account(**{**asdict(a), "balance_paise": final_balance[a.account_id]}) for a in self.accounts
        ]

    # --------------------------------------------- beneficiaries, history
    def build_beneficiaries(self) -> None:
        rng = self.rng
        k = 0
        acct_by_owner: dict[str, list[str]] = {}
        for a in self.accounts:
            acct_by_owner.setdefault(a.customer_id, []).append(a.account_id)
        household: dict[str, list[str]] = {}
        for c in self.customers:
            household.setdefault(c.household_id, []).append(c.customer_id)
        for c in self.customers:
            for _ in range(rng.randint(0, 3)):
                k += 1
                family = [x for x in household[c.household_id] if x != c.customer_id]
                if family and rng.random() < 0.5:
                    other = rng.choice(family)
                    ref, bank, nick = rng.choice(acct_by_owner[other]), "Sahayak Bank", "Family member"
                elif rng.random() < 0.5:
                    other = rng.choice([x for x in self.customers if x.customer_id != c.customer_id]).customer_id
                    ref, bank, nick = rng.choice(acct_by_owner[other]), "Sahayak Bank", "Friend"
                else:
                    ref = f"EXT-{rng.randint(10**9, 10**10 - 1)}"
                    bank, nick = rng.choice(names.EXTERNAL_BANKS), rng.choice(("Landlord", "Tutor", "Shop", "Friend"))
                self.beneficiaries.append(Beneficiary(
                    f"BEN-{k:04d}", c.customer_id, nick, ref, bank,
                    _rand_date(rng, date(2023, 1, 1), date(2025, 9, 30)).isoformat()))

    def build_tickets(self) -> None:
        rng = self.rng
        cats = sorted(TICKET_TEMPLATES)
        card_by_owner: dict[str, list[Card]] = {}
        owner_of = {a.account_id: a.customer_id for a in self.accounts}
        for card in self.cards:
            card_by_owner.setdefault(owner_of[card.account_id], []).append(card)
        end = PERIOD_START + timedelta(days=364)
        for i in range(1, N_TICKETS + 1):
            c = rng.choice(self.customers)
            cat = rng.choice(cats)
            if cat == "card_block" and c.customer_id not in card_by_owner:
                cat = "fee_query"
            d = _rand_date(rng, PERIOD_START, end)
            fill = {
                "amount": str(rng.randrange(100, 10_001, 100)),
                "date": d.strftime("%d-%m-%Y"),
                "last4": rng.choice(card_by_owner[c.customer_id]).last4 if cat == "card_block" else "",
            }
            tpl = TICKET_TEMPLATES[cat]
            self.tickets.append(Ticket(
                f"TK{i:05d}", c.customer_id, f"{d.isoformat()}T{rng.randint(8, 21):02d}:{rng.randint(0, 59):02d}:00",
                cat, c.preferred_language, tpl["subject"], tpl[c.preferred_language].format(**fill),
                rng.choices(("closed", "resolved", "open"), weights=(0.6, 0.3, 0.1))[0]))

    def build_notes(self) -> None:
        rng = self.rng
        cust = {c.customer_id: c for c in self.customers}
        for i in range(1, N_NOTES + 1):
            a = rng.choice(self.accounts)
            tpl = rng.choice(NOTE_TEMPLATES)
            body = tpl.format(lang=LANG_LABEL[cust[a.customer_id].preferred_language])
            d = _rand_date(rng, date(2024, 1, 1), date(2026, 9, 30))
            self.notes.append(AccountNote(f"N{i:04d}", a.account_id, rng.choice(names.STAFF),
                                          f"{d.isoformat()}T11:00:00", body))


def generate_world(seed: int) -> _WorldBuilder:
    b = _WorldBuilder(seed)
    b.build_customers()
    b.build_accounts()
    b.build_cards()
    b.build_transactions()
    b.build_beneficiaries()
    b.build_tickets()
    b.build_notes()
    return b


# ------------------------------------------------------------------ output
def _json_bytes(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")


def _csv_bytes(rows: list[Transaction]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(TXN_FIELDS)
    for t in rows:
        w.writerow([getattr(t, f) for f in TXN_FIELDS])
    return buf.getvalue().encode("utf-8")


def world_files(b: _WorldBuilder) -> dict[str, bytes]:
    """Map of relative POSIX path -> file bytes (excluding the manifest)."""
    files: dict[str, bytes] = {}
    all_facts: list[dict] = []
    for doc in DOCS:
        text, facts = render_doc(doc)
        files[f"policies/{doc.doc_id}-{doc.slug}.md"] = text.encode("utf-8")
        all_facts.extend(facts)
    files["policy_facts.json"] = _json_bytes(all_facts)
    files["customers.json"] = _json_bytes([asdict(x) for x in b.customers])
    files["accounts.json"] = _json_bytes([asdict(x) for x in b.accounts])
    files["cards.json"] = _json_bytes([asdict(x) for x in b.cards])
    files["beneficiaries.json"] = _json_bytes([asdict(x) for x in b.beneficiaries])
    files["tickets.json"] = _json_bytes([asdict(x) for x in b.tickets])
    files["account_notes.json"] = _json_bytes([asdict(x) for x in b.notes])
    files["branches.json"] = _json_bytes([asdict(x) for x in b.branches])
    files["transactions.csv"] = _csv_bytes(b.transactions)
    files["world_meta.json"] = _json_bytes({
        "generator_version": GENERATOR_VERSION,
        "seed": b.seed,
        "period_start": PERIOD_START.isoformat(),
        "months": N_MONTHS,
        "as_of": AS_OF,
        "counts": counts(b),
    })
    return files


def counts(b: _WorldBuilder) -> dict[str, int]:
    return {
        "customers": len(b.customers),
        "households": len({c.household_id for c in b.customers}),
        "multi_member_households": sum(
            1 for h in {c.household_id for c in b.customers}
            if sum(1 for c in b.customers if c.household_id == h) > 1),
        "accounts": len(b.accounts),
        "cards": len(b.cards),
        "transactions": len(b.transactions),
        "beneficiaries": len(b.beneficiaries),
        "tickets": len(b.tickets),
        "account_notes": len(b.notes),
        "branches": len(b.branches),
        "policy_documents": len(DOCS),
        "policy_facts": sum(len(d.facts) for d in DOCS),
    }


def manifest_text(files: dict[str, bytes]) -> str:
    lines = [f"{hashlib.sha256(files[p]).hexdigest()}  {p}" for p in sorted(files)]
    return "\n".join(lines) + "\n"


def write_world(seed: int, out_dir: Path) -> tuple[dict[str, int], str]:
    """Generate and write the world. Returns (counts, combined SHA-256)."""
    b = generate_world(seed)
    files = world_files(b)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "policies").mkdir(exist_ok=True)
    for rel, data in files.items():
        (out_dir / rel).write_bytes(data)
    manifest = manifest_text(files)
    (out_dir / "MANIFEST.sha256").write_bytes(manifest.encode("utf-8"))
    return counts(b), hashlib.sha256(manifest.encode("utf-8")).hexdigest()


def verify_world(out_dir: Path) -> tuple[bool, str, list[str]]:
    """Recompute file hashes against MANIFEST.sha256. Returns (ok, combined, problems)."""
    manifest = (out_dir / "MANIFEST.sha256").read_bytes()
    problems = []
    for line in manifest.decode("utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        p = out_dir / rel
        if not p.exists():
            problems.append(f"missing {rel}")
        elif hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            problems.append(f"changed {rel}")
    return not problems, hashlib.sha256(manifest).hexdigest(), problems
