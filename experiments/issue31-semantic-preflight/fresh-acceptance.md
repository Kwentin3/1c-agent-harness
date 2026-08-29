# Fresh no-native acceptance — discount threshold

## Input given to the agent

> Apply a discount only when the order amount is at least 100; retain full price below 100.

No source code, issue #29 fixture, or existing positive control was used as the business-rule input. The resulting plan is [`fresh-discount-plan.json`](fresh-discount-plan.json).

## Agent semantic challenge

| Required meaning | Clause and task quote | Case / scalar observation | Plausible wrong implementation | Distinguishing result |
|---|---|---|---|---|
| Boundary is inclusive at 100 | `threshold`: “only when the order amount is at least 100” | `amount100` / `discountAccepted=Yes` | `amount > 100` | predicts `No` |
| Values below 100 preserve full price | `preservation`: “retain full price below 100” | `amount99` / `discountAccepted=No` | always-discount | predicts `Yes` |

The task quotes are verbatim substrings of the short task. Both clauses have observation and case coverage; no established-domain source is claimed. The two countermodels are explicit, plausible, and each differs from GREEN in one retained case. This is an agent-authored semantic challenge; the CLI checks its formal data, not natural-language correctness.

## Reproduction and result

```bash
python3 scripts/semantic_preflight.py \
  experiments/issue31-semantic-preflight/fresh-discount-plan.json
```

Observed result: exit `0`, `FORMAL COHERENCE READY`, `nativeRun: false`.

**Semantic acceptance:** `PREFLIGHT PASS / KISS PASS` for this prepared task-to-contract challenge. The full route — reading the short task, constructing the challenge and plan, and running the formal checker — had no native 1C attempt, dependency, service, GUI, snapshot, or infobase creation. It is evidence that the required agent step is usable; it is not an automatic proof that arbitrary natural-language tasks are understood.
