# Managed-client probe compile hardening

Use this before a business native cycle when a prepared configuration adds code to
`ManagedApplicationModule` and a server-call common module.

## Why this gate exists

Designer `/LoadConfigFromFiles` can succeed while Enterprise later compiles a reachable managed-client
branch and exits before a receipt. A missing receipt is a runner failure, not a business RED result.
Audit **all** added client/server callables, not only the expected success route: client code may be
compiled before an `Except` branch is ever executed.

## Exact-runtime observations (Jet training 8.5.1.1150)

Two separate probes exited before their first receipt because error-reporting helpers copied into the
managed-client module were not safe on that exact route:

- `ErrorDescription(ErrorInfo())` produced a managed-module syntax diagnostic.
- `Chr(13)` / `Chr(10)` produced `Procedure or function with the specified name is not defined (Chr)`.

These facts do **not** define a platform-wide ban on those names. They mean that a new probe must not
assume a helper is available merely because Designer accepted the source or because it is familiar in
another 1C context.

## Exact-runtime startup-bypass observation (Jet training 8.5.1.1150)

A disposable canary initially reached `ENTERPRISE` but exited with
`{ManagedApplicationModule(62,36)}: Error in expression`. On that exact target,
line 62 was the unchanged standard call `StandardSubsystemsClient.OnStart()`.
The failure was isolated by placing the complete `/C`-gated canary branch **at the
start** of `ManagedApplicationModule.OnStart`, then writing its client pre-call
receipt, synchronously calling an exported `ServerCall=true` common-module
function, appending the returned server-generated UUID token and terminal marker,
and executing `Return` **before** the standard-startup call. The harmless canary
then completed with matching client/server receipts and a fresh UUID distinct from
the request nonce.

This is a narrow transport observation, not a business-route proof. Keep the
standard tail unchanged. In review packets, include the exact added BSL or a real
added-code diff, not only self-reported hashes/static-scan output. The unchanged
standard module may contain `Execute(...)` after the early `Return`; distinguish
that baseline code from forbidden primitives in the added probe block.

## Safe preparation pattern

1. Start from the smallest prior exact-runtime-proven `OnStart → exported server call → receipt`
   shape.
2. List every added callable and every callable it invokes, including `Try`/`Except` error branches.
3. In receipt/error paths, prefer fixed ASCII-safe labels such as `client-error` and `server-error`.
   Do not serialize platform exception text unless the exact helper path has its own proof.
4. Static-scan the complete prepared diff for forbidden or unproven primitives before freeze. Review
   the full module, not a hand-selected excerpt.
5. If the complete skeleton is new, freeze one harmless compile-canary first: no business objects,
   no `BankReceipt.Fill`, no production change, one bounded disposable run, and exact receipt rows
   for client entry, server success, handled server failure, completion, input identity and cleanup.
6. Only after that can a separate business contract use the proven skeleton. Do not consume its RED
   or GREEN attempt on compile-hygiene discovery.

## Failure handling

If the canary exits before receipt, retain its log/result and report the exact compiler locator.
Do not retry or run the business GREEN under that contract. A future contract may use a corrected
skeleton only after a fresh review and budget are frozen.
