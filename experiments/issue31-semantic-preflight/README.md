# Issue #31 — semantic preflight before native 1C

This package demonstrates a cheap, fail-closed check of a proposed semantic contract, probe observation plan, and external oracle **before** any native 1C attempt.

The preflight does not prove business behavior and does not choose requirements. It validates only what the plan declares:

- every acceptance clause identifies its basis (`user-task`, `established-domain`, or `unknown`);
- observations are declared externally checkable and scalar;
- every case and countermodel supplies the complete declared observation vector, so a matching countermodel is reported as a survivor;
- artificial receipts match their declared expectations under the explicit `exact` key-set policy;
- exactly RED and GREEN are required; in each phase, `bindings` uniquely cover the complete case/observation matrix, GREEN equals the semantic matrix, and RED differs from GREEN;
- duplicate receipt keys are detected before dictionary conversion.

## Entry point

From the repository root:

```bash
python3 scripts/semantic_preflight.py \
  experiments/issue31-semantic-preflight/issue29-plan.json

python3 scripts/semantic_preflight.py \
  experiments/issue31-semantic-preflight/positive-control.json
```

Exit code `0` means `READY FOR NATIVE`; exit code `1` means `CONTRACT BLOCKED`. Output is JSON and always includes `nativeRun: false`.

A fresh plan is ordinary JSON, not a new business-rule DSL. Use the two published inputs as small examples. Plan and receipt paths are opened component-by-component relative to the repository descriptor; descriptor-based reads reject absolute paths, traversal, symlink ancestors/finals, multiply linked files, and files larger than 1 MB without reflecting untrusted receipt keys. The semantic meaning still comes from the user task and the relevant domain skill; the validator merely checks the declared matrix and receipt policy.

## Frozen issue #29 control

`issue29-plan.json` uses byte-identical local copies of the frozen issue #29 receipts and transcribes the published oracle expectations and case matrix. A regression test binds each copy to the unchanged original. The validator contains no issue-29-specific checks or names.

It returns `CONTRACT BLOCKED` through general rules:

1. `last-row-only` predicts the same complete observation vector as the required behavior and therefore survives;
2. the exact RED oracle expectation omits keys present in the complete RED receipt;
3. `no-posting-exception` is marked `unknown`, because neither the user task nor a cited established 1C semantic source made it a requirement;
4. the balance observation is explicitly non-scalar and not externally checkable because it came from equality of separate 1C `Structure` values.

The same receipt comparison also reports the contradictory GREEN exception and balance values. These are additional contradictions, not substitutes for the four required defect classes.

## Positive control and oracle mutations

`positive-control.json` declares a minimal `quantity > 0` rule. Its zero/positive cases distinguish `>= 0` and reject-all countermodels, all clauses have a user-task basis, and both artificial complete receipts match the exact oracle expectation. It returns `READY FOR NATIVE`.

`tests/test_semantic_preflight.py` copies that plan into repository-local temporary directories and proves that missing, extra, duplicate, and wrong-value receipt mutations are rejected individually. It also proves fail-closed behavior for missing RED/GREEN, incomplete or duplicate semantic bindings, duplicate countermodel IDs, GREEN/case disagreement, RED=GREEN, boolean schema versions, empty semantic values, malformed paths, absolute/traversal paths, receipt and plan symlinks, FIFOs, and a symlink-loop plan.

## Domain ownership

- Generic countermodel matrices, requirement provenance, oracle coherence, and verdict semantics are documented in `skills/software-development/semantic-contract-testing/`.
- 1C posting exception uncertainty and scalar register-balance observations are documented in `skills/1c/1c-enterprise-linux/references/data-backed-document-write-probes.md`.
- `scripts/semantic_preflight.py` performs formal checks only. It never imports, launches, or locates 1C and does not read `project-target.json`, snapshots, or infobases.

## Limits

- A dishonest or incomplete plan can omit a plausible countermodel or falsely label an observation scalar. Human/domain reasoning is still required to prepare the plan.
- `READY FOR NATIVE` means the declared measuring instrument is internally coherent, not that the production function works.
- The executable validator intentionally supports only one receipt policy (`exact`) and one `key###value` text format. The skills describe when another explicit policy may be designed, but this issue does not add a framework or registry.
- Independent review is required for acceptance of this new capability at exact HEAD, not for ordinary daily use.
