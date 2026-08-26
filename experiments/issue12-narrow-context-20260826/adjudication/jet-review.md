# Issue #12 — independent Jet metadata adjudication

## Decision: retain baseline; candidate not useful

**Status: DONE.** The baseline is a semantic success and both arms pass native 1C platform acceptance. The candidate is a partial semantic failure because its new attribute has `<FullTextSearch>Use</FullTextSearch>` instead of the frozen oracle's `DontUse`. The bounded-frontier candidate is not useful under either the original preregistered rule or the stricter pre-results amendment.

The exact hidden UUIDv5 equality is **not** used to distinguish the arms. It is an oracle construct defect: the public task expressly hid expected UUIDs and disclosed no deterministic algorithm or canonical name (`selection-jet-metadata-v3/public-task.json:19-26`), while the private oracle later requires one exact UUIDv5 generated from hidden inputs (`oracle.json:27-33`). Both arm UUIDs are syntactically valid, unique, non-colliding, and accepted by native Designer. The frozen oracle remains untouched; raw exact-equality failures are retained in `adjudication.json`.

## Frozen identity and changed-file closure

- The snapshot manifest SHA-256 is `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`.
- Fresh verification found 5,099 manifest entries and 5,099 files, with zero missing files, extras, or digest mismatches.
- Each work copy contains 5,099 files and differs from the snapshot only at `Catalogs/Warehouses.xml`.
- Each retained `change.diff` exactly matches a fresh binary no-index diff. Hashes:
  - baseline: `d5e9343250f67f1d3f5f71af27e6cdd7479c2c74fa9aecf1335a0b4146494356`
  - candidate: `5c2e7098b8e6a94c1ac0a839a8a6996a4cf54b003711f8668d086efdee138a8f`
- CRLF convention and BOM state match the source in both changed XML files.
- Therefore forms, BSL, `Configuration.xml`, `ConfigDumpInfo.xml`, register metadata, and unrelated metadata were not changed.

## XML semantic result

Both arms correctly add one direct `Catalog.Warehouses` attribute with:

- internal name `AllowNegativeInventoryBalance`;
- English synonym `Allow negative inventory balance`;
- type `xs:boolean`;
- explicit false fill value;
- `Use=ForItem`;
- `Indexing=DontIndex`.

The baseline also has `FullTextSearch=DontUse` and passes the complete fairness-adjusted semantic checklist (11/11). The candidate has `FullTextSearch=Use` (`arms/jet-candidate/change.diff:43-46`) and scores 10/11. Native acceptance does not erase this private-oracle semantic mismatch; it shows only that both serializations are platform-valid.

### UUID oracle defect

The oracle's deterministic UUID policy was intended to make its reference reproducible, but that does not make exact equality a fair blind-arm requirement. A blind executor could not derive the hidden canonical name or know UUIDv5 was required. Accordingly:

- raw frozen-oracle equality: both fail;
- fairness-adjusted UUID criterion: both pass because each UUID is valid, unique in its work copy, absent from the original snapshot, and the work copy passes native load/update.

This correction does not rescue the candidate, whose full-text-search mismatch is independent of UUID choice.

## Locators and fresh context bytes

All declared paths/ranges are in bounds and their full-file or fragment hashes validate.

| Metric | Baseline | Candidate |
|---|---:|---:|
| Source fragments | 3 | 5 |
| Source lines | 90 | 218 |
| Fresh source bytes | 2,860 | 7,438 |
| Wall clock | 480 s | 347.93 s |

The candidate additionally logs 1,449 bytes of the shared public task, for 8,887 total logged fragment bytes. For the arm comparison, only source fragments are compared because the task is common to both arms and baseline does not duplicate it in `context.json`.

Candidate relative to baseline:

- wall-clock reduction: **27.51%**;
- source-context reduction: **−160.07%**, i.e. a **160.07% increase**;
- navigation-operation reduction: unavailable. Candidate metrics record five searches and six fragments but no comparable navigation-operation total, so none is invented.

## Native acceptance

Both receipts report platform `1C training 8.5.1.1150`, process exits 0, zero DumpResult, and status `ok`. Their referenced log hashes match the retained logs:

- baseline create: `ec54e87ed4aa545af38542709403253bf3a4549347114e425f8609cc787714d6`;
- candidate create: `ded25161712cc1b07af54deebefb00f22aae2133dee3ccf1054872b9eb6d2676`;
- both load/update logs: `4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86`.

The create logs say infobase creation completed successfully. The load/update logs end with `Configuration successfully updated` and include `Catalog.Warehouses`. Pre- and post-snapshot checks are 5,099/5,099 with zero missing, extra, mismatched, or symlink entries. This is sufficient to grade both arms **native platform acceptance PASS**.

Methodological caveat: the receipts name each arm work-copy path but do not record the exact input-tree hash or command line. The retained log/result hashes and success markers support acceptance, but a future receipt should content-bind the complete work copy and preserve the invoked command. No Enterprise runtime receipt exists; under the amendment that means runtime semantics are unproven. Here no runtime behavior was requested or claimed, so it is not a task failure.

## Dangerous distractor check

`AccumulationRegisters/InventoryInWarehouses.xml` is a concrete same-term distractor from the frozen filename search: it contains both *inventory* and *warehouses*, but it is an accumulation register rather than the warehouse master-data owner. Both arms excluded it and changed/cited only the catalog owner. Candidate search rationale explicitly distinguishes the Catalog owner from register, command, role, picture, and subsystem hits. This amendment negative passes.

## Frozen decision rules

### Original preregistered rule

**NOT_USEFUL_KEEP_BASELINE.** The candidate fails the no-lower-coverage hard gate because of `FullTextSearch=Use`. Retained insufficient-context and stale-binding negative probes are absent. The 27.51% wall-clock reduction cannot complete the original signal because the required no-increase-in-navigation-operations condition is unproven. Context bytes increase, no essential relation improves coverage, and protocol preparation time is unavailable; total candidate duration is 347.93 seconds, so the five-minute cost ceiling is not demonstrated.

### Stricter pre-results amendment

**NOT_USEFUL_KEEP_BASELINE.** Although wall clock falls by at least 25%, source context regresses by 160.07%, far beyond the 10% Pareto non-regression bound, and comparable operation telemetry is missing. The essential-relation branch also fails because candidate coverage is lower, not higher.

## Final verdict

- **Baseline:** semantic success; native acceptance PASS.
- **Candidate:** native acceptance PASS, but semantic failure on full-text-search policy and no usefulness-rule win.
- **Selection:** retain direct-source baseline; add no component.
- **Oracle correction:** preserve the frozen exact UUID expectation as raw history, but do not use it as a fair blind-arm discriminator.
