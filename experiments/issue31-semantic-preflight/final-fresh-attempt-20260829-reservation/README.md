# Final observable fresh attempt — reservation threshold

## Verdict

**PREFLIGHT FAIL / FORMAL TOOL ONLY**

This is the one fresh no-native attempt authorized by the owner decision. It is preserved because it failed honestly: the executor had enough public guidance to form a substantive three-case semantic matrix, but its plan did not conform to the validator's undocumented clause schema. It made one transparent correction (`schemaVersion: 1`) after the initial schema error; the one permitted re-check then returned `CONTRACT BLOCKED`. No further correction or attempt was made.

This package does not reconstruct older fresh runs and does not claim a successful fresh-executor path.

## Bound attempt

| Field | Value |
|---|---|
| Task | `Confirm a reservation only when requested units do not exceed available units; reject a request above availability.` |
| Candidate at start | HEAD `5ef41ff0e5b3671d7c899114ca199cf0f73a3d67`, tree `08c3704058b46083e6a36fe8688e970999f23bb8` |
| Skill | `semantic-contract-testing` v`0.3.0`, resource manifest SHA-256 `f63f51f84786b3287cc2265089d4d6264b97baa7e4d193c7808efef67c75129c` |
| Executor | Hermes Agent subagent; Git identity `Kwentin3 <123741920+Kwentin3@users.noreply.github.com>` |
| Duration | `71195.62645 ms` monotonic elapsed time |
| Native attempts / owner interventions | `0 / 0` |
| Formal command | `python3 scripts/semantic_preflight.py .local/issue31-final-fresh/issue31-reservation-plan.json` |
| Formal result | exit `1`; `CONTRACT BLOCKED`; `nativeRun: false` |

The subagent's declared allowed and forbidden context, complete semantic challenge (clauses, unknowns, observation, three cases, and countermodels), full formal stdout/stderr, correction history, and artifact hashes are preserved **verbatim** in [`verbatim-result.json`](verbatim-result.json). [`executor-transcript.log`](executor-transcript.log) preserves the available live trace and visibly records the two formal invocations and one patch.

## Evidence-boundary failure

The retained live transcript is renderer-truncated/ellipsized and some read operations are not path-qualified. It therefore does **not** independently prove that the executor read *only* the declared context or that no forbidden action occurred. This package is deliberately classified `PREFLIGHT FAIL / FORMAL TOOL ONLY` for that evidence-boundary defect as well as the formal schema failure. It is a durable record of the one authorized attempt, not a claim that the observable fresh-executor acceptance gate passed.

## Failure mechanism

The initial formal check rejected a missing top-level `schemaVersion`. The only correction added `schemaVersion: 1`. The allowed re-check then rejected `clauses[0]` because the public issue README had described provenance requirements but not the validator's exact required clause shape: `basis`, `id`, `source`, and `statement`. The executor had instead created `id`, `kind`, and `taskQuote`.

This is a failure of the fresh path, not a claim that the semantic matrix is accepted. The executor's independently derived cases were below availability (`4/5 → confirmed`), equality (`5/5 → confirmed`), and above availability (`6/5 → rejected`); its plausible countermodels were strict-less-than, unconditional confirmation, and equality-only confirmation. The exact unaccepted plan and artificial receipts are retained for inspection.

## Integrity

[`manifest.json`](manifest.json) binds the attempt identity and SHA-256 values for every retained artifact. The formal command originally consumed the `.local` path named in the verbatim report; the byte-identical retained copies are committed here. Verify with:

```bash
sha256sum -c <(python3 - <<'PY'
import json
for path, digest in json.load(open('manifest.json'))['artifacts'].items():
    print(f'{digest}  {path}')
PY
)
```

No native 1C, GUI, service, dependency, network, `scripts/native_cycle.py`, or `scripts/project_target.py` was invoked by the executor.
