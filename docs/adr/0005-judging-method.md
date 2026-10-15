# ADR-0005: Judging method — deterministic judges only

Status: Accepted (user decision, 2026-10-15)

## Decision
- Every metric uses deterministic judges (see system-design §7): audit log, approval queue, handoff log, ownership table, and structured policy facts.
- **The optional same-model wording judge (Section 0.3) is not used.** Fabricated non-numeric policy claims (wording-only) are therefore **not measured**, and reports will say so in the limitations.
- No hosted judge is used.
- Because no LLM-judged number is reported, the Stage 5 60-item labelling sheet and kappa check do not apply. `docs/judge-validation.md` will record the deterministic judges' fixture-test results and a hand spot-check of numeric-fabrication flags on DEVELOPMENT runs, done by the user. The spot-check is reported as precision on flagged items with a Wilson CI, and it is descriptive: no threshold gates it.

## Consequences
- Fewer model calls and no same-model bias in the headline numbers.
- RQ1/RQ2 coverage of "fabricated policy" is limited to numeric claims (fees, limits, deadlines). The Stage 1 policy corpus will put most of its checkable claims in numeric form so this metric has enough substance.
- Changing this decision later needs a new ADR, made before any attack result is seen.
