# Fresh no-native acceptance — discount threshold

## Input given to the fresh executor

> Apply a discount only when the order amount is at least 100; retain full price below 100.

The executor received only that task and the `semantic-contract-testing` skill before it derived the challenge. It did not read existing `fresh-*` artifacts or semantic-preflight tests until its independent model was frozen.

## Independent semantic challenge and amendment

The first clean run took **288,906 ms** end-to-end and returned `CONTRACT BLOCKED` for semantic acceptance: the then-candidate promoted decimal representation/precision even though the task did not establish it. The amendment deliberately returns to the smallest domain-neutral integer matrix from that review:

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

A final independent clean-context executor then derived the same minimal authorized matrix before reading these artifacts: `99 → No`, `100 → Yes`, `101 → Yes`. It passed the amended plan in **389,501 ms** end-to-end, with no findings or surviving countermodels. Its frozen boundary excluded decimal precision, rounding, negative values, discount amount, and an upper cap as unstated requirements.

This records an independent no-native semantic challenge and its amendment. It is evidence that the agent step is observable and correctable; it is not an automatic proof that arbitrary natural-language tasks are understood.
