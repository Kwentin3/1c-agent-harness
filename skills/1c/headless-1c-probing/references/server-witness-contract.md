# Server-witness receipt contract

Use this as a small transport-neutral contract for a disposable headless probe. It deliberately proves route observability only, not business correctness.

## Request

Generate fresh UUIDv4 values for every native attempt:

```json
{
  "protocolVersion": "<frozen-version>",
  "runId": "<uuid-v4>",
  "caseId": "<uuid-v4>",
  "nonce": "<uuid-v4>",
  "operation": "serverWitness",
  "requiresServer": true
}
```

Never reuse identities after a native result. Keep request values to a safe text alphabet if they are interpolated into BSL literals.

## Raw receipts

Use UTF-8, an ending newline, and exact records:

```text
key###value###Type
```

Client first records immutable identity plus:

```text
runtimeStarted###true###Boolean
probeEntered###true###Boolean
serverCallIssued###true###Boolean
```

Only after the synchronous server call returns may it append:

```text
serverReached###true###Boolean
caseStarted###true###Boolean
businessResult###<server-token>###String
complete###true###Boolean
```

The server-side writer independently emits identity, `serverReached`, `caseStarted`, the same `businessResult`, and `complete`. The token is generated in server code and must differ from the client nonce.

## Minimal evidence checklist

- Frozen request and allowed changed-path list.
- Hashes of the generated client/server probe source.
- Runner result, exact argv hash, raw client/server receipt hashes.
- Parser verdict over raw bytes, not a copied summary.
- Post-run canonical identity and no-owned-platform-process observation.

## Common pitfalls

- Do not infer server reach from a client `OnStart` receipt.
- Do not rebuild unchanged standard event-handler code; insert only the early-return branch.
- A copied canonical tree may be owner-read-only. Change permissions only on a new disposable copy.
- Pass source text directly to a review. A path or hash that reviewers cannot access is not reviewable.
- Treat a reviewer claim as a hypothesis and verify it against the exact target dialect/source before adjudicating it.
