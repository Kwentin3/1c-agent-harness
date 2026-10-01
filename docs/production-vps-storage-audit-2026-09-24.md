# Production VPS storage audit — 2026-09-24

## Scope and safety boundary

This is a read-only audit of storage consumed by the 1C investigation in the
Hermes WebUI production container. It does not authorize deletion, container
restart, Dashboard start, or changes to Hermes state.

Protected and not inspected for cleanup:

- `/data/hermes-home/state.db`, its WAL/SHM files, and sessions;
- other users' workspaces and task data;
- live containers and service state;
- the canonical Jet CF, admitted snapshots, manifests, and retained evidence.

## Confirmed current filesystem state

At `2026-09-24T16:33:10+00:00`, the filesystem mounted at `/workspace` was:

```text
size=40,279,699,456 bytes
used=33,942,106,112 bytes
available=4,589,686,784 bytes
use=89%
```

The container-visible mount source is the production host path
`/opt/hermes-devops-agent/data/workspace`, so
`/workspace/1c-harnest/...` corresponds to the host path named in the incident.
The inode snapshot was healthy (about 597k of 9.7M used, 7%).

## Production 1C copies

The task-owned directory is:

```text
/workspace/1c-harnest/.local/dist/1c-8.5.1.1522
```

Its allocated size from `du` is **3,873,501,184 bytes** (3.607 GiB). The two
material files are:

| Path | Logical bytes | SHA-256 | mtime UTC |
|---|---:|---|---|
| `server64_8_5_1_1522.zip` | 1,926,723,506 | `99e735cb66ddfee5b4cf218f08b3b988c0c7c74fbbb27d348c579057d59c7b71` | 2026-09-24 05:51:50 |
| `extracted/setup-full-8.5.1.1522-x86_64.run` | 1,946,649,714 | `b1cd8dd036718c2c9046fe39cd4431715f3bc8773c40bb31f5373c762785619f` | 2026-09-24 05:52:56 |

The ZIP has 37 members and exactly one `.run` member. Streaming its contents
produced the same SHA-256 as the extracted `.run`. The two filesystem files have
different single-link inodes, so the extracted copy consumes additional disk
space; it is not a hardlink.

Repository search found no reference to `8.5.1.1522` or this directory outside
the candidate itself. The project's declared source remains
`.local/dist/Jet-1.0.3.1-tr.cf`; its runtime contract does not name 8.5.1.1522.

### Required final copies are on the executor

The established strict route is
`executor@1charness.speechbattle.com:2222`. On that executor:

- the active training runtime contract points to
  `/workspace/1c-agent-harness/.local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t`;
- the server runtime used for issue #80 contains
  `/workspace/1c-agent-harness/.local/issue80-ibcmd-100/proot-opt/1cv8/x86_64/8.5.1.1150/ibcmd`;
- the extracted `proot-opt` tree occupies **1,247,207,424 bytes**;
- the complete retained issue #80 task root occupies **3,178,377,216 bytes**;
- the executor has about 103 GiB available (27% used).

Therefore the production `8.5.1.1522` ZIP/extraction is neither the selected
project runtime nor the retained runtime that produced the issue #80 results.
The required final copy is the extracted 8.5.1.1150 runtime on the executor.
Its own 1.914 GB installer is still retained there; deciding whether to compact
the executor copy is a separate cleanup task and is not needed to recover the
production VPS.

## Container writable data

Measured top-level totals:

- `/tmp`: **573,153,280 bytes**;
- `/uv_cache`: **590,503,936 bytes**;
- combined: **1,163,657,216 bytes** (about 1.084 GiB).

The following `/tmp` entries were created by completed 1C/issue #80 research
on 2026-09-21 through 2026-09-22 and are not project state:

| Entry | Allocated bytes |
|---|---:|
| `/tmp/test13373530775469114447` | 262,029,312 |
| `/tmp/jre17` | 142,036,992 |
| `/tmp/jre17.tar.gz` | 46,645,248 |
| `/tmp/platform-context-exporter-0.1.5.jar` | 42,508,288 |
| `/tmp/issue80-platform-help` | 41,369,600 |
| `/tmp/issue80-platform-context` | 12,161,024 |
| `/tmp/processor-generator` | 11,776,000 |
| `/tmp/packBlock10311103928742735257` | 5,271,552 |
| `/tmp/pr77-review` | 4,874,240 |
| `/tmp/platform-context-exporter` | 2,764,800 |
| **Total** | **571,437,056** (0.532 GiB) |

The origin of `issue80-platform-*` and `processor-generator` is corroborated by
the issue #80 session transcript. The Java/JRE/JAR/`packBlock` entries form the
same platform-context-exporter toolchain and share the same creation window.

`/uv_cache` is a shared package cache used by unrelated tasks and sessions.
It must not be removed recursively as part of this incident. A later idle-time
`uv cache prune` can be considered separately after verifying the exact `uv`
command/version and current runtime ownership.

## Proposed deletion set requiring owner approval

### Set A — high-confidence 1C duplicate

Delete only:

```text
/workspace/1c-harnest/.local/dist/1c-8.5.1.1522
```

Expected allocated recovery: **3,873,501,184 bytes** (3.607 GiB).

### Set B — completed task-owned `/tmp` tools

Delete only the ten explicitly listed `/tmp` entries above.

Expected allocated recovery: **571,437,056 bytes** (0.532 GiB).

### Combined expectation

Expected recovery for A+B: **4,444,938,240 bytes** (4.140 GiB). Based on the
current free-space snapshot, available space should rise from about 4.275 GiB
to about 8.415 GiB. The acceptance check is the actual before/after
`df -B1` result, not this estimate.

Do not delete `/uv_cache`, any other `/tmp` entry, executor artifacts,
`.local/targets`, `.local/runs`, `state.db*`, sessions, or container data in this
cleanup.

Host-level open-file inspection was unavailable, and recursive `/proc/*/fd`
inspection is blocked by the WebUI runtime guard. The classification above is
therefore based on exact runtime contracts, repository references, executor
state, ownership, timestamps, and task provenance—not on a completed
host-wide open-descriptor proof. Immediately before deletion, re-check the
candidate identities and current `df`; if host access becomes available, also
require no open descriptors under the deletion roots. Any mismatch stops the
cleanup.

## OOM and Dashboard status

The reported 24 September host OOM and stopped Dashboard are accepted as
incident context, but the audit does **not** establish causality between that
OOM and the 1C work. Host Docker/journal access is not exposed inside the WebUI
container, and no production-host SSH credential is present in the profile.
The Dashboard process state therefore remains unverified from this session.

During this audit, a new diagnostic error occurred: a Python comparison first
streamed the `.run` member from the ZIP correctly, then called `read_bytes()` on
the 1.946 GB extracted file and was killed with exit code 137. The current
cgroup reports `oom_kill 1`. This proves only a fresh audit-induced OOM in the
current container scope. It does not identify the victim or cause of the prior
host event. No file was written or changed by this failed comparison.

Host-level follow-up should read the 24 September kernel journal and Docker
container state, record the exact OOM victim/cgroup/timestamp, and inspect the
Dashboard container's exit code/OOM flag before any start/restart. That requires
an operator-owned host route or explicit production SSH access.

## Approved cleanup result

The owner approved **Set A + Set B**. Immediately before deletion:

```text
used=33,943,867,392 bytes
available=4,587,925,504 bytes
use=89%
```

Exactly the eleven approved paths were removed. Post-cleanup verification found
none of them present. After deletion:

```text
used=29,499,064,320 bytes
available=9,032,728,576 bytes
use=77%
```

Actual recovered capacity was **4,444,803,072 bytes (4.140 GiB)**. The 135,168
byte difference from the estimate is filesystem accounting drift between the
earlier inventory and the immediate pre-delete snapshot. The retained executor
binaries were read back after cleanup:

- `.../issue80-ibcmd-100/proot-opt/1cv8/x86_64/8.5.1.1150/ibcmd`: executable,
  55,310,040 bytes;
- `.../.local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t`: executable,
  2,703,888 bytes.

`state.db` and `state.db-wal` still exist with mode `0600`; `.local/targets`
still exists. No container, Dashboard, session, shared `/uv_cache`, executor
artifact, or other `/tmp` entry was changed by this cleanup.

## Cleanup integration for future heavy tasks

Use a minimal task-owned lifecycle rather than a general cleanup service:

1. Heavy acquisition/extraction/native work runs only on the executor under one
   named `.local/<task-id>/` root.
2. Record before/after `df -B1`, exact artifact hashes, and the retained final
   locator in the task receipt.
3. Use streaming hashes; never `read_bytes()` for distribution-sized files.
4. In `finally`, remove only declared disposable paths. Preserve evidence and
   the selected runtime explicitly.
5. End every heavy task with a dry-run inventory containing path, owner, bytes,
   mtime, retention class, and reason. Any ambiguous/shared path remains.
6. Add a fail-closed admission check on the production VPS: refuse 1C
   distribution download/extraction there unless the task explicitly names the
   production host and records a free-space budget plus cleanup plan.
7. Prefer a per-task TTL marker and a later report-only sweeper. Do not run a
   broad recursive cleanup hook over `.local`, `/tmp`, or `/uv_cache`.
8. Verify cleanup with actual `df -B1`, retained-artifact existence/hash, and a
   closed deletion set.
