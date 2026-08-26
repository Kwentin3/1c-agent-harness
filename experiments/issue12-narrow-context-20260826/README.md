# Issue #12 — narrow-context evaluation package

This package freezes the reviewable evidence for issue #12. It compares standard direct-source navigation with the smallest candidate that introduced no new runtime component: a bounded context-frontier protocol using the same filesystem search/read tools.

## Result

**Retain the direct-source baseline. Add no parser, index, graph, RAG, daemon, MCP service, or dependency.**

Both approaches answered the frozen SDMS task completely (9/9 oracle items, no dangerous claims or invalid locators). The Jet baseline produced the complete minimal metadata change and both Jet arms passed native platform acceptance, but candidate added unrequested `FullTextSearch=Use` and therefore failed the semantic hard gate. It also failed the stricter efficiency rule frozen before results:

- SDMS: +21.96% context bytes, +14.29% navigation operations, only −11.40% wall clock;
- Jet: −27.51% wall clock, but +160.07% selected source context and lower semantic coverage;
- the amended Pareto rule allowed at most 10% regression in another observed efficiency metric.

`decision.json` is the machine-readable verdict. `adjudication/*.md` gives the independent ledger and caveats.

## Frozen tasks

- `tasks/sdms.json`: repository-relative publication of the frozen SDMS blind contract;
- `tasks/sdms-questions.json`: exact canonical question set whose SHA-256 is bound by both SDMS answers;
- `tasks/sdms-frozen-original.json.b64`: exact original frozen task bytes in explicit Base64 transport encoding; decode before SHA-256 or JSON review;
- `tasks/sdms-binding.json`: mechanically tested identity chain from those decoded frozen bytes through path-only sanitization to the canonical question set and both arms;
- `tasks/jet.json`: add one false-by-default item-level Boolean attribute to warehouse metadata, without forms, BSL, posting logic, or runtime semantics.
- Issue #10 is reused rather than rerun for the existing local BSL/write class.

The first real historical Jet candidate was rejected before arms: it changed 18 files and added a complete report subsystem, so it did not isolate the minimal metadata capability. The accepted synthetic task changes one existing metadata XML file and has a native platform gate.

## Contents

- `design.json` — hashes and compact form of the design and pre-results amendment;
- `tasks/` — model-visible blind task contracts;
- `answers/`, `contexts/`, `metrics/` — exact frozen arm outputs;
- `diffs/` — exact no-index arm diffs;
- `patches/` — equivalent repo-root-independent patches for reproduction;
- `evidence/` — sanitised native 1C receipts for both Jet arms;
- `adjudication/` — independent per-task scoring and methodology review;
- `decision.json` — final bounded decision and negative scenarios;
- `package-manifest.json` — exact closed-set artifact hashes.

Heavy work copies, disposable infobases, full 1C logs, immutable snapshots, and private selection oracle remain under ignored `.local/`; they are not committed. Receipts bind their hashes and closure counts without publishing machine-specific paths.

## Native result

Both Jet patches were applied in physically separate writable copies of the 5,099-file immutable Jet snapshot. Each arm used a new disposable file infobase on official 1C training platform 8.5.1.1150:

1. `CREATEINFOBASE`;
2. `DESIGNER /LoadConfigFromFiles <work-copy> /UpdateDBCfg`;
3. require process exit 0, exact `DumpResult = 0`, and `Configuration successfully updated` in the load log;
4. revalidate the immutable snapshot as 5,099 listed/actual files with zero missing, extra, mismatch, or symlink entries.

The receipts in `evidence/` record success for both arms. This proves platform acceptance/schema consistency only. No Enterprise runtime behavior is claimed because the task intentionally adds metadata without enforcement logic.

## Oracle caveat

The frozen private Jet oracle required one exact UUIDv5 even though the public blind task explicitly hid both its algorithm and expected value. That arbitrary identity is not inferable and cannot fairly distinguish blind arms. The oracle was not silently changed: the defect is preserved in the adjudication. Both arms used unique valid UUIDs and both loaded/updated natively, so semantic grading accepts both.

## Fail-closed negatives

`tests/test_issue12_evidence.py` mutates disposable in-memory/copy data and requires rejection for:

- a stale/foreign snapshot content ID;
- removal of the essential SDMS request-manager context;
- selection of same-term distractor `Reports/ЗадачиПоЗаявкам.xml` as creation-path evidence;
- expansion of the Jet metadata task into a form/BSL source;
- changed, missing, or unlisted package artifacts through exact manifest closure.

## Reproduction

Validate the committed packet:

```bash
python3 -m unittest tests.test_issue12_evidence -v
python3 -m unittest discover -s tests -v
git diff --check
```

To reproduce native acceptance after preparing the lab from `docs/lab.md` and `docs/lab-bootstrap.md`:

```bash
SNAP=.local/runs/training-jet-review-final/snapshot
RUN=.local/runs/issue12-reproduction-<unique-id>
mkdir -p "$RUN/work" "$RUN/logs"
cp -R "$SNAP/." "$RUN/work/"
chmod -R u+w "$RUN/work"
git apply --directory="$RUN/work" experiments/issue12-narrow-context-20260826/patches/jet-baseline.patch
```

Then run the same fixed `CREATEINFOBASE` and `DESIGNER /LoadConfigFromFiles /UpdateDBCfg` commands described in `docs/issue-10-write-cycle.md`, targeting only `$RUN/work` and `$RUN/ib`. Require exact-zero DumpResult, the success log marker, and clean pre/post snapshot closure. Never load or dump over the immutable source snapshot.

## Scope

The result is bounded to one SDMS business-path task, one Jet metadata task, the two observed model runs per task, and reused issue #10 evidence. It is not a statistical benchmark and does not establish universal superiority or inferiority of a navigation method across 1C configurations.
