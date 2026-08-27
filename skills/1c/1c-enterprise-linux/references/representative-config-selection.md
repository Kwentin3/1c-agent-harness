# Selecting a legally usable representative 1C configuration

Use this note when a smoke/demo fixture is insufficient and an issue requires a complex configuration plus an independent oracle.

## Selection gates

1. **Freeze identity:** pin a full commit SHA or release tag resolved to a SHA. Do not rely only on a mutable branch or the configuration's internal version field.
2. **Verify rights:** inspect the repository LICENSE *and* NOTICE/third-party notices. A public repository without an explicit license is not a reusable open-source fixture. A top-level permissive license may not cover bundled 1C libraries.
3. **Match legal platform use:** record platform prerequisites separately from source-code licensing. Some configurations based on 1C:Subsystems Library permit study on the training platform but require a lawfully acquired platform/basic delivery for other use.
4. **Measure complexity without a full download:** use the GitHub recursive tree API at the pinned SHA to count BSL/XML/MDO files, total bytes, metadata object references, tests, docs, and release-asset sizes. Avoid large release assets during shortlist research.
5. **Read actual compatibility metadata:** inspect `Configuration.xml` (`CompatibilityMode`, often `Version8_3_xx`) or EDT `Configuration.mdo` (`compatibilityMode`). README minimum-platform claims are a separate fact and may be stricter.
6. **Grade the oracle:** executable Gherkin/Vanessa/YaXUnit tests > versioned API/schema specifications > detailed workflow docs > README only. Confirm whether tests are current and actually run; merely finding `.feature` files is not CI evidence.
7. **Separate compatibility mode from runtime:** opening `CompatibilityMode=8.3.12` on platform 8.5 tests an old metadata mode, not behavior on the 8.3.12 runtime. Legacy-platform claims require the exact old platform executable/license and a fixture that ran there.
8. **Prefer source trees over large bundles:** partial/sparse clone the pinned source paths when possible. Use `.cf` only when it is small, pinned, and its provenance is clear; treat `.dt` as seeded data with additional read-only/privacy implications.

## Candidate evidence snapshot (researched 2026-08)

These are starting points, not timeless endorsements; re-check upstream state and legal notices before use.

### BlizD/Tasks — strongest public business candidate

- Pin: tag `2025.10.19.1`, commit `c440e577d4f24600180d40f1df9465ac7dfc4ddf`.
- Rights: Apache-2.0 plus `NOTICE.md`; NOTICE says it is based on 1C:Subsystems Library and explicitly allows study on the training version within its limits.
- At that commit: 9,276 files, 5,815 XML, 2,125 BSL, 6 `.feature` files; about 237 MiB of blobs. Metadata includes 102 roles, 517 common modules, 88 catalogs, 13 documents, 37 reports, 193 information registers, one business process, and one task.
- Compatibility: `Version8_3_21`; README says minimum platform 8.3.22.1923.
- Oracle: six business-facing Gherkin scenarios plus README/wiki/video documentation. Treat as medium-high until current execution is demonstrated.
- Provenance caveat: the pinned tag's configuration declares internal version `2025.03.30.1`; bind experiments to SHA and record the mismatch.
- Verdict: good issue-level candidate after a human freezes 5–7 expected answers; avoid the ~126 MiB release ZIP during discovery.

### dns-technologies/SDMS — strong corporate-domain runner-up

- Pin: commit `eb372065e273ceade9939542ce56565c4d422e91` (no release/tag at research time).
- Rights: GPL-3.0.
- Artifacts: `sdms.cf` about 8.05 MiB, `sdms.dt` about 7.91 MiB, and EDT sources.
- Complexity: 2,492 files, 646 BSL, 775 MDO; 30 roles, 100 common modules, 54 catalogs, 10 documents, 23 reports, 103 information registers, and 24 scheduled jobs.
- Compatibility: 8.3.26.
- Oracle: README plus OpenAPI 3.1 / API version 1.2 with 36 paths and 40 operations; no tests observed.
- Verdict: representative, but oracle coverage is strong mainly for API/deployment questions. Prefer `.cf` over seeded `.dt` for a read-only config experiment.

### 1C-Company/GitConverter — compatibility/technical fixture only

- Pin: release `v.1.0.8.4`, commit `cc7a7afb2d8f1432bd54afcefdba31f1e9b51aff`.
- Rights: CC-BY-SA-4.0; official release includes a ~319 KiB `1cv8.cf`.
- Complexity: 274 files, 41 BSL, 50 MDO, extensive workflow documentation, no tests observed.
- Compatibility: 8.3.12.
- Verdict: useful for old compatibility-mode and tooling probes, but too narrow to stand in for a real business application or old runtime.

### Rejection patterns

- `1C-Company/dt-demo-configuration`: technically substantial but no LICENSE/README/tests at the inspected commit and still a demo; public hosting alone is insufficient permission.
- `1c-syntax/ssl_3_2`: licensed and large, but a subsystem library rather than a standalone business application.
- `1Ci-Company/Jet`: excellent native smoke fixture, but do not use it to close an acceptance criterion that explicitly rejects toy/demo-only evidence.

## Minimal experiment handoff

Before native loading, preserve:

- repository URL, tag, resolved commit SHA, and selected artifact/path;
- LICENSE and NOTICE URLs at the SHA;
- compatibility mode and README platform minimum as separate fields;
- tree-based complexity inventory and exact unit (`bytes`, MiB, or file count);
- 5–7 predeclared questions with expected facts, allowed evidence, and dangerous false conclusions;
- oracle status (`executed`, `documented-only`, `unknown`) and a named human reviewer when tests do not cover the whole question set.

A candidate can close a representative-config blocker without being committed into the public repository: keep source, platform, dumps, indexes, and results under the ignored machine-local workspace and publish only provenance, measurements, questions, and non-sensitive outcomes.