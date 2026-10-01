# Issue #78 — compact model-facing diagnostic responses

## Boundary

The companion contract is unchanged. It still returns the complete JSON response,
and the plugin still validates `capabilityVersion` and `artifactId` before doing
anything else. Only then, for the three diagnostic operations, the plugin may build
a compact copy for the model. Coding tools and the retained TechLog selection are
not changed.

Compaction is fail-closed. It applies only to known response shapes with
`status=ok` and no `partial=true` or `complete=false` marker at any nested level.
Blocked, unavailable, partial, compatibility-error and unknown response shapes are
returned unchanged. Page truncation remains visible and is not treated as source
incompleteness.

## Representation

Successful complete diagnostic responses keep `status=ok` but omit the already
validated model-facing delivery passport: `artifactId`, `capabilityVersion`,
`schemaVersion` and `operation`. Those fields remain in the companion response and
both matching release manifests.

For a page with at least two groups, only fields present with exactly equal values
in every group may move to `groupCommon`. The response says that these fields apply
to every item in `groups`. The same fixed, non-recursive rule produces
`recordCommon` for every item in `records`, or for every item in `before`, `record`
and `after` on an exact-record response. Missing fields never equal null or empty
fields. Different values stay on their original items.

Example group page:

```json
{
  "status": "ok",
  "groupCommon": {
    "event": "EXCP",
    "countScope": "retainedFilteredSelection",
    "summary": {"meaning": "File not found '<redacted:path>'"}
  },
  "groupCommonAppliesTo": "every item in groups in this response",
  "groups": [
    {"count": 5, "errorSignature": "hmac-sha256:first", "ref": "snapshot:…:group:EXCP:first"},
    {"count": 1, "errorSignature": "hmac-sha256:second", "ref": "snapshot:…:group:EXCP:second"}
  ],
  "groupsTruncated": true
}
```

The full callable refs, signatures, fingerprints, individual times, selection
indexes and record identities remain. `sourceTimeToken` also remains because it may
contain more than six fractional digits even when `occurredAt` does not. Redaction,
truncation, TTL/stability, coverage, filters, source window/timezone, count scope
and neighbor scope/relation stay explicit on every applicable response.

## Time instruction

`one_c_observe` continues to accept source-local calendar timestamps without `Z`
or a numeric offset. When a discovery timestamp is reused for the same reported
`sourceTimeZone`, the agent keeps its calendar date/time and every fractional digit
and omits only the offset. This is not a general instruction to strip an offset
from a timestamp expressed in another timezone.

## Verification and measured result

The adapter tests cover exact reconstruction of common plus individual fields,
heterogeneous and empty pages, nested partial coverage, blocked and unknown forms,
compatibility blockers, full refs, distinct signatures/fingerprints, exact-record
neighbor scope and `sourceTimeToken` values with more than six fractional digits.
Existing TechLog fixtures continue to cover partial file inventory and visually
similar but distinct events.

The implemented transformation was replayed offline over the same nine saved
registered-tool responses used by the #78 R&D. Both sides use sorted compact JSON,
UTF-8 and one final newline:

| Response | Existing bytes | Implemented bytes |
|---|---:|---:|
| discovery | 527 | 363 |
| blocked timestamp request | 283 | 283 |
| broad observation | 1,980 | 1,509 |
| group page, offset 2 | 1,815 | 1,333 |
| refined observation | 2,004 | 1,533 |
| records page | 2,165 | 1,515 |
| exact record and neighbors | 3,061 | 2,126 |
| group page, offset 4 | 2,453 | 1,576 |
| group page, offset 20 | 1,736 | 1,537 |
| **Total** | **16,024** | **11,775** |

The reduction is 4,249 UTF-8 bytes, or 26.5% of this compared response layer. It is
not a token, cost or whole-run measurement. The blocked timestamp response remains
unchanged, and no reduction in call count is claimed by this offline replay.

The three description strings grow from 485 to 797 serialized UTF-8 bytes (+312)
to state common-field and timestamp semantics. The bundled skill shrinks from
2,832 to 2,290 file bytes (-542). These figures are separate from the response
percentage; the acceptance run did not load the bundled skill.

This is offline replay, not user acceptance. Deployment, restart and a new ordinary
Hermes chat require separate authorization.
