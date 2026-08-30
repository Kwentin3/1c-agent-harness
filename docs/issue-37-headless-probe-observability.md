# Headless probe observability and client→server boundary (issue #37)

This note records a narrow, reproducible lesson from the interrupted native
experiments for [issue #36](https://github.com/Kwentin3/1c-agent-harness/issues/36)
and the diagnostic work in [issue #37](https://github.com/Kwentin3/1c-agent-harness/issues/37).
It describes **how to make a disposable headless probe observable**. It does
not prove the `BankReceipt` business rule, authorize a production patch, or
change the runner's task-specific-oracle boundary.

## Problem

A `run-prepared` lifecycle can successfully create a disposable file infobase
and load the configuration while still producing no runtime receipt. In the
first #36 native attempt the task-specific probe was placed *after*
`StandardSubsystemsClient.OnStart()` in `Ext/ManagedApplicationModule.bsl`.
In headless `ENTERPRISE` that standard startup did not return before the
runtime budget ended, therefore the receipt-writing code was never reached.

The important distinction is:

- `CREATEINFOBASE` and `DESIGNER /LoadConfigFromFiles ... /UpdateDBCfg` prove
  only platform acceptance of the prepared configuration;
- a terminal receipt proves only the explicitly instrumented path that wrote
  it;
- absence of a receipt is not a business RED result and cannot justify GREEN;
- a Designer load does not guarantee that a client-only instrumentation path
  will compile or execute when `ENTERPRISE` first reaches it.

A later #36 v3 attempt illustrates the last point: Designer load succeeded,
but `ENTERPRISE` exited before a receipt with
`{ManagedApplicationModule(94,36)}: Expecting ')'`. The fault was in the
throwaway probe path, not evidence about `BankReceipt`. The exact parser cause
inside that generated v3 probe remains unproven; do not turn the line locator
into a general language claim without a separate minimal reproduction.

## Confirmed headless route

Issue #37 used three fresh disposable probes, each with a new prepared tree
and file infobase. The canonical snapshot, CF, manifest, and tracked worktree
were not changed. All three probes used the same narrow entry pattern:

1. `OnStart` checks that `LaunchParameter` is nonblank.
2. The task probe runs before `StandardSubsystemsClient.OnStart()`.
3. The probe returns before the standard-startup branch.
4. `LaunchParameter` is the runner-bound path of the client receipt.

The staged probes established the following limited facts:

| Probe | Observed result | What it establishes |
|---|---|---|
| Client→server ping | terminal client receipt reported `serverResponse=pong` | early managed-client code can synchronously call an exported server-call common-module function in this disposable file-IB route |
| Server `TextWriter` | terminal client receipt plus a sibling server receipt | server-side code can write an explicit evidence path and return through that call boundary |
| Fixture stages | server stage receipt reached `bankReceipt.afterFill`; client receipt reported `serverResult=done` | the same route executed disposable Counterparty/Currency/BankAccount/SalesInvoice writes and the explicit `BankReceipt.Fill(SalesInvoice.Ref)` call |

The last probe's prepared-file closure was exactly
`Ext/ManagedApplicationModule.bsl` and
`CommonModules/JetServerCall/Ext/Module.bsl`. The common module is declared
`ClientManagedApplication=false`, `Server=true`, `ServerCall=true`. The
frozen evidence and independent review are retained under ignored `.local/`
roots and in the #37 issue thread; they are deliberately not duplicated in
tracked documentation.

This proves a **bounded execution route**, not full application startup,
interactive-client behavior, all server APIs, or correct content of a filled
document.

## Required preparation pattern

For a new headless native contract that needs a server-side document method:

```bsl
Procedure OnStart()

    If Not IsBlankString(LaunchParameter) Then
        IssueProbe(LaunchParameter);
        Return;
    EndIf;

    // StandardSubsystems
    StandardSubsystemsClient.OnStart();
    // End StandardSubsystems

EndProcedure
```

The illustrative snippet is structural, not copy-paste production code. The
probe must exist only in the writable prepared copy and must never be added to
the canonical snapshot or production patch.

For a client→server probe, keep the client and server roles explicit:

- the client opens the runner-bound receipt, invokes an exported server-call
  function, and appends observations **only after that call returns**;
- the server creates only task-owned disposable data, invokes the real target
  method, and returns observed values rather than a precomputed expected
  verdict;
- if several cases are needed, run one server call per case. A partial receipt
  can then identify the last returned case instead of collapsing many cases
  into an opaque timeout;
- an optional server-side sibling diagnostic file may help localize an
  unfinished server call, but the runner validates only its declared,
  descriptor-bound client receipt channel.

The business contract still defines the receipt schema, exact expected values,
and pass/fail interpretation. `scripts/native_cycle.py` continues to own only
process lifecycle, receipt-channel safety, process-tree cleanup, and input
identity checks.

## 1C-specific observation rules

Call the real operation under test. For the #36 shape this means
`BankReceipt.Fill(SalesInvoice.Ref)`, not assigning `BankReceipt.BankAccount`
directly. A direct assignment can make a receipt look correct while entirely
bypassing the filling code.

Observe fields that actually exist on the metadata target. In the current Jet
snapshot the `BankReceipt.PaymentDetails` row has `Document`,
`PaymentAmount`, and `Amount`; it has no `BankAccount` field. Header
`BankAccount` and payment-row observations must therefore be recorded
separately.

## Failure handling and next-contract rule

A missing/incomplete receipt, runtime timeout, early runtime exit, or
probe-compile error is a failed native attempt under its frozen contract. It
is not permission to edit that contract, rerun it, or run its GREEN phase.
Preserve the retained runner diagnostics (`result.json`, receipt/evidence,
logs and generated spec) and first establish the smallest diagnostic route
that distinguishes the failure.

A corrected probe requires a **new** frozen contract, fresh prepared roots,
and a new disposable native budget. It must state what changed in
instrumentation or observability, preserve the identity gate, and avoid
reusing results from a terminal predecessor as RED or GREEN evidence.

## Limits

- This note does not identify why the v3 generated probe had the parser error.
- It does not prove normal `StandardSubsystemsClient.OnStart()` completion.
- It does not establish business behavior for #36 or any other rule.
- It does not make `TOP 1` selections deterministic or broaden the supported
  write surface.
