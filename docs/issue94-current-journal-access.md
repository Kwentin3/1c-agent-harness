# #94 — persistent access to the current demo journal

**DONE / ORDINARY_HERMES_PERSISTENT_ACCESS_PASS.** Contract: [operator task #94](https://github.com/Kwentin3/1c-agent-harness/issues/94).
The owner approved the restricted entry/config and read-only mounts on 2026-10-07.
The installed capability is source commit `cd0100aa5312fb7411d16dc56caa0bd3277990a3`,
LF SHA256 `adc0ee5c6513bf873783750e3b32c8048309df179657b747cc476920859d1646`,
in [PR95](https://github.com/Kwentin3/1c-agent-harness/pull/95).
This access prerequisite leaves the exporter/reader and product acceptance of
[#90](https://github.com/Kwentin3/1c-agent-harness/issues/90) with Hermes.

## Actual source and execution boundary

Retained reference `d2f38aa86d7bc461712df72fc22d5eb924324cbf5f386ca44a458024fd24970c`,
image `sha256:69f919497cada9a8611f3de61df902d9f94bf20f84552ef5bd93125c38608ef9`,
is running under `1c-jet-demo.service`; PID 2763670 and start
`2026-10-07T06:33:35.714659532Z` remained unchanged throughout provisioning.
The existing owner URL is https://1c-demo.speechbattle.com/jetcontrol/ru/.

The active VRD `/var/www/jetcontrol/default.vrd`, SHA256
`e5406c8e7352b43c6499e2ff4fe189c9b239fe045eb0ac46de2960555850ac7d`,
binds `File=/var/lib/1c/ib`. Its `1Cv8Log` is the current source; demo service
UID/GID 33 owns the IB/log, timezone UTC. The source directory's device 71/inode 6180626
matches inside demo and the read-only worker mount. At handoff it contains LGF
and two LGP files, 688417 bytes; the non-native probe reads 16 bytes from each file.
This is a direct live mount, without a copied slice or an archive substitution.

Each request checks exact reference/image, active service and exact VRD, then
resolves the current journal through Docker's `GraphDriver.MergedDir`.
Storage driver must remain `overlay2`; unexpected identity/driver fails closed.
Only the journal and already installed official ibcmd directory are mounted,
both read-only. The worker uses existing image
`sha256:036a932ca78ec1f161b83fc3d26d663d950a8e845002c160771950ec72ce6488`,
UID 10001/GID 33/groups [33], UTC, read-only root, zero capabilities, no network,
Docker socket or IB mount. No runtime was installed or copied to Hermes.

Exact official ibcmd 8.5.1.1150 is mounted with its existing native libraries/resources,
binary SHA256 `62e72e15bb4550c4ffcf421f962c27fd1e1ddde1ba31e5bc0d7c9e0c2352dde7`.
Configured task output/HOME/TMP use 32 MiB tmpfs `/work`; output≤1 MiB, native≤30 s,
controller≤40 s plus exact helper cleanup, 1 CPU/256 MiB/128 PIDs. The worker performs
safe write-open denials on the journal and `/etc/passwd`, without write/truncation,
and creates/removes its canary in `/work`.

## Ordinary Hermes invocation

In Hermes' existing WebUI terminal, use the separate pinned SSH config:

```sh
ssh -F /data/hermes-home/credentials/ssh/current-journal/config -T current-journal "current-journal-v1 BASE64_TOKEN"
```

`BASE64_TOKEN` is base64 of a UTF8 task-owned request file. Capture stdout/stderr
privately before inspecting receipt metadata; raw payloads stay outside Git/chat.
Config SHA256 `4a39fa3a87e40979ebd4925ec501b5996ca78c24eac587a01409169dbc473fff`.
It uses the existing diagnostic identity and pinned SSH ProxyJump through the old
executor. One home authorized-key entry enforces fixed command, restrictions and
the admitted jump source. The revoked coding key remains unused.

Probe: `{"schemaVersion":1,"operation":"probe"}`.
Export has exactly `schemaVersion`, `operation:"export"`, `start`, `end`, `format`,
`followMilliseconds`. Times are UTC naive ISO seconds; range 0–86400 s, format json/xml,
follow integer 0–1000 ms. No source/runtime/output path, arbitrary argv or shell.
An extra source/output field or `id` is rejected with exit 2 and native 0.

Export invokes fixed `ibcmd eventlog export --format=... --skip-root --from=...`
`--to=... --out=/work/eventlog.FORMAT [--follow=...] /source/journal`.
The receipt preserves argv, timestamp/duration/exit, bounded output/hash/bytes,
stdout/stderr metadata and before/after source inventory. Acquisition consistency
is explicitly `NOT_PROVEN_BY_ACCESS_CAPABILITY`; access does not prove rotation,
freshness, coverage, selection/page/record or #90 product acceptance.

## Hermes acceptance and retained access

Current ordinary Hermes session `1944872b1f4a` performed the
[first access witness](https://github.com/Kwentin3/1c-agent-harness/issues/94#issuecomment-6035780751):
probe and three source/output/shell refusals passed; one export was charged to the
existing ledger before invocation. Native/SSH exit 0, native 5.238867317 s, wall 11.629884855 s.
Request UTC 2026-10-07 09:55:46 to 10:10:46, JSON/follow 0; output 0 bytes, empty SHA256. Inventory
before/after matched. An empty output does not prove absence of events or full coverage.
Full protected receipt SHA256 `ce21adf5f24764a503d13c3a2c5398d3f52fa64e6a59c58e3a0ac44f412b0be3`.

After [explicit operator cleanup](https://github.com/Kwentin3/1c-agent-harness/issues/94#issuecomment-6035822105),
Hermes personally repeated the same route at 2026-10-07T10:17:01.765996Z:
[post-cleanup persistent access PASS](https://github.com/Kwentin3/1c-agent-harness/issues/94#issuecomment-6035866327).
SSH exit 0, wall 6.629503134 s, native 0. Probe SHA256
`7836984342ccab7565efb12057709daf65bf23236bab28331dff5e353cb4a0bc` was byte-identical
to the first witness. The three safe refusals passed again. Canonical ledger and
contract were read back unchanged; no second export/help/session occurred.
Post-cleanup private receipt SHA256
`b596742ee3e24b772669e778fe55fd2352a82fae822fcd98fb7e5b5b926b2c98`,
manifest SHA256 `2a527d2dfcbad47ce7380d38754d8c42744ef40b28fe63743a3f34c486ae40c4`.

Budget after witness: help 2/3, export 1/12, session cycles 0/2, native 5.773221766 s/900 s.
Canonical ledger SHA256 `6bf7d25627e27424035aac92e3be3b75f90c1ab2284afe19d404f27fe883ab14`;
contract SHA256 `325fbdc242d96de33774474408ce1482cb83806ab543ad398a1a7e751461fd8f`.
Private Hermes evidence: `/workspace/1c-harnest/.local/issue94-access-intake/`,
directory 0700/files 0600; requests, receipts, payload, ledger reservation/readbacks
and manifest remain protected there. The exact installed handler hash is operator
attestation; Hermes independently read the config/source candidate and actual
restricted-route source/runtime receipts.

Operator native invocations: 0. Hermes owns the canonical ledger on the existing
diagnostic executor, `/workspace/1c-agent-harness/.local/issue90-current-source-rnd/ledger.json`.
No ledger reset or duplicate native witness occurred. #90 remains open.

All transient issue94 workers/processes are removed after calls. There are no new
timers/services or a retained worker. Demo was not stopped/restarted/recreated;
its auth/logging/config/business data and old diagnostic/coding bindings remain.
The existing Hermes launcher and WebUI were not changed/restarted.

Persistent resources: one forced key entry; home
`/home/roman/.local/issue94-current-journal/current-journal.py` (root-owned 0555)
and caller-owned lock; separate WebUI `credentials/ssh/current-journal/config`
and pinned known_hosts. There is no expiry timer. Home operator owns deployment,
rotation and revocation, using the existing protected credential mechanism.

After calls end, revoke only the authorized-key line marked `issue94-current-journal`,
then the separate config/pins and handler/lock. Preserve unrelated entries rather
than restoring an old whole file after intervening changes. Exact pre-change
authorized_keys and source backups are protected under the home task's
`.operator-backup/`; no key bytes appear in this document/evidence.
On planned restart of the same retained reference, the next request resolves its
current PID/MergedDir; a changed CID/image/VRD/driver fails closed for the operator.
Restart recovery was not exercised because demo must stay available.

## Validation and protected evidence

Seven focused tests exercise actual forced-command admission refusals without
Docker/platform calls. The module, embedded worker and actual VRD probe compile;
the installed source matches Git's LF bytes. Exact code candidate passed
[Python 3.9/3.12 CI](https://github.com/Kwentin3/1c-agent-harness/actions/runs/37605109200).

Operator private evidence: `.local/issue94-20261007/` in the comfyUI workspace;
`operator-evidence-manifest.json` SHA256
`4802a7ae81494a7f21b7f62e38abfae97a37983d451b215ed5743aaefc778c08` provides an allowlist of identity/provisioning/parity checks,
CI, direct handoffs, ordinary Hermes public receipts and protected evidence metadata.
Raw journal output and private credentials are retained only in protected task
storage. Published evidence contains locators/hashes and no raw journal/key bytes.

Source binding follows the documented [1C file-IB journal layout](https://kb.1ci.com/1C_Enterprise_Platform/FAQ/Administration/DBMS/Data_structure_in_1C_Enterprise_8/?language=en).
Protection uses native [Docker read-only bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
and [OpenSSH forced-command restrictions](https://man.openbsd.net/sshd.8).
