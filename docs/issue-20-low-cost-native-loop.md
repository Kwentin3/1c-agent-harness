# Issue #20 — low-cost prepared-tree native loop

Status: PR #22 exact candidate `a3527412118f2c5dc608b0c549a5f4ff0c308d8b` / tree `1305ee066fc791eb0d35351c8df9be8c067422a7` passed independent review and CI for the one-command product core. Owner acceptance then held issue #20 on one reproduced operating-cost counterexample: each completed invocation retained about 224.8 MB, including two 61.8 MB configuration copies, with no bounded compaction policy. The current follow-up is limited to compacting only the current invocation while preserving result/evidence diagnostics; it requires fresh lifecycle evidence and review before merge.

## User boundary

The caller has already authored the task-specific BSL patch, runtime probe and semantic oracle in an ordinary prepared tree below `.local/prepared/`. The common capability does not create or interpret them.

One supported command must own every remaining mechanical action:

```bash
python3 scripts/native_cycle.py run-prepared \
  --input-tree .local/prepared/<task> \
  --complete-marker 'complete###true' \
  --timeout-seconds 180
```

The same command can be repeated without editing a hash, spec, nonce, receipt path or run root. Each invocation prints a machine-readable envelope containing the final status and repository-relative `resultPath`.

## Fixed completion transport

The prepared probe treats the 1C global `LaunchParameter` as the receipt file path and writes a fresh UTF-8 receipt whose exact terminal line is `completeMarker`. The executor passes the generated receipt path through the standard 1C `ENTERPRISE /C` parameter. This is the platform-defined startup-parameter seam, not task-specific BSL patching by the lifecycle tool.

The task may derive other probe-local values from that path or keep them static in its own prepared tree. Their meaning remains outside the lifecycle capability.

Platform references:

- 1C Administrator Guide, command-line parameters: <https://its.1c.ru/db/v838doc/bookmark/adm/TI000000493>
- 1C Developer Guide: the startup parameter is the `/C` analogue exposed as global `LaunchParameter`: <https://kb.1ci.com/1C_Enterprise_Platform/Guides/Developer_Guides/1C_Enterprise_8.3.23_Developer_Guide/Chapter_37._Service_features/37.2._Setting_Designer_parameters/37.2.5._1C_Enterprise_startup/>

## Generated artifacts and identities

For each invocation the command must:

1. create a fresh unique invocation root below `.local/runs/native-cycle/`;
2. record the prepared source identity, including modes, paths, entry types, empty directories and bytes;
3. copy the prepared source to `frozen-input/` without changing the source;
4. remove write bits only from the generated frozen copy and fingerprint it;
5. generate a closed spec and a non-existing native `runRoot` below the invocation root;
6. use the accepted `run_cycle()` implementation as the only owner of copy → file IB → create/load/runtime → cleanup;
7. pass the generated receipt path through exact runtime argv as `/C <path>`;
8. recheck the original prepared source after every success or failure;
9. persist and print the final result location.
10. after terminal source recheck, compact only the current invocation by removing its generated `frozen-input`, `run/work-copy`, `run/ib`, `run/home` and `run/tmp` trees;
11. retain generated spec, final result, receipt and native logs/results, and report observed peak/retained logical bytes plus cleanup duration;
12. fail closed if current-invocation compaction fails. Prepared inputs, snapshots, platform trees and sibling/older invocation roots are never cleanup targets.

The result must distinguish:

- prepared source identity before/after;
- generated frozen-input identity;
- generated spec identity;
- executor pre-`chmod` copy identity;
- post-`chmod` Designer load identity;
- exact generated runtime argv, including `/C` binding.

## Baseline and budget

Before this change, caller-owned preparation after task-specific patch/probe authoring required three manual actions per binding:

1. recursively remove write bits;
2. import internal Python code to compute the closed-tree fingerprint and copy it into JSON;
3. author a new spec with a fresh run root and receipt binding.

Target from the user command boundary:

- supported command blocks: 1;
- manual `chmod`: 0;
- ad-hoc Python snippets: 0;
- manual hash substitutions: 0;
- manual spec/run-root/nonce/path edits: 0;
- manual process cleanup on nominal success: 0;
- native attempts: measured, not inferred;
- wall time: measured from command start, including freeze/fingerprint/binding;
- new common product code: measured on the final candidate.
- observed peak and retained logical bytes per invocation: measured from the invocation root;
- manual artifact cleanup after success/failure: `0`.

`LOW-COST NATIVE LOOP` is permitted only if all target counts are met by success and clean repeat using the same caller command.

Measured candidate result:

- supported caller command blocks per run: `1`;
- manual `chmod`, fingerprint substitution, spec/run-root/receipt edits: `0`;
- native attempts: success `1`, repeat `1`;
- full command wall time: success `176.030 s`, repeat `169.239 s`;
- executor wall time within those totals: success `151.896 s`, repeat `145.268 s`;
- same caller command: yes;
- unique invocation roots/specs/bindings: yes;
- post-repeat active native processes: `[]`.

The earlier candidate verdict is superseded by owner acceptance `PRODUCT CORE PASS / ISSUE #20 HOLD` until bounded operating storage cost is demonstrated. The final low-cost verdict may be restored only after fresh success/repeat show compact retained state with no manual cleanup and a new independent KISS/storage review passes.

## Bounded current-invocation storage contract

Compaction is part of `run-prepared`, not a separate cleaner or retention daemon. It has no path, age, count or glob input. Its target set is constructed from the invocation object created by the current process and is exactly:

```text
frozen-input/
run/work-copy/
run/ib/
run/home/
run/tmp/
```

The retained compact record is:

```text
spec.json
run/result.json
run/evidence/
run/logs/
```

The final result reports policy, status, exact `configuredTargets`, verified `completedRemovedPaths`, retained path classes, exact `preCompactionLogicalBytes`, `removedLogicalBytes`, `retainedLogicalBytesExcludingResult`, compaction duration and `manualCleanupActions=0`. The result file is excluded from the retained byte field to avoid a self-referential size loop; the evidence cost ledger measures actual post-command retained total and a sampled lifecycle peak externally. Cleanup runs after the prepared source terminal recheck on success and failure paths. A cleanup error cannot remain `runtime_contract_completed`; it is persisted as `artifact_cleanup_failed`. Existing lifecycle failures keep their primary failure status and add explicit failed-compaction diagnostics.

This contract deliberately does not delete another invocation, an older issue root, prepared input, source snapshot, manifest, platform or external path. Cross-run retention and general filesystem cleanup remain outside the product surface because current-invocation compaction removes the reproduced unbounded-growth cause without adding a cleaner abstraction.

## Compared approaches

### A. Generated frozen binding inside the existing CLI — selected

Extend `scripts/native_cycle.py` with `run-prepared`; generate a frozen input and v1 spec, add the receipt path to the accepted runtime argv through `/C`, then call the existing executor. This keeps one executable and one lifecycle implementation. The only new persistent states are the invocation root, frozen input and generated spec required by the finish contract.

### B. Separate preparation wrapper — rejected

A second script could freeze/fingerprint, author a spec and launch `native_cycle.py run`. It would expose two public executables and duplicate failure/result-location ownership. Deleting that wrapper would still leave the same user path expressible directly in the existing CLI, so it is unnecessary.

A BSL placeholder replacement engine was also rejected: it would mutate the generated configuration and create a generic patching surface when the platform already provides `/C`/`LaunchParameter`.

## Falsifiable acceptance

Pure/fake-process tests must prove:

- writable and read-only prepared inputs are accepted without changing source bytes or modes;
- symlink/non-regular inputs fail closed;
- two different input identities/shapes produce correctly distinct source/frozen identities;
- generated roots/specs/bindings are unique on repeat;
- the same caller argv completes two fake native lifecycles with no manual edits;
- failure prints and persists an unambiguous result location;
- success and failure automatically remove only the current invocation's reproducible heavy trees while retaining compact diagnostics;
- cleanup failure is explicit and cannot leave a nominal success;
- sibling invocation roots and prepared/snapshot inputs are never cleanup targets;
- observed peak/removed/retained bytes are persisted and repeat requires zero manual artifact cleanup;
- the generated runtime argv contains exactly one `/C` followed by the generated receipt path;
- no second lifecycle implementation or semantic receipt parser is introduced.

Milestone evidence must then add:

- one fresh native success and one clean native repeat through `run-prepared`;
- prepared-source byte/mode identity before and after both runs;
- exact generated identities, argv, result locations and process-cleanup state;
- a second non-native input shape proving the preparation contract is not tied to issue #18;
- full Python 3.9/3.12 suites;
- independent adversarial review of exact HEAD/TREE;
- a separate open/unmerged PR.

Issue #20 closes only after that result is merged and the full measured budget supports the product claim.
