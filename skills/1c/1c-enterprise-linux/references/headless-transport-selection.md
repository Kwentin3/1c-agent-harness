# Selecting a headless request/response transport

Use this reference before treating a headless 1C probe pattern as a permanent
harness interface. It is a **pre-native comparison protocol**, not a business
RED/GREEN contract.

## When to use it

Use when more than one transport is plausible, for example:

- early managed-application `OnStart` plus a receipt;
- an external data processor started with `ENTERPRISE /Execute`;
- Test Manager/Test Client; or
- another platform-provided client/control mechanism.

Do not assume that the most "native" mechanism wins. Compare it to the simple
baseline on the required observable product result and recurring operational
cost.

## First: freeze transport-neutral semantics

Before creating a disposable IB or launching 1C, freeze a small request and
response contract. Bind every request to fresh, never-reused identifiers:

- protocol version;
- run ID;
- case ID;
- nonce; and
- requested execution layer (for example, server required).

The response must distinguish, by evidence rather than process exit:

1. runtime started;
2. probe received control;
3. client-to-server call was issued;
4. server code was reached, when required;
5. case started;
6. task-specific result or an explicit typed failure; and
7. terminal completion.

`DESIGNER` load success, a process return code, or any pre-existing receipt is
never a business or layer-success witness.

## Prove server reach without a tautological echo

A client-visible echo of request data (such as the request nonce) does not
prove server execution: a client-side path could emit it without crossing the
boundary.

For a transport-selection smoke, use two current-run, task-owned receipts:

- **client response** records the client milestones and the returned
  server-derived token;
- **server witness** is written from the generated server-only module after it
  enters server code, and contains the same opaque token.

The token must be generated after server entry, must differ from the request
nonce, and must match exactly in both receipts. Statistically audit the
prepared source closure: the server-only module is the sole instrumented writer
of the server-witness path, client instrumentation writes only the client
response, and generated code contains no `Execute`/`Eval` or object
creation/write/posting APIs.

This is evidence against accidental or miswired harness behavior, **not a
cryptographic boundary against a malicious same-UID process or intentionally
hostile generated configuration**. State that limit explicitly; do not claim
OS-level writer attestation where client and server share the same trust domain.

## Strict, fail-closed response grammar

Choose one exact line or JSON grammar before running any arm. For a lightweight
TextWriter receipt, a practical shape is:

```
key###value###type
```

Specify the complete ordered records, literal values, and types. A typical
success response has fixed identity headers, one record for every reached
milestone, a typed business result, and exactly one terminal `complete` record.
Reject blank, unknown, duplicate, omitted, out-of-order, or post-completion
records. Require a stable completed client receipt (at least two equal reads)
before stopping the owned process.

For a typed failure response, preserve the fixed identity prefix and reached
milestones, then allow exactly one enumerated failure class and optional bounded
ASCII detail before `complete`. Never convert a silent exit into a claimed
server-call or task exception.

Useful separate classes include:

- runtime exited before probe;
- timeout with probe unobserved;
- runtime exited after probe but before case start;
- explicit server-call failure;
- explicit task exception;
- runtime exited after case start without a typed terminal result;
- timeout after case start;
- malformed response;
- stale/foreign response; and
- cleanup failure.

## Fair candidate comparison

Keep the tournament bounded:

1. Research the exact runtime and official mechanism documentation first.
   **Then run an admission preflight before freezing a scored launch:** require
   the pinned executable, immutable snapshot/manifest, required fixture, and a
   runner seam that can carry the arm's declared request and observe its required
   receipts. If any shared prerequisite is absent, classify the arm or whole
   tournament as **CONTEXT BLOCKED**. It consumes no one-smoke budget, is not a
   capability failure or a losing score, and does not justify installing an
   unpinned alternative or silently falling back to another arm. A unit-tested
   portable receipt parser proves only static contract behavior—not platform
   dispatch, server reach, or cleanup.
   Exclude a candidate only with a concrete incompatibility or scope reason;
   do not install a new service merely to keep an arm alive.
2. Freeze all viable candidates, exact roots, native budget, failure matrix and
   selection rule before the first launch.
3. Run **one** harmless, clean-state smoke per candidate. A capability failure
   is an outcome for that candidate, not permission to silently fall back to
   another transport or repair its scored attempt.
4. Give only the winner controlled failure checks and a separately frozen new
   task scenario.

For a manager/client arm, record every deliberately launched 1C client leader,
PID plus `/proc` start time, a unique run marker, and the loopback test port.
On terminal response or timeout, terminate only processes bearing that marker,
wait for port release, and record cleanup failure even if late cleanup succeeds.
Never kill an unmarked process; report it as an external collision.

## Deterministic KISS tie-break

A candidate must first meet all correctness gates: exact current-run binding,
server witness when required, task-specific result, malformed/stale rejection,
and bounded cleanup. Do not average a critical failure away.

For passing candidates, record a fixed, reproducible tuple such as:

1. temporary changed regular-file count versus snapshot;
2. added plus deleted LF-normalized BSL lines;
3. declared platform client-process leaders;
4. additional executable/service dependencies;
5. actual platform invocations; and
6. final receipt bytes.

Compare lexicographically and declare **no clear winner** if still equal.
Record wall time for transparency, but do not use a single noisy measurement as
a deciding tie-breaker.

## Evidence and containment

Keep the frozen protocol, prepared-source hashes/diff closure, request IDs,
exact argv, both raw receipts, native result, process/port scan, and target
continuity under the issue-owned `.local/` root. Re-run the project target
identity before and after each arm. Keep a later business scenario separate:
a transport smoke must not reuse a failed business contract or invoke its target
method.
