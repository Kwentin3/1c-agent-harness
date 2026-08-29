# Issue #29 canonical core-loop result

## Verdict

`FUNCTIONAL FAIL — native behavior improved, but frozen GREEN evidence contract did not pass.`

The two permitted native attempts were consumed by one RED and one GREEN `run-prepared` call. No low-level or manual 1C lifecycle was used. Native observations indicate that the production candidate rejected the tested zero- and negative-price postings before recorder movements, preserved draft saving, and preserved the tested positive multi-row case. They do **not** prove the full feature contract or the universal rule for every row. The frozen evidence cannot establish the required full GREEN:

1. `oracle.py` compares the complete RED dictionary to a partial `expected_red`, so the durable honest RED is rejected before GREEN grading.
2. The frozen GREEN expectation requires `zeroPostingErrorPresent=No` and `negativePostingErrorPresent=No`, while cancellation from a posting handler produces the observed posting exception (`Yes`).
3. The probe compares two distinct 1C `Structure` instances with `=`, which yielded `zeroBalanceUnchanged=No` and `negativeBalanceUnchanged=No` even though both rejected recorders have zero movement rows. The receipt does not emit the component balance values needed to re-grade that invariant externally.
4. A surviving last-row-only countermodel passes the entire published matrix: the zero case has one row; the mixed negative case places its invalid row second and last; and the valid case has two positive rows. The matrix therefore does not distinguish the intended all-row validation from an implementation that checks only the last row. This violates the issue requirement for an invalid row in a non-boundary position and means the universal quantifier “every row” remains unproven.

Changing the frozen probe/oracle after RED or spending a third native attempt would violate issue #29, so the result is published honestly rather than relabeled GREEN.

## Evidence chronology boundary

The local execution transcript recorded creation of `semantic-contract.md` and `oracle.py` before the first native RED and creation of the production candidate afterward. However, the contract, oracle, patches, receipts, and results were first committed together after both native runs. The runner results do not bind hashes of the contract or oracle, and no earlier Git commit or issue comment provides an independently durable content-bound freeze receipt. Therefore **pre-patch freeze chronology is independently unproven** in the published package. The package preserves the files and observations as produced, but it does not claim that an external reviewer can prove their pre-patch chronology from GitHub artifacts alone.

## Native evidence

| Attempt | Invocation | Result | Receipt SHA-256 | Key observations |
|---|---|---|---|---|
| RED | `.local/runs/native-cycle/run-h809px3g` | `runtime_contract_completed`, load result 0 | `b85f505740e18f9d35454766a0a01c55888cf47af87025353f233381b352bc60` | invalid postings succeeded and moved inventory; positive control passed |
| GREEN | `.local/runs/native-cycle/run-wd_g4sge` | `runtime_contract_completed`, load result 0 | `c5e3015a9eb1b3f8714a254281eadd72f82cd999fd13c6892f92566648a998df` | invalid drafts saved; invalid postings rejected; zero recorder rows; positive control passed; balance booleans remained untrustworthy |

Portable copies of both runner results and receipts are retained here. `production.patch` is the one-file production candidate. `instrumentation.patch` is task-only probe instrumentation. The frozen semantic contract and oracle are unchanged.

## Input and scope integrity

- base: `05cb3a5661d69f309e5d9657b312979e1a9d3a5c`
- canonical configuration: JetTr `1.0.3.1`, 5,099 files
- source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
- snapshot manifest SHA-256: `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`
- production scope: only `Documents/InventoryIncrease/Ext/ObjectModule.bsl`, seven inserted BSL lines
- common runner/front door/tests/skills: unchanged

## Budget and storage

- executor lane: 1 continuation of the original fresh executor; parent takeover 0
- front-door calls: 1
- native attempts / `run-prepared` calls: 2 / 2
- low-level/manual lifecycle: 0
- canonical repeats: 0
- original start: `2026-08-29T09:38:58Z`
- GREEN completed before `2026-08-29T09:58:50Z`; PR publication remained within 3,600 seconds
- exact disposable roots removed after portable evidence retention: `.local/prepared/issue29-core-loop`, `.local/runs/native-cycle/run-h809px3g`, `.local/runs/native-cycle/run-wd_g4sge`
- pre-cleanup logical bytes from the last complete inventory: 123,640,573; all three roots verified absent
- final measured filesystem free bytes after cleanup: 9,310,224,384

## Files

- `semantic-contract.md` — pre-production frozen contract
- `oracle.py` — pre-production frozen external oracle (intentionally retained unchanged, exits 1)
- `production.patch` — minimal candidate production delta
- `instrumentation.patch` — RED/GREEN task instrumentation delta
- `red-receipt.txt`, `green-receipt.txt` — native receipts
- `red-result.json`, `green-result.json` — compact runner-owned results
