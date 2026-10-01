# Issue #55: SupplierInvoice supplier document number

## Scope and result

This is a retained, bounded JetTr `1.0.3.1` write experiment, not a deployed
configuration change or universal write support.

The task required a supplier document number for posting and prohibited a second
posted document for the same supplier and exact stored number. Draft saving,
a different supplier with the same number, and reposting the same document were
preserved. The global document lock is a deliberately conservative serialization
choice for this slice, not a proven production throughput design.

Historical source and budget: [issue #55](https://github.com/Kwentin3/1c-agent-harness/issues/55).
The owner's **ACCEPT / COST FAIL** remains unchanged; finalization does not
reset the native-run ledger, budget or first-pass history.

## Artifacts and evidence boundaries

- `exact-production.patch`: production candidate, immutable at finalization;
  document attribute/form and guard at the start of `Posting`.
- `exact-instrumentation.patch`: test observation/runner code, not production.
- `request.json`: retained request identities, not a new invocation.
- `receipt.json`: retained native result, client/server bytes and hashes, patch
  hashes, prepared/frozen/runner identities and automatic-cleanup report.
- `oracle.py`: local validator, strengthened after the native run.

The saved server receipt explicitly records `draft_blank`, `missing_number`,
`first_same_supplier`, `duplicate_same_supplier`, `same_number_other_supplier`,
`repost_same_document`, `existing_behavior`, rejected-case `movement1..4`, and
per-job `concurrent.{a,b}.succeeded/movement1..4` plus `posted_count`.

Current unit tests verify request canonical serialization, client/server exact
bytes/SHA-256 and both patch hashes. The two-job witness is bound per job:
exactly one winner with one movement in each of the four declared registers,
and one loser with zero movements. Unknown Boolean strings fail closed. The
exact historical receipt still passes; no receipt/result hash is regenerated.

This is a **retained-evidence replay**, not a fresh 1C run. Canonical source,
prepared/frozen tree hashes and cleanup are historical recorded claims; the
source trees have not been reopened or independently rehashed in this pass.
The receipt is narrow: it does not independently observe all sequential
positive-case movement counts, errors' precise rejection causes, the persisted
state of the saved draft, or the `existing_behavior` Boolean in depth.
These limitations must not become a universal business/atomicity claim.

## Adjudication of earlier source review

The patch modifies `Posting`, not `UndoPosting`. The platform documents separate
handlers: [Using the Posted field and the posting process](https://1c-dn.com/library/using_the_posted_field_and_the_posting_process/).
Therefore "this Posting guard necessarily prevents unposting" is unsupported.
Unposting was not separately exercised by the retained business probe; no new
unposting PASS is claimed. Direct register writes or direct manipulation of the
Posted field are also outside this task's documented posting entry point.

The broad document lock is an accepted bounded trade-off, not a request for a
new information register or a speculative refactor. Formatting/normalization of
supplier numbers, migration of previously posted documents, sustained-load
behavior and production installation remain outside the proven slice.

## Reproduce without platform or source changes

From repository root:

```sh
python3 -m unittest tests.test_issue55_evidence -v
```

This decodes the retained packet into disposable temporary files, invokes the
current oracle and checks four concrete false-PASS mutations. It does not invoke
1C, SSH, the shared task runner or change original/snapshot/live IB bytes.
