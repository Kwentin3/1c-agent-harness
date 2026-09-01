# Issue #38: corrected-head native readiness report

## Decision

> **PRODUCT ROUTE NOT READY**
>
> The current A front door reached the 1C client→server probe and produced a
> linked receipt pair, but the existing runner did not accept the receipt as a
> completed run. This is an integration failure at the terminal-marker boundary,
> not a native protocol PASS.

This report records the owner-authorized post-freeze correction and one native
smoke. It does not rescore the earlier transport comparison, authorize another
run, or change the Issue #38 protocol.

## Exact identities and scope

| Item | Value |
|---|---|
| Base candidate, PR #42 | `8d317c79c589290e1817e177b1cda12bebce811c` |
| Corrected candidate, PR #44 | `e2c104b95cd31c431135b7e2d13ae2574134e6eb` |
| Corrected tree | `43c47549d3afbe44d301baf7c138db973a25548a` |
| Runtime | training `1cv8t 8.5.1.1150` |
| Runtime SHA-256 | `0d11379cfd37c029a472fa500cbd8a64050cc5e53f7904036f8f6ce6a7fe0574` |
| Canonical target | JetTr `1.0.3.1` |
| Snapshot continuity | 5,099 files; manifest `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691` |

The owner authorized only one adjacent-script repair: make
`issue38_frontdoor` pass the prepared input to `native_cycle run-prepared` as a
repository-relative path. `native_cycle` retained its strict rejection of
absolute and escaping input paths.

The regression uses the real copied `native_cycle.py`, a task-owned fake
`xvfb-run`, and a non-executable placeholder `1cv8t`. It REDs on the frozen
head as `precheck_failed`; on the corrected head it crosses the real input-path
precheck and reaches a controlled `create_failed` without launching 1C. See
`tests/test_issue38_protocol.py`:
`test_frontdoor_run_handoffs_repo_relative_prepared_tree_to_real_runner_precheck_without_1c`.

Non-native checks on the corrected head:

- focused Issue #38 protocol and preparer suite: 60/60 PASS;
- full repository suite: 231/231 PASS;
- `py_compile` relevant scripts, `skills/manifest.json` JSON parse, and
  `git diff --check`: PASS;
- GitHub CI: Python 3.9 and 3.12 PASS.

The authorizing checkpoints and raw terminal receipt are retained in GitHub:

- [owner repair/native authorization](https://github.com/Kwentin3/1c-agent-harness/issues/38#issuecomment-5490985475);
- [owner safe synchronization authorization](https://github.com/Kwentin3/1c-agent-harness/issues/38#issuecomment-5491290381);
- [PR #44 corrected-head checkpoint](https://github.com/Kwentin3/1c-agent-harness/pull/44#issuecomment-5491417096);
- [Issue #38 terminal receipt](https://github.com/Kwentin3/1c-agent-harness/issues/38#issuecomment-5491542632).

## What the one authorized native smoke proved

The smoke used a fresh request and clean issue-owned roots:

```text
prepared: .local/prepared/issue38-e2c104b-smoke
evidence: .local/issue38-native-e2c104b/smoke
runner:   .local/runs/native-cycle/run-x57juccp
```

The request bound fresh values:

```text
runId:  77f4f6b4-0b21-4807-b657-b778ce70c252
caseId: a4b34a0e-1b2d-4e7c-abdd-ed21fe52e2bb
nonce:  0664f8a5-2ab5-4a28-af16-562675df6267
```

`CREATEINFOBASE` and `DESIGNER /LoadConfigFromFiles /UpdateDBCfg` both passed
with `DumpResult=0`. The generated client receipt and server witness contain
matching current `runId`, `caseId`, `nonce`, and a server-generated token
`e5fa6d64-b0fc-4268-8235-9032b8d6b77e`, different from the nonce. The portable
Issue #38 validator accepts the copied pair.

This supports a narrow fact: the disposable configuration started, the probe
received control, the client crossed to the server-only module, and that module
returned a token which appeared in both retained receipts.

## Why the smoke is not a PASS

The runner returned:

```text
status: runtime_timeout
failedStage: runtime
error: runtime completion marker not observed within 120s
processReturn: -15
```

The runner input marker is the literal `complete###true`
(`scripts/issue38_frontdoor.py`, `_COMPLETE_MARKER`; passed at
`_native_command`). The generated receipt's last record is instead
`complete###true###Boolean` (`_client_probe` and `_server_probe`). The
portable protocol validator correctly requires the typed three-field record
(`scripts/issue38_protocol.py`, `_validate_receipt`). But the generic runner
compares the final physical line against its supplied literal
(`scripts/native_cycle.py`, `_receipt_diagnostic` and `run_runtime`).

Therefore the receipts became useful evidence only after the runner had timed
out and stopped the owned process. The host validator cannot retroactively turn
that runner result into an accepted end-to-end success.

This is a confirmed boundary mismatch, not an inference from process exit:

```text
Issue #38 front door owns receipt template and chooses marker
        ↓ supplied marker: complete###true
native_cycle owns literal completion observation
        ↓ physical final receipt line: complete###true###Boolean
Issue #38 protocol owns typed receipt validation
```

## Cleanup and limits

After the smoke:

- the owned prepared root was absent;
- `1cv8t` and `Xvfb` were absent;
- the canonical target remained `ready` with the pinned manifest;
- the executor was a clean detached checkout at `e2c104b…`;
- the repeat roots were absent and invocation 2 did not start.

One top-level native invocation was used. The second authorization was only for
a clean repeat after a full first PASS, so it remains unused rather than being
repurposed as a retry after this failure.

This report does **not** prove:

- a repeatable native protocol route;
- that the generic runner accepts the typed Issue #38 terminal receipt;
- a selected transport winner;
- Issue #43 readiness or any business behavior;
- permission to merge PR #42/#44 or close Issue #38.

## Product interpretation

The product consumer is not the 1C end user. It is the harness/agent that needs
one reliable answer to a bounded request:

```json
{"status":"success","serverToken":"server-generated value"}
```

The required chain is:

```text
1C receipts → runner accepts completion → front door validates receipts → agent reads JSON → owner sees a short report
```

The smoke demonstrates that the first and much of the third link can work. It
does not establish the middle link, so the agent cannot safely treat a later
receipt file as a success when the runner has reported timeout.

## KISS proposal for a future owner decision

### Recommended minimal repair

Authorize a fresh, separate post-failure correction only if the goal remains to
make A a reproducible product front door:

1. Change the Issue #38 front door's supplied completion marker to the exact
   existing terminal record, `complete###true###Boolean`.
2. Add one direct regression proving that the literal passed to `native_cycle`
   is also the final literal produced by the Issue #38 client probe.
3. Keep `native_cycle` generic: it continues to compare one caller-supplied
   literal and does not parse Issue #38 rows or accept multiple forms.
4. Freeze a new native budget; do not reuse the unspent repeat authorization.

This is KISS because it removes the only duplicate definition of terminal
completion. It introduces no new transport, protocol version, response format,
runner parser, service, or framework.

### Rejected alternatives

| Alternative | Why not now |
|---|---|
| Teach `native_cycle` the Issue #38 typed grammar | It makes a generic lifecycle runner own an issue-specific protocol. |
| Let runner accept both short and typed markers | It creates two valid completion grammars and hides future mismatches. |
| Add a second final line just for runner | It adds a second completion signal and makes the typed validator and runner disagree about what is authoritative. |
| Treat post-timeout host validation as PASS | It weakens the runner/cleanup contract and accepts evidence produced outside the runner's accepted terminal state. |
| Spend the remaining repeat authorization | The owner made it conditional on a first full PASS; this smoke was not one. |

## Minimal future gate

The smallest owner question is:

> Authorize the one-literal front-door completion-marker correction, one
> cross-boundary regression, and one new clean native smoke budget; keep runner,
> protocol grammar, BSL probe semantics, Issue #43, merge, and transport choice
> out of scope.

Until such a decision, the correct status is **PRODUCT ROUTE NOT READY**.
