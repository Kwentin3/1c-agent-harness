# Issue #31 — formal preflight and agent semantic challenge

This package keeps two different checks explicit before any native 1C attempt.

1. **Agent semantic challenge.** Starting from the short user task, the agent makes the semantic model explicit, retains plausible countermodels, maps each clause to cases and scalar observations, and records unknowns instead of inventing acceptance criteria. This is human/domain reasoning governed by `semantic-contract-testing`.
2. **Formal/oracle coherence.** `scripts/semantic_preflight.py` validates the prepared plan, complete vectors, artificial RED/GREEN receipts, and exact receipt policy. It does not claim to understand natural language or prove that the agent selected the right countermodels.

The result names are deliberately separate:

- `FORMAL COHERENCE READY` — the declared formal instrument is coherent; an agent semantic challenge is still required before native work.
- `CONTRACT BLOCKED` — a declared contradiction, survivor, missing provenance/coverage, malformed plan, or receipt failure was found.

Every output includes `nativeRun: false`.

## Entry point

```bash
python3 scripts/semantic_preflight.py \
  experiments/issue31-semantic-preflight/issue29-plan.json

python3 scripts/semantic_preflight.py \
  experiments/issue31-semantic-preflight/fresh-discount-plan.json
```

Exit `0` is `FORMAL COHERENCE READY`; exit `1` is `CONTRACT BLOCKED`.

## What the formal plan must bind

This is ordinary JSON, not a business-rule DSL. The validator requires only enough provenance to block the three reproduced omission/bypass shapes:

- a `user-task` clause includes a nonempty verbatim `taskQuote` contained in the plan's `task`;
- an `established-domain` clause carries a repository-relative `{path, locator, quote}`; `locator` is exactly `line:N` and that line must contain the quote;
- every clause must be referenced by at least one observation and case;
- at least one explicit countermodel is required; each predicts all case × observation cells;
- observations are scalar and externally checkable; unknown clauses block;
- RED/GREEN bindings are complete and unique, GREEN equals the case matrix, RED differs, and receipts follow the exact policy.

These checks do **not** convert quoted text into a proof of business semantics. They make agent reasoning inspectable and make a contradictory task, unlocated domain claim, or silent removal of all countermodels fail closed.

Plan and receipt paths remain repository-relative, reject traversal and symlinks, and must be small regular files. The prior descriptor/inode race hardening was intentionally removed: no matching single-user threat model was demonstrated, and the KISS budget is reserved for semantic linkage.

## Frozen issue #29 control

`issue29-plan.json` uses byte-identical local copies of frozen issue #29 receipts and transcribes its published case/observation material. It returns `CONTRACT BLOCKED` by general rules:

1. `last-row-only` matches the declared complete vector and survives;
2. RED's exact expectation omits receipt keys;
3. `no-posting-exception` is unknown rather than an authorized criterion;
4. the `Structure` balance comparison is non-scalar and externally uncheckable.

The validator contains no issue-29-specific branch. This control is a regression fixture, not evidence that the CLI independently discovered issue #29 from source code.

## Fresh no-native acceptance

[`fresh-acceptance.md`](fresh-acceptance.md) records a separate small discount-threshold task, a reproducible formal matrix, plan, and artificial receipts. Its plan returns `FORMAL COHERENCE READY`; no 1C, snapshot, infobase, dependency, daemon, service, or GUI is used. Historical fresh-executor chronology is explicitly marked **unproven** unless a reviewable report binds the exact task, allowed context, executor identity, full result, duration, and candidate identity.

## Limits

- The validator checks declared provenance and formal coherence, not natural-language entailment, task-to-contract contradiction, or completeness of the real-world countermodel set. In particular, a verbatim `taskQuote` can prove only text presence; it cannot distinguish negation or quotation of that text.
- The agent and relevant domain source remain responsible for semantic challenge. An independent reviewer is required only for this issue's acceptance, not ordinary daily preflight.
- The executable supports one exact `key###value` receipt policy; no registry or workflow engine is added.
