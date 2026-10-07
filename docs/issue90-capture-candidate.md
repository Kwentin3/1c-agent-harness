# Goal90 — current capture source candidate

**PARTIAL / SOURCE_CANDIDATE_NOT_INSTALLED. #90 remains OPEN.**
This candidate extends PR93; it does not deploy, restart, merge, or close the Goal.
[Access #94](https://github.com/Kwentin3/1c-agent-harness/issues/94#issuecomment-6035866327) passed personally after operator cleanup.
The former `CURRENT_JOURNAL_ACCESS_BLOCKED` is historical, not the current blocker.

## Facts and actual execution

- Existing diagnostic launcher was read through pinned SSH. It still selects the retained September #80 archive. A current-journal capture capability is not automatically a current installed reader. Registered tool schemas remain the existing nine tools; none is added here.
- Through the #94 route, one further ledger-reserved official ibcmd export covered UTC **2026-10-06 10:50:55 → 2026-10-07 10:50:55**. SSH/native exit0, native **1.519781652 s**, transport/controller wall **11.101641562 s**, output **982281 bytes**, SHA256 `e49403b281e29dbd180f8e18761f97aa9c72257e1a218ca89b0fea0f7faa5a0e`.
- **1445 records**, earliest11:14:11 on October6, latest06:37:09 on October7; 1420 Information and 25 Error; 147 nonempty comments. These are observations of the returned export, not proof of temporal completeness, root cause or absence of more errors. The existing official-JSON→reader-XML conversion accepts these actual fields.
- Before/after directory inventory was equal; identity remained the exact #94 retained container/image/VRD and official binary. No source copy, alternate IB, archive fallback, new parser or runtime installation was used. Stat equality is not a content/snapshot fence.
- Canonical ledger readback: **help2/3, exports2/12, session cycles0/2**, native total **7.293003418 s/900 s**; SHA256 `89bd63a3f8ac14e1693e1fb2ebc6180be4023a148cd4a53965af6440489dc5b8`. Budget was not reset. Native attempt was reserved/read back before execution; failures would consume their attempt too.
- Public demo ingress without credentials returns **401 / Basic**. This ordinary session has no demo credential in its approved native secret source or environment. No other files, process memory or history were searched for passwords; no login was attempted.
- Registered `one_c_observation_info({})` still returned its existing September18 EXCP/EXCPCNTX source: three files/47170 bytes. This proves that route still works, not fresh October telemetry. Coding/open/native verification was not invoked; revoked #91 credentials remain unused.

Sanitized machine evidence: [current-capture-receipt.json](../experiments/issue90-current-source/current-capture-receipt.json).
Exact raw requests, ledger CAS/readbacks, native receipt and output are protected under the task-owned continuation area, not committed. Neither raw events/comments nor secrets/connection coordinates are in this package.

## Minimal source change

### 1. Existing exporter owns conversion and capture admission

[`eventlog_file_exporter.py`](../one_c_harness/eventlog_file_exporter.py) retains the existing direct-ibcmd path. A deployment-selected capture mode uses three settings:

- `ONE_C_HARNESS_EVENTLOG_CAPTURE_COMMAND`: absolute executable, stdin closed export request → bounded private capability receipt.
- `ONE_C_HARNESS_EVENTLOG_CAPTURE_BINDING`: absolute deployment-owned JSON file.
- Existing `ONE_C_HARNESS_EVENTLOG_WORK_ROOT`: task-owned output/evidence root, physically separate from command/binding.

If either new setting is present, a missing/invalid mate fails closed; it never falls back to the archive/direct backend.
The closed binding contains exactly `schemaVersion:1`, human `name`, `referenceId`, `referenceImage` (`sha256:` digest), `vrdSha256`, and `binarySha256`. Identity is deployment-selected, never a model argument. The host/operator fills it from admitted #94 evidence, not a guessed IB name.

The exporter checks returned reference/image/VRD/binary pins, actual IB→journal relation and mounted directory identity, nonprivileged worker UID/GID/groups, UTC/RO boundaries, native status/duration, exact requested window/format in argv, finite recent receipt time (≤60s, bounded clock skew), safe bounded inventories and decoded output length/hash. A mismatch or stale capture is rejected. This is validation of a trusted transport receipt, not independent re-inspection of root-owned handler bytes.

The capture command has a75s external deadline and bounded stdout2MiB/stderr1KiB; the #94 native limit stays30s/output1MiB. Owned process groups are cleaned. Valid canonical JSON receipts are retained0700/0600 alongside existing bounded evidence, at most eight `capture-*.json` files with one-hour retention. `sourceCapture.capture.receiptSha256` hashes canonical receipt JSON, **not necessarily the original wire spacing**. It therefore matches the canonical private receipt file; the separately published native receipt hash refers to exact received bytes.

The existing converter emits reader XML with one closed namespaced `Capture` metadata element. It carries only safe identity, capture/output/receipt hashes, times and conservative freshness/coverage. No host/mount/IB paths, argv or base64 payload are exposed.

### 2. Existing reader keeps evidence attached to retained selections

[`eventlog_observation.py`](../one_c_harness/eventlog_observation.py) validates the optional metadata and retains it with integrity-protected selection state. Select/page/record expose the **same** `sourceCapture`; page/record never reacquire the source. Existing filters, count limits, comment continuation, opaque references, TTL and compact output remain.

For current captures:
- `snapshot.stable` means retained bytes only, never live-source consistency.
- `coverage.retainedCountComplete` reports the existing count-boundary result.
- `coverage.temporalComplete=false`; `complete=false`, `partial=true`.
- `freshness.completeThrough=null`; a recent receipt is not proof of event visibility through now.
- Changed inventory is marked `source_changed`; unchanged inventory remains `capture_consistency_unproven`.
- Empty results remain partial/unknown, not “no errors”. Unavailable, stale, corrupt and foreign-binding captures fail separately/safely.

Legacy XML without Capture preserves the accepted #80 behavior only in legacy deployments. The current reader deployment must set `ONE_C_HARNESS_EVENTLOG_REQUIRE_CAPTURE=1`: missing metadata then fails closed, never “ok archive”. Legacy evidence is not promoted to current-source evidence. The new dispatcher cannot silently route a current diagnostic request to that archive.

### 3. Thin deployment glue; no new service or model tool

[`current-journal-client.py`](../hermes-plugin/deployment/current-journal-client.py) encodes only the closed JSON request and uses the existing pinned `current-journal` alias/config selected by `ONE_C_HARNESS_CURRENT_JOURNAL_SSH_CONFIG`. It accepts seconds-only UTC window/JSON/follow0; source/runtime/output/shell input is rejected. It execs the established SSH route, not a platform process on Hermes. Heavy runtime remains on the home executor.

[`one-c-harness` dispatcher](../hermes-plugin/deployment/one-c-harness) routes only `eventlog_select/page/record` to absolute executable `ONE_C_HARNESS_CURRENT_EVENTLOG_COMPANION`, a deployment-owned installed **data-only** companion in Hermes. Native acquisition is still the existing home capability. Missing current companion fails without archive fallback. Techlog and coding routing stay unchanged. Existing historic remote selections are preserved, not migrated or deleted; their refs must not be mistaken for the new local selection store.

Deployment must pair the new companion and plugin release seal; an old plugin/new companion artifact mismatch correctly refuses. No production installation/activation has been performed here. The dispatch/client files are separately source-controlled glue; the existing release-seal algorithm covers the core/plugin/skill closure, not these deployment files. Their exact commit/file hashes must be bound during rollout.

## Retained-real-export replay, not installed acceptance

The unmodified native receipt/payload were replayed through the candidate with a **declared retrospective validation clock** (`native start+duration`). This does not invent a received-time witness or claim the old receipt is fresh now.

Candidate XML754542bytes. Local selection0.388994198s; source1445/matched25 Error records. Two pages returned25 distinct opaque refs. One real comment1232bytes was read in ten128-byte chunks; sourceCapture stayed identical through page/record. A second selection over the same saved input did not change the first selection's bytes/hash/page. No native call occurred in replay.

This closes a candidate consumer/provenance check only. It **does not** close installed positive selection→page→record/comment, a second new event, session lifecycle, current visibility latency or production performance. Old receipt replay is not a fresh source query.

## Review corrections on the source candidate

[DeepSeek review of e3cc3cc](https://github.com/Kwentin3/1c-agent-harness/pull/93#issuecomment-6037026702) was collected/published. It is static source inspection, not execution or merge authorization. Hermes reproduced F1–F4 against that candidate with regressions observed failing for the reported behavior, then made bounded fixes:

- **F1:** reader compares offset-free parsed datetimes, not timestamp spelling. Space-separated and fractional aliases accepted by the running Python ISO parser survive the exporter→XML→reader boundary; a genuinely different requested end still fails. Python3.9 rejects `.5` (while accepting `.123`); the regression checks that unsupported form stays `invalid_request`, not invented cross-version support. Correction CI run37615717579 caught this test assumption (3.9 FAIL/3.12 PASS); the fixture was corrected, not the native contract. This does **not** widen the #94 transport: `current-journal-client.py` still accepts only canonical seconds-only `YYYY-MM-DDTHH:MM:SS`. Fractional/native transport support is not claimed.
- **F2:** actual `source_stale_capture` from exporter remains a distinct `unavailable` reason through reader decoding. Existing `source_stale` remains accepted for compatibility.
- **F3:** `coverage.countReasonCode` and `coverage.temporalReasonCode` independently retain count and temporal limitations through selection/page/record; the existing primary `reasonCode` remains count-first for compatibility.
- **F4:** non-dict or missing-pin `sourceBinding` is explicitly `source_binding_mismatch`, still rejected before conversion. Corrupt non-binding receipt fields remain `source_incomplete_receipt`.
- **F5 retained limitation:** capture returns lifecycle/record/XML metrics to its caller but does not write the legacy optional `ONE_C_HARNESS_EVENTLOG_METRICS` file. Cost evidence comes from protected acquisition receipts and measured calls, not that file. No metrics parity or installed-performance acceptance is inferred.
- **F6 clarified:** package metadata requires Python≥3.10; CI3.9 is a source compatibility test, not an installability claim. Deployment glue requires POSIX `sh`, `base64`, `python3`, and `/usr/bin/ssh`, plus the admitted operator-owned pinned config/alias. The unchanged coding dispatcher has a separate Python3.11+ requirement. The source reproduction commands below exercise fixture processes/dispatch only, not installation or live transport. These prerequisites must be checked before owner-authorized activation.
- **F7 retained boundary:** operator SSH config/content and deployment-selected local companion remain trusted installation inputs. Harness does not edit that config, change the forced command, infer permission to activate, or repeat native exports for review.

The original exact-head CI for e3cc3cc succeeded in run37614089055 (3.9/3.12). It does not apply to later correction bytes. The historical `candidate-test-receipt.json` is preserved for that candidate; corrections have a separate `review-corrections-test-receipt.json`. No native/SSH/session/deploy calls are part of this correction round. A later review must bind the replacement candidate; unfinished/failed reviews remain pending/INCONCLUSIVE, never a second approval.

## Validation and remaining acceptance

Tests are added before the respective missing behavior (observed RED → GREEN): capture→XML metadata, foreign binding rejection, corrupt/stale/runtime receipt rejection, retained page/record/partial-empty, deployment capture-process path, timeout, and local eventlog dispatcher without fallback. Actual external-process fixtures exercise boundaries without native1C/network. New transport has a closed-command encoding fixture. Existing full gates/release sealing and CI apply; test receipts are in the PR report, not inferred from source inspection.

Reproduce source-only checks from repository root:

```sh
python3 -m unittest discover -s tests -p 'test_eventlog*.py' -v
python3 -m unittest discover -s tests -p test_current_journal_client.py -v
python3 -m unittest discover -s tests -p test_hermes_deployment_wrapper.py -v
python3 -m unittest discover -s tests -v
git diff --check
```

No replay command for private data is promised reproducible without its protected input; deterministic synthetic fixtures run from a clean checkout. Native exports cannot be casually repeated: use canonical remaining budget and reserve before invoking.

**Next external prerequisite:** owner-bound installation/activation of this exact source candidate and its deployment glue/settings, without demo restart or replacing its runtime. Provide the already-existing demo session credential to the admitted Hermes secret/auth surface for the two permitted ordinary session cycles. User must not relay raw exports/passwords. This is one environment-enablement handoff, not a request to repeat read-only approval and not evidence of completed deployment. No new rights/key/mount is needed for journal reads.

After enablement Hermes still owns: genuine registered fresh query, two ordinary login/logout witnesses, detection of the subsequent event, stable prior selection, installed positive comment continuation, measured visibility/cost, and honest changing-source/rotation boundaries. Direct live capture currently lacks a documented fence/flush guarantee; no generalized consistency or rotation support is claimed. If an added capture mechanism requires changing the operator capability, obtain a separately bounded owner decision rather than quietly editing PR95's installed handler.

The10s selection threshold is **not proven**: the real capture transport alone took11.101642s; the0.388994s local replay is not comparable to an installed end-to-end query. Visibility≤30s is NOT_RUN; session budget0/2. Business-data/config/logging-policy writes, native coding, install/restart/merge: **0**.
