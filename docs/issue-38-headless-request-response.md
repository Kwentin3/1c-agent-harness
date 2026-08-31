# Headless request/response: A-baseline partial proof (issue #38)

## Current verdict

> **A BASELINE PARTIAL PASS / NO CLEAR WINNER**

The retained evidence proves that the narrow `OnStart → exported server call →
linked receipts` route can carry one harmless server result on the exact training
runtime. It does **not** prove that this route wins a transport tournament:
only A has native evidence, the pre-run freezes were not published before the
runs, B/C were not scored, and D has no complete public disposition.

This document is a bounded correction to PR #40, not a replacement chronology.
The exact post-hoc inventory is [issue-38-posthoc-evidence-inventory.md](issue-38-posthoc-evidence-inventory.md).
No new native run is authorized by this document.

## Current fail-closed response grammar

`scripts/issue38_protocol.py` implements the fixed `issue38-v5` request shape.
It accepts **only** these JSON keys:

```text
protocolVersion, runId, caseId, nonce, operation, requiresServer
```

`runId`, `caseId`, and `nonce` are fresh UUIDv4 strings; the only supported
operation is `serverWitness`, and `requiresServer` is `true`. An extra request
field is rejected, so a receipt cannot silently validate a request whose task
input changed after the request was frozen.

A success needs both client and server receipts, with the same request identity,
ordered milestones, matching `businessResult`, and a result different from the
nonce:

```text
client: runtimeStarted → probeEntered → serverCallIssued →
        serverReached → caseStarted → businessResult → complete
server: serverReached → caseStarted → businessResult → complete
```

There are two separate typed failures:

- `serverCallFailure` is client-only and stops exactly after `serverCallIssued`.
  A server receipt is forbidden because server reach is not claimed.
- `taskException` claims `serverReached` and `caseStarted`, so it now requires a
  matching **server-authored** receipt through `failureClass=taskException` and
  `complete`. If a detail is present, client and server details must match.

Runner create/load failure, exit before probe, timeout, stale/foreign/malformed
response, and cleanup failure remain runner evidence; a client receipt cannot
rename them into an application result.

## Reproducible A front door

`issue38_frontdoor.py` is the small, task-specific adapter around the existing
`native_cycle.py run-prepared` lifecycle. It owns only the Issue #38 request,
receipt templates and validation order; it does not create a service or change
the canonical snapshot.

Its sole prepared-tree primitive is `scripts/managed_probe_prepare.py`. That
primitive owns only technical tree lifecycle: it requires source and prepared
roots to be disjoint, atomically claims its named output root before copying, and
copies the input into that fresh `.local/prepared/` tree. It preserves the
complete managed-application module, splices the supplied early client block
after any initial `Var` declarations (including a UTF-8 BOM before `OnStart`
and `//` inside quoted string literals),
appends the supplied server block, checks that exactly the two declared BSL files
changed, freezes the copy, and performs safe explicit discard. A collision at an
existing output is refused without deletion; failure cleanup applies only after
this primitive has claimed the output. If preparation and cleanup both fail, the
reported error carries both causes. It rejects unsafe path/symlink components
and missing `ServerCall=true` metadata. Its bounded token scan is input hygiene,
**not** a proof that arbitrary supplied BSL has no business effect; the Issue
#38 adapter and its semantic task contract own that meaning. The front door does
not implement a second copy/splice/freeze path.

`prepare` is non-native: it creates a fresh request outside the input tree and
asks that primitive to create the named disposable prepared tree. Every relative
`--input-tree`, `--prepared-tree`, and `--request` path is interpreted relative
to `--repo-root`, never the caller's current directory. A standalone prepared
tree is retained only until its caller explicitly discards it; use:

```bash
python3 scripts/issue38_frontdoor.py discard \
  --repo-root . \
  --prepared-tree .local/prepared/issue38-a-next
```

The resulting closure changes only these two BSL files:

```text
Ext/ManagedApplicationModule.bsl
CommonModules/JetServerCall/Ext/Module.bsl
```

The generated client probe receives the runner's `/C` receipt path, crosses to
`JetServerCall.Issue38ServerWitness`, and the server function writes the sibling
`<receipt>.server` witness before returning its token. The fresh request identity
is embedded as safe literals in this disposable probe closure; it is never
inserted into canonical source.

```bash
python3 scripts/issue38_frontdoor.py prepare \
  --input-tree .local/runs/training-jet-review-final/snapshot \
  --prepared-tree .local/prepared/issue38-a-next \
  --request .local/issue38-next/request.json
```

The `run` form performs that preparation, invokes the existing bounded
`native_cycle.py run-prepared` (`120` seconds, `complete###true`), accepts a
runner JSON object only, and reads receipts only from a regular, non-symlink
`.local/runs/native-cycle/run-*` invocation root. It then calls
`validate_terminal`. It discards the prepared tree on every terminal runner,
receipt, timeout, validation, and success path; a cleanup failure is returned
explicitly rather than suppressed. The standalone request file is retained as
run evidence and is never silently deleted:

```bash
python3 scripts/issue38_frontdoor.py run \
  --repo-root . \
  --input-tree .local/runs/training-jet-review-final/snapshot \
  --prepared-tree .local/prepared/issue38-a-next \
  --request .local/issue38-next/request.json
```

**Do not run the second command while the owner HOLD is active.** It exists so a
future separately authorized A run has one clear `request → disposable 1C →
validated response` entry point rather than a post-hoc checker.

## Compact retained A evidence

`tests/fixtures/issue38-a-metadata-read-v1/` contains Base64-encoded exact retained
receipt bytes from `run-kmqsmjkt` and a compact result summary. The original request JSON
was not retained, so `request.reconstructed.json` is explicitly reconstructed
from the retained identity fields and generated probe; it is not presented as a
pre-run request artifact.

The test checks both receipt SHA-256 values and validates the real linked pair:

```bash
python3 -m unittest \
  tests.test_issue38_protocol.Issue38ProtocolTests.test_retained_a_success_packet_validates_and_keeps_remote_hashes -v
```

It yields `{"status":"success","serverToken":"SalesInvoice"}`. This proves
one bounded server metadata-read result, not a general business API or a winner.

## Limits and next owner decision

- A controlled historical `taskException` receipt was client-only under the old
  grammar. It is **not** accepted as a server-proven task exception by the
  corrected validator and is retained only as historical evidence.
- B (`EPF /Execute`) and C (Test Manager/Test Client) are unscored prerequisites,
  not platform failures. Their build/supervision cost must be measured only in a
  future authorized comparison.
- D (`1cecla`) was locally excluded from the exact runtime but was not carried
  through the required public research comparison. It cannot be silently treated
  as a tournament loss.
- No integration winner, no clean repeat, and no closing claim exist yet.

The next legitimate product decision is whether to authorize one bounded B smoke
with a published research/protocol freeze and, if comparison becomes possible, a
clean repeat of the selected arm. That decision is intentionally left to the
owner.
