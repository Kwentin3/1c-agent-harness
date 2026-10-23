# Goal90: ordinary-chat access to current ЖР and ТЖ

Owner refinement in Hermes WebUI: prove the agent's access to the registration
journal (ЖР) and technological journal (ТЖ) of the running training demo.
A native 1C agent/client is a hypothesis, not a prescribed installation.
Continue Goal90, handoff96 and PR93; do not create a duplicate Goal or reset its
ledger. Heavy execution stays on the home executor. No new review cycle.

## Evidence from this continuation

- Current-journal restricted non-native probe: ACCESS_PROBE_PASS, 6.441055 s;
  wire SHA256 `7836984342ccab7565efb12057709daf65bf23236bab28331dff5e353cb4a0bc`,
  identical to accepted post-cleanup witness. It proves continued access, not
  fresh-event detection, capture consistency or completeness.
- Canonical ledger unchanged: SHA256
  `86d8fc3551e2c81ca841fa455633ca42f013221a0dc73b81547893d9943fc24d`,
  help2/3, exports4/12, sessions0/2, native8.480200893012807/900 s;
  pending STARTED0. This continuation spent native0/export0/session0.
- Registered `one_c_observation_info` succeeds: UTC, three files, 47170 bytes,
  EXCP/EXCPCNTX, observed interval
  2026-09-18T15:25:25.291000+00:00–2026-09-18T15:26:22.170000+00:00.
  This is retained historical TechLog access, not proof of current demo ТЖ.
- Existing diagnostic executor has executable training 8.5.1.1150 `1cv8t`,
  `1cv8ct`, `1cv8st` in its declared runtime directory. `ragent`, `ras`, `ibcmd`
  were not present **in that directory**; no global absence is asserted.
  Current-journal capability already runs a separately mounted official ibcmd.
- Diagnostic mount inventory does not expose `/var/lib/1c/ib`. The current-journal
  worker intentionally mounts only the current journal and official ibcmd, not
  the IB (operator contract PR95). Existing diagnostic `web-demo/demo-ib` is
  historical and must not be used as a substitute.
- No `logcfg.xml` was found under the diagnostic training-platform directory.
  This does not establish whether the separate running demo has a configured ТЖ.

Private exact inventory/probe receipts: task-owned
`.local/issue90/native-access/{inventory.stdout,probe.stdout,receipt.json}`.
No raw records or credentials are published.

## Minimal remaining environment prerequisite

Home deployment owner should expose a bounded native session capability **inside
or legitimately connected to the current demo environment**, with identity bound
to the admitted current reference/VRD. Reuse installed native software first;
do not install a cluster agent merely because it is named an agent.

The capability must permit only the two already authorised ordinary login/logout
cycles, report their lifecycle and cleanup, preserve other sessions and demo
availability, and make no business/configuration/logging-policy writes. Check
startup side effects and training session limits before admitting a cycle.
Read-only journal access does not confer IB/session access. Do not provide root,
Docker socket, a writable IB mount to diagnostics, broad shell access or secrets
in Git/chat. If authentication is necessary, use the existing native secret source.

In the same bounded read-only discovery, identify whether the running demo already
produces a ТЖ and whether it can be safely read and bound to this same reference.
If absent or inaccessible, report that fact; logging activation needs a concrete
separate decision and is not silently included. No synthetic error or business
write is authorised just to produce a ТЖ event.

## Still separate acceptance gates

The matched plugin/companions/dispatcher are staged, not activated. Supported
between-run WebUI lifecycle remains mandatory; no active-run restart or registry
patch. Registered fresh ЖР select/page/record/comment and repeated new-event
acceptance remain NOT_RUN. Current-demo ТЖ access/coverage remains UNKNOWN.
Historical full selections17.05–18.83 s still exceed10 s; no improved latency is
claimed. No new exports were spent merely to repeat historical events.

Verdict: **PARTIAL / ENVIRONMENT PREREQUISITE**, not PRODUCT PASS. No installation,
demo restart, policy change, native coding, merge or release occurred. Preserve
all earlier evidence, rollback and immutable inputs.
