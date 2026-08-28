# Issue #23 stage 1 — frozen pre-patch semantic contract

Status: **frozen before production metadata/BSL, probe, or native execution**. This document is the one stage-1 artifact. Amendments must be additive and must not rewrite this freeze.

## 1. Received-information and authority boundary

The original fresh-executor lane received live issue #23, repository `main` at `ac673ff6ed2542452767983395fb635396d61282`, and published repository docs/skills; it received no unpublished task patch, probe, oracle, or selected feature. This bounded continuation additionally received the complete prior fresh-research transcript at `/data/hermes-home/cache/delegation/live/deleg_265da076/task-0.log`, which contained candidate reconnaissance but no selection or task-specific solution. This continuation independently reread live issue #23 and reopened every material source range cited below.

- `ownerInterventions=0`. Coordinator instructions that preserved the already-delegated scope did not supply business semantics, 1C commands, hashes, or a solution.
- Derived without owner help: immutable source binding, candidate choice, business boundary, countermodels, observations, future RED/probe boundary, and preservation scope.
- Stage-1 prohibitions observed: no production metadata/BSL, probe, native 1C, runner/skill/snapshot change, push, or GitHub comment.

## 2. Immutable source binding and exact locators

The source of truth is the immutable hierarchical snapshot rooted at `.local/runs/training-jet-review-final/snapshot`, addressed below only by snapshot-relative paths.

- snapshot manifest SHA-256: `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`
- source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
- closure at freeze: 5,099 declared and actual files; missing/mismatch/extra/symlink/writable files all `0`

Material source files and frozen SHA-256 values:

| Snapshot-relative source | SHA-256 | Exact inclusive locator and fact |
|---|---|---|
| `Documents/SalesInvoice.xml` | `2aadf05f9fc93e482fc6a450d914b58a2f657162a341757d547d4da07b9ef27a` | `216-226`: posting is allowed and declares four accumulation-register record sets. `252-299`: header-attribute container and the `Customer` reference. `1017-1067`: final existing header attribute, then forms/tabular-section boundary. |
| `Documents/SalesInvoice/Ext/ObjectModule.bsl` | `535bbbee743a15a92d536c824dd2b69418f6e1d0429b31d9f0b9ca2084a65611` | `14-27`: server `Posting` entry point and existing early EDI refusals. `29-54`: initialization, four movement paths, record-set write, and negative-balance control. `74-82`: `BeforeWrite` currently only preserves exchange-load behavior and derives `Total`. |
| `Catalogs/Counterparties.xml` | `54887809b84ef3ad51bef2bead01998c9dada12af89e4b447017b0aac281ed6a` | `399-487`: attribute container and existing item-level `Customer`/`Supplier` Boolean attributes, the metadata seam considered by candidate B. |

Direct content checks over those exact frozen bytes found neither `PaymentDueDate` nor `SalesBlocked`. Prior task distinctions are also explicit in tracked evidence: `experiments/issue14-business-rule-20260827/README.md:7-10` is an every-row positive-quantity posting guard; `experiments/issue18-sales-invoice-calculation-20260827/README.md:7-9` is server-side row amount derivation/normalization.

## 3. Candidate comparison and KISS decision

Both candidates are meaningful metadata+BSL changes grounded in the locators above.

| Candidate | Metadata + behavior | Positive / negative / preservation shape | KISS assessment |
|---|---|---|---|
| **A — selected: `SalesInvoice.PaymentDueDate`** | Add one optional date-only attribute to `SalesInvoice`; at server posting, reject an entered due date whose calendar date precedes the invoice calendar date. | Later/same-day due date posts; preceding-day due date remains a draft; blank due date follows the existing route. | One business object, one metadata file, its existing object module, no lookup/query/new object. Object-level temporal consistency is distinct from #14 row quantity and #18 amount normalization. |
| **B — rejected: `Counterparties.SalesBlocked`** | Add one Boolean to `Counterparties`; reject posting a `SalesInvoice` whose referenced customer is blocked. | Unblocked customer posts; blocked customer remains draft; supplier/customer flags remain otherwise unchanged. | Meaningful, but crosses catalog write/read and document posting boundaries, requires an additional counterparty state fixture and correct customer-vs-supplier interpretation, and couples two objects. It offers no necessary capability over A for this gate. |

Decision: choose A. B is rejected only by KISS and bounded test cost, not as meaningless. A remains optional rather than mandatory so existing invoices are not newly rejected merely because the attribute did not previously exist.

## 4. Frozen business statement and semantic model

**Business statement:** A sales invoice may record an optional payment due date. When an unposted `SalesInvoice` is posted through the server object lifecycle, an entered `PaymentDueDate` must be on or after the calendar date of the document's standard `Date`; otherwise posting is refused atomically. Blank means “unspecified” and does not add a refusal.

For only the new issue-23 gate:

```text
Issue23AllowsPosting(d) ⇔
    IsEmpty(d.PaymentDueDate)
    OR BeginningOfDay(d.PaymentDueDate) >= BeginningOfDay(d.Date)
```

All pre-existing posting gates still apply independently.

- **Subject/domain:** one persisted, unposted `DocumentObject.SalesInvoice` and its new optional `PaymentDueDate` attribute, whose metadata type is Date with date-only fractions.
- **Quantifier:** object-level, exactly one due-date value; no tabular-row or aggregate quantifier.
- **Predicate/boundary:** blank is allowed; otherwise compare calendar dates. Same calendar day is included. Time-of-day cannot make a same-day value invalid.
- **Operation scope:** direct server `Posting` of an already saved draft. Draft save must remain possible even when the date is earlier, so refusal is specifically observable at posting. UI/form checks, `Filling`, `BeforeWrite`-only enforcement, imports, and client-only handlers are not substitutes.
- **Failure and persisted state:** an earlier-day case returns from the posting attempt with the document still persisted as `Posted = false`; the entered `PaymentDueDate` remains persisted and rereads unchanged.
- **Atomicity/side effects:** the failed attempt creates zero recorder movements in `Sales`, `CustomerBalance`, `InventoryInWarehouses`, and `InventoryCost`; paired before/after balances and aggregates are unchanged. No partial record-set effect may survive.
- **Preservation:** blank, same-day, and later-day values do not alter the pre-existing posting route or movement/balance vector. Existing failures such as insufficient stock remain failures. No default due date, date mutation, or change to `Total`, inventory rows, customer, warehouse, currency, VAT, or EDI fields is authorized.
- **Unknown/out of scope:** forms/UI presentation, user-facing wording/localization, migration of existing production data, extensions, exchange-load behavior, copy/fill defaults, undo posting, reposting an already posted document, concurrent edits, deployment, and non-Jet/platform portability. Successful native disposable-IB evidence will not establish production readiness.

## 5. Allowed implementation envelope

The future production delta may add exactly the `PaymentDueDate` attribute in `Documents/SalesInvoice.xml` and a minimal server guard in `Documents/SalesInvoice/Ext/ObjectModule.bsl` at the `Posting` entry point before movement preparation/writes. Equivalent minimal BSL that satisfies every observation is allowed; the contract does not freeze code spelling.

Not allowed: new objects, forms, roles, integrations, common modules, runner/framework changes, automatic defaulting, broad refactors, or weakening existing posting gates. Expected production-file count is exactly `2`; harness/skill changes are `0`.

## 6. Materially plausible wrong implementations

| ID | Counterimplementation and why plausible | Distinguishing observation/case |
|---|---|---|
| C1 | **Metadata-only:** the attribute exists and persists, but posting ignores it. This is the easiest half-change. | N1 and N2 must save as drafts but fail posting atomically. |
| C2 | **BSL-only:** a guard is added without the metadata attribute, or checks another existing field. | M1 requires platform-visible `SalesInvoice.PaymentDueDate`, date-only type, write, and reread; source-baseline metadata lookup remains absent without breaking load. |
| C3 | **No-op/dead guard:** both files change, but the condition is unreachable or never sets refusal. | N1/N2 posting state and zero side effects. |
| C4 | **Hard-coded fixture/stale receipt:** reject one known date/ref or emit expected constants instead of observing current state. | N1 and N2 use fresh distinct document refs and two dynamic date deltas; all receipts bind the current run nonce/ref, and the external oracle queries persisted state/movements rather than trusting probe verdict words. |
| C5 | **Wrong entry point:** UI, form, `Filling`, or `BeforeWrite` rejects/changes the value, while direct server posting bypasses it. | N1/N2 draft writes must succeed and reread the entered value; only the subsequent direct server post fails. |
| C6 | **Full-timestamp comparison:** midnight due date is compared with a noon document timestamp and incorrectly rejected. | B1 uses the same calendar day with due time at day start and must post. |
| C7 | **Current-date comparison:** an otherwise valid historical invoice is rejected because its due date is before runtime “today.” | P1 is derived from recorded run date, remains historical, and must post because it is later than the document date. |
| C8 | **Wrong blank/boundary direction:** blank is required/rejected, same-day is excluded, or later dates are rejected. | R1 blank, B1 same-day, and P1 later-day all post and preserve the value. |
| C9 | **Late refusal/partial effects:** cancellation happens after record-set work and leaks movements/balance changes. | N1/N2 require `Posted=false`, zero recorder movements in all four declared registers, and exact paired balances. |
| C10 | **Candidate confusion/wrong object:** `SalesBlocked` or `PaymentDueDate` is added to `Counterparties`, while `SalesInvoice` lacks the selected field. | M1 inspects the `SalesInvoice` metadata object and persists the value on the invoice itself. |

No finite fixture excludes malicious test-aware code. The claim is limited to materially plausible implementation mistakes; current-run identities, dynamic relative dates, persisted-state queries, and an expectation-free probe prevent the realistic constant/stale variants.

## 7. Clause → observation → minimal future cases

All document dates are derived from the platform run date `R = BeginningOfDay(CurrentDate())`, and the receipt records concrete values and types. Cases use otherwise equivalent valid invoice data unless explicitly marked.

| Case | Input | Required observation | Clauses/countermodels killed |
|---|---|---|---|
| M1 metadata/persistence | Inspect metadata by string; in GREEN write a fresh invoice with a nonblank due date and reread it. | Attribute exists on `SalesInvoice`, has date-only Date type, and exact value survives write/reread. | metadata meaning; C2, C10 |
| P1 later/historical positive | `Date = R-10 days + 12h`; `PaymentDueDate = R-9 days`. | Draft saves; post succeeds subject only to existing gates; `Posted=true`; due date unchanged; non-issue movement/balance vector matches R1. | predicate positive; C7, C8 |
| B1 exact boundary | `Date = R-10 days + 12h`; `PaymentDueDate = R-10 days` at day start. | Same observations as P1. | inclusive calendar-day boundary; C6, C8 |
| N1 negative | `Date = R-10 days + 12h`; `PaymentDueDate = R-11 days`. | Draft saves/rereads; direct post fails; `Posted=false`; due date unchanged; zero four-register recorder movements; balances unchanged. | failure/atomicity; C1, C3, C5, C9 |
| N2 varied negative | Fresh different invoice ref; `Date = R-20 days + 12h`; `PaymentDueDate = R-22 days`. | Same negative observations as N1, bound to the second ref. | C1, C3, C4, C5, C9 |
| R1 blank preservation | Same ordinary valid data/date as P1; blank `PaymentDueDate`. | Draft saves; post follows existing success route; value remains blank; movement/balance vector matches the paired pre-feature route. | optionality/preservation; C8 |
| R2 existing refusal preservation | Blank due date plus the established insufficient-stock shape. | Existing posting refusal remains atomic with its pre-feature observation vector. | preservation of existing negative gate |

The external oracle compares raw typed observations. Probe process success alone is never a business result.

## 8. Baseline/RED plan — absent behavior without broken loading

No RED is executed in stage 1. After independent pre-patch challenge, and still before assembling the full production patch:

1. **Source baseline copy:** create a physical prepared copy from the immutable snapshot. A task-specific probe performs string-based runtime metadata lookup for `PaymentDueDate`; it must record `attributeExists=false` and skip any direct access to the missing property. Therefore the unmodified configuration can load/update and the RED is not an artificial compile/load failure.
2. **Metadata-only diagnostic RED copy:** create a second fresh prepared copy containing only the selected attribute plus task instrumentation. It must load/update, pass M1 persistence, and then N1/N2 must incorrectly post under unchanged BSL. That observed survivor proves the required behavior is absent and gives C1 mutation power. This diagnostic tree is not the production candidate.
3. Only after those receipts are sealed may a third fresh prepared copy receive the complete two-file metadata+BSL production delta for GREEN. Clean repeat starts from yet another fresh copy.

A broken fixture/probe/load is `INVALID`, not RED. RED requires successful platform load/update/runtime and current-run domain observations that differ only because the selected posting rule is absent.

## 9. Future probe/oracle and physical-copy boundary

- Source CF, snapshot, and manifest remain immutable/read-only. Every baseline, diagnostic RED, GREEN, and repeat tree/IB is physically separate under an issue-owned `.local/` root; none is an in-place overlay or symlink into the snapshot.
- The task-specific probe/instrumentation and semantic oracle remain outside the general lifecycle runner. The probe creates data and emits raw typed values, refs, run nonce, post outcomes, movement counts, and balances; it contains no expected pass/fail table. The external oracle evaluates this frozen matrix.
- The original-source baseline probe uses metadata lookup by name and conditional access so the absent field cannot break loading. GREEN may access the property only after M1 confirms metadata presence.
- Native execution later uses only the existing public `run-prepared` interface. No runner, generic patch generator, semantic framework, cleaner, skill, or snapshot change is authorized.
- Before and after every future native phase, recheck the manifest/CF identity and snapshot closure. Prepared-copy hashes bind each run separately; future production and instrumentation diffs stay distinct.

## 10. Evidence tier and limits

Current evidence tier is **static, identity-bound pre-patch contract**: exact source bytes prove available seams and feature absence, not runtime semantics. The issue ultimately requires **milestone/R&D native evidence** (baseline/RED, GREEN, clean repeat, exact candidate binding, and independent reviews) because it claims an end-to-end metadata+BSL product path. This stage makes no platform-acceptance, runtime, GUI, migration, deployment, or production-readiness claim.

Freeze gate: independent review must attempt a materially plausible survivor against this exact document before any production patch. Any deficiency is recorded as an additive amendment with chronology preserved.

## 11. Additive amendment 1 — relational independence, full calendar ordering, and preservation

This section is appended after two independent read-only adversarial reviews of the exact frozen commit. It does not rewrite sections 1–10. Both reviews returned `HOLD` because materially plausible wrong implementations survived the original finite matrix:

- a guard based on an absolute runtime-date threshold instead of `SalesInvoice.Date`;
- a comparison of only day, or month/day without year;
- a correct lower-bound guard combined with an unintended maximum payment-term window;
- a metadata observation that reports only runtime value type `Date` and therefore does not prove the platform metadata qualifier is date-only.

The following cases and criteria are mandatory in addition to M1/P1/B1/N1/N2/R1/R2.

### P2 — old absolute date, document-relative valid

- `Date = R - 40 days + 12 hours`;
- `PaymentDueDate = R - 39 days`;
- the draft saves and rereads successfully;
- direct server posting succeeds and `Posted = true`;
- the due value remains unchanged;
- the complete normal movement/balance vector matches the compatible blank-date control.

This valid due date is older in absolute time than N1 and N2. It kills an absolute current-date threshold that happens to separate the original cases.

### N3 — recent absolute date, document-relative invalid

- use fresh references;
- `Date = R - 2 days + 12 hours`;
- `PaymentDueDate = R - 3 days`;
- the draft saves and rereads successfully;
- direct server posting is refused;
- persisted `Posted = false` and the due value remains unchanged;
- recorder movement counts are zero in `Sales`, `CustomerBalance`, `InventoryInWarehouses`, and `InventoryCost`;
- paired before/after aggregates and balances are unchanged.

This invalid due date is newer in absolute time than P1 and B1. Together P2 and N3 force a relation to the document date rather than to runtime age.

### P3 — far-later preservation

- `Date = R - 10 days + 12 hours`;
- `PaymentDueDate = R + 400 days`;
- the draft saves and rereads successfully;
- direct server posting succeeds and `Posted = true`;
- the due value remains unchanged;
- the complete normal movement/balance vector matches the compatible blank-date control.

This kills a plausible but out-of-scope maximum payment-term or upper-bound refusal.

### N4/P4 — deterministic cross-year ordering

Let `Y` be a historical year derived at runtime from `R` and use fresh references for each case.

- **N4:** `Date = January 1 of Y at 12:00`, `PaymentDueDate = December 31 of Y-1 at day start`; require successful draft save/reread, direct-server posting refusal, `Posted = false`, unchanged due value, zero recorder movements in all four registers, and unchanged paired aggregates/balances.
- **P4:** `Date = December 31 of Y-1 at 12:00`, `PaymentDueDate = January 1 of Y at day start`; require successful direct-server posting, `Posted = true`, unchanged due value, and the same complete normal movement/balance vector as a compatible blank-date control.

N4 kills day-only and month/day-without-year under-validation. P4 kills the inverse shortcut that rejects every cross-year pair.

### Strengthened metadata observation

M1 must record from the platform metadata object, not merely infer from a runtime value:

- the attribute name;
- that its type description contains `Date`;
- that `Attribute.Type.DateQualifiers.DateFractions = DateFractions.Date`.

The write/reread observation remains required. `TypeOf(value) = Date` alone is insufficient because it does not distinguish date-only from date-time-capable metadata.

### Separate semantic source criterion

For `PaymentDueDate`, the production delta may introduce only the document-relative lower-bound refusal:

```text
nonblank due calendar day < document calendar day
```

It must contain no `CurrentDate`/runtime-date dependency, fixed age threshold, upper bound, payment-term window, component-only day/month/year shortcut, or any other additional `PaymentDueDate`-dependent refusal. Equivalent BSL spelling remains allowed. The final source review must verify this semantic criterion in addition to runtime observations.

### Amended observation matrix

The task-specific oracle must now cover M1, P1, B1, P2, P3, P4, N1, N2, N3, N4, R1, and R2. For every case it must record the same typed persisted-state and side-effect fields defined in section 7; it may not weaken the original clauses while adding the new cases.
