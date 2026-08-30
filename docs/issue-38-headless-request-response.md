# Headless request/response: narrow baseline (issue #38)

## Decision

The retained headless interface is the smallest proven baseline:

```text
frozen request → ENTERPRISE /C receipt path → early OnStart probe
               → exported server call → client receipt + server witness
               → strict local validator
```

It is a task preparation pattern, not a permanent 1C API. Every native task still
uses a read-only canonical source, a named writable prepared copy, and a disposable
file infobase through `scripts/native_cycle.py run-prepared`.

## Frozen response contract

`scripts/issue38_protocol.py` implements `issue38-v5`.

A request contains fresh UUIDv4 `runId`, `caseId`, and `nonce`, with the fixed
`operation=serverWitness` and `requiresServer=true`. A successful client receipt
must record, in order:

1. the exact request identity;
2. `runtimeStarted`, `probeEntered`, and `serverCallIssued`;
3. `serverReached` and `caseStarted`;
4. a server-derived `businessResult`; and
5. `complete`.

The server-only witness has the same identity, server milestones, result, and
completion. Both result values must match and must differ from the request nonce.

A typed task failure is a different terminal response: it contains the identity and
reached client milestones followed by one allowed `failureClass`, optional
`failureDetail`, and `complete`; a server witness is forbidden for that outcome.

The validator rejects absent, stale, foreign, reordered, duplicate, malformed, or
post-completion records. It does not convert a runner timeout, an early runtime
exit, or cleanup failure into an application-level result.

## Normal validation step

After `native_cycle.py` has retained its evidence, validate the request and the
receipt paths explicitly:

```bash
python3 scripts/issue38_protocol.py \
  --request .local/issue38/request.json \
  --client-receipt .local/runs/native-cycle/<run>/run/evidence/receipt.txt \
  --server-receipt .local/runs/native-cycle/<run>/run/evidence/receipt.txt.server
```

The command writes one sorted JSON object to stdout and returns zero only for a
valid protocol result. A declared successful client receipt without the corresponding
server witness is rejected.

## Native evidence

On the owner-controlled HOME executor using training 1C `8.5.1.1150`, the A arm
passed one bounded harmless smoke. The request IDs were fresh; client and server
receipts contained the same server-generated UUID token; the portable validator
accepted the pair; the immutable source tree remained unchanged; and no owned 1C
process remained after cleanup.

Winner validation then proved two distinct outcomes from clean disposable state:

| Scenario | Result |
|---|---|
| Server reads `Metadata.Documents.SalesInvoice.Name` | Linked client/server receipts validate as `success` with `SalesInvoice`. |
| Server raises a fixed task exception | Client receipt validates as typed `taskException`; server witness is absent as required. |

The probes do not call `BankReceipt`, create/post business objects, or modify the
canonical snapshot, CF, manifest, or live infobase.

## Other arms

- **External EPF `/Execute`: `CONTEXT BLOCKED`.** There is no existing EPF,
  reproducible authorized export path, or supported runner seam for the exact
  training runtime. This is not a scored platform failure.
- **Test Manager/Test Client: `CONTEXT BLOCKED`.** The platform components exist,
  but there is no task-specific manager algorithm, target/test-client route, or
  bounded two-client supervisor. This is not a scored platform failure.

## Limits

The two receipts are strong evidence against accidental client-only success, but not
cryptographic writer attestation against a hostile same-UID process. This mechanism
proves only the generated task route and does not make a general write API or replace
business-specific semantic tests.
