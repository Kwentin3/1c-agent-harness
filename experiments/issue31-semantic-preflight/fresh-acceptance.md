# Fresh no-native acceptance — discount threshold

## Input given to the fresh executor

> Apply a discount only when the order amount is at least 100; retain full price below 100.

The short task is the reproducible input for the formal plan below. This committed package does **not** establish that a particular executor received only this task, which context it had, or how long it took to derive a plan.

## Reproducible formal semantic matrix

The matrix deliberately uses the smallest domain-neutral integer cases needed to distinguish the declared threshold countermodels:

| Required meaning | Case / scalar observation | Plausible wrong implementation | Distinguishing result |
|---|---|---|---|
| Below threshold retains full price | `amount99` / `discountAccepted=No` | always discount | predicts `Yes` |
| Boundary is inclusive | `amount100` / `discountAccepted=Yes` | discount only if `amount > 100` | predicts `No` |
| Above threshold gets discount | `amount101` / `discountAccepted=Yes` | discount only if `amount == 100` | predicts `No` |
| Guard is not reversed | `amount99`, `amount100`, `amount101` | discount if `amount <= 100` | predicts `Yes`, `Yes`, `No` |
| Guard is not silently disabled | `amount100` / `discountAccepted=Yes` | never discount | predicts `No` |

The task establishes a comparison boundary, not decimal representation, rounding, negative handling, or a discount rate. Those are intentionally not acceptance criteria.

## Reproduction and result

```bash
python3 scripts/semantic_preflight.py \
  experiments/issue31-semantic-preflight/fresh-discount-plan.json
```

The formal instrument returns exit `0`, `FORMAL COHERENCE READY`, `nativeRun: false`. No native 1C, snapshot, infobase, service, GUI, or dependency is used.

## Fresh-executor chronology — unproven

Earlier discussion described two clean-context executions (an initial rejection and a later pass). This repository does not retain a durable, independently inspectable binding for either execution: executor/delegation identity, exact allowed context, verbatim report or report hash, and the then-candidate for the initial rejection. Those historical timings and verdicts are therefore **not acceptance evidence** and are intentionally not reproduced here.

The committed evidence is limited to the formal plan, its artificial receipts, and the reproducible command above. A future fresh-executor acceptance must capture a reviewable report bound to its exact task, context boundary, executor identity, full result, elapsed duration, and candidate identity before it can support an acceptance claim. This document is not automatic proof that arbitrary natural-language tasks are understood.
