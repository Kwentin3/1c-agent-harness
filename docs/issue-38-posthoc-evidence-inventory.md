# Issue #38: post-hoc evidence inventory

## Purpose and chronology boundary

This is an inventory of local HOME-executor artifacts retained after the native
work. It is published **after** the owner review and is not called a
pre-invocation research or protocol freeze. The frozen local protocol files show
what was used, but their earlier public publication cannot be established from
Git history; this document does not reconstruct that chronology.

The full issue goal requires a public research freeze, a public protocol freeze
before scored runs, comparable first-attempt data for viable arms, winner
selection, clean repeat, and a new bounded task scenario. Those conditions are
not met. Current verdict remains:

> **A BASELINE PARTIAL PASS / NO CLEAR WINNER**

## Exact environment declared by the retained v5 artifact

| Field | Retained value |
|---|---|
| Canonical Git input | `4ad01036cd212355d17faeba3b22145c83de1bc3` |
| CF SHA-256 | `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a` |
| Snapshot manifest SHA-256 | `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691` |
| Snapshot files | `5099` |
| Runtime | Linux training `1cv8t 8.5.1.1150` |
| Harmless smoke budget declared in v5 | one success smoke per arm, `120` seconds |
| Local v5 artifact | `.local/issue38-native-protocol/protocol-freeze-v5.json` |

The local v5 file records A, B, C and D as hypotheses and an explicit
lexicographic selection rule. It is evidence of a local freeze artifact, **not**
evidence that it was published before the first invocation.

## Native evidence that can be independently rechecked now

### A: retained non-BankReceipt metadata-read success

`tests/fixtures/issue38-a-metadata-read-v1/` is a compact copy of retained
receipt bytes from HOME executor run `run-kmqsmjkt`:

| Item | Value |
|---|---|
| Result | `SalesInvoice` |
| Client receipt SHA-256 | `598306b0bf6f06c1368f7d98e5f7f0f9ca55490912ae6ffa2333db2e823d95a6` |
| Server receipt SHA-256 | `4302239e8f9bd59774363648317968d01a8f660e5ff0abe72d23a54b7df9e608` |
| Runner status | `runtime_contract_completed` |
| Runtime / total lifecycle | `55.820 s` / `70.619 s` |
| Stable client reads | `2` |
| Prepared input before/after | identical `1da70ae1dc372a06590c3e3413db1d4f29301529bfcbaef1330f7bcd23bb1f7c` |
| Process containment after cleanup | no owned 1C/Xvfb process observed |

The client/server receipt pair binds the same retained run ID
`aced25b8-64df-40b7-9144-b312903428d2`, case ID
`34619b95-9e9c-45f4-aa7e-74e59b3dbe9e`, and nonce
`c7fced59-7ff1-404e-84f9-e26eedc1addd`. The request JSON in the tracked packet
is marked `reconstructed`: original request-file bytes were not retained. The
packet proves the linked retained receipt pair and result, not an original
request-file digest or a pre-run freeze.

### A: historical controlled failure

`run-8wqwm_cu` retained a client receipt with
`failureClass=taskException` and `failureDetail=controlled-server-task-exception`
(SHA-256 `85c47625a6722b33dd43e3c48b33f658bad6cab09ecad2866657d4c7ff3d83f5`).
It had no server failure witness because the then-local grammar allowed
client-only typed failures.

The corrected validator rejects that shape for a server-proven task exception.
Therefore this artifact is recorded as **historical old-grammar evidence only**;
it is not counted as a current task-exception pass or a winner-validation result.

## Arm accounting, without invented scores

| Arm | Native comparison status | What the retained artifacts establish | What they do not establish |
|---|---|---|---|
| A — early `OnStart` + server witness | Partial native evidence | A linked metadata-read success route and clean contained lifecycle | A tournament score, a current taskException witness, clean repeat, or winner status |
| B — EPF `/Execute` | Not scored | Repository lacked a retained EPF/build/export path and existing runner argv seam at the time of research | That `/Execute` is inferior, unsupported, or too costly; no B first attempt ran |
| C — Test Manager/Test Client | Not scored | No retained manager algorithm, client route, or bounded two-process task supervisor | That Test Manager is inferior or unsupported; no C first attempt ran |
| D — `1cecla`/native client agent | Not scored | Local research recorded absence of a task-code transport in the exact available runtime | The issue-required published comparison/disposition or a scored loss |

There is no truthful selection table with common pre-run roots, first-attempt
counts, cold setup, BSL changes, process counts, and timings for A/B/C/D. It
must remain absent rather than be synthesized post hoc.

## No-native correction made after HOLD

The tracked PR correction does not spend a new platform invocation. It:

1. rejects any unknown request key, closing the `taskInput` mutation bypass;
2. requires a matching server-authored started/failure witness for a claimed
   `taskException`;
3. adds a tested `issue38_frontdoor.py` source path which prepares a fresh request
   and two-file disposable closure, and whose `run` command delegates to the
   existing bounded lifecycle then validates the current receipts;
4. retains this compact historical packet and makes its hashes executable in
   unit tests.

## Required owner decision before another native invocation

A future comparison must first publish a new, honest research/protocol freeze
that declares exact candidate arms, roots, first-attempt budget/count, expected
cost metrics, and selection rule. The minimal decision requested is whether to
authorize one bounded B `/Execute` smoke (and its necessary disposable EPF
preparation) followed only by the contractually allowed comparison work. No
such authorization is assumed here.
