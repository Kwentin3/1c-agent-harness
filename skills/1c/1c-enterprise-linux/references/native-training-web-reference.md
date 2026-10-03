# Native training web reference: preparation and daily acceptance

Use when preparing or admitting a **file-mode Linux training web publication**.
This is a narrow observed route, not a deployment framework or a license promise.
Separate administrative preparation from the ordinary read-only agent workflow.

## Evidence boundary

Observed: Ubuntu 24.04 amd64, training **8.5.1.1150**, package Apache
**2.4.58-1ubuntu8.15**, native installation under `/opt/1cv8t`, one-process
worker MPM, an isolated file-IB copy, loopback, and a declared hardened derivative
of publisher output. The unadapted installation reproduced native language-resource
404; the two-resource adaptation below then enabled native UI, empty-day Dashboard,
Refresh and a fresh session after a full container stop/start.

This does **not** prove nonzero business arithmetic, midnight rollover, RLS,
other OS/builds, byte-identical publisher defaults, public ingress, fresh-agent
web reproduction, or the CF Designer lifecycle on this particular new runtime.
Exact receipts and acceptance scope belong to the repository experiment evidence;
this reference owns only reusable mechanics. Do not infer a new administrative
permission from this document.

## 1. Admit the real execution environment

- Check actual OS/architecture, available runtime and target, source identity,
  storage/RAM, current sessions, and the established pinned execution route.
- For an already prepared environment, perform ordinary read-only admission;
  do not reinstall, relocate the platform, or launch privileged publication.
- For a new environment, obtain bounded operator authority for one separated
  target, package installation, publisher, test copies and agreed restart.
  No permanent sudo/Docker socket, host packages, public ports or shared-service
  changes follow from it. Missing administrative access is a concrete prerequisite,
  not a reason to replace native installation with unproven local library assembly.
- Task data/evidence stay in the task's ignored `.local/` area. Installed software
  may remain root-owned in its vendor/package paths **inside the admitted target**.
  Retain originals, demo/backup and unknown artifacts; cleanup only owned temporaries.

## 2. Operator preparation, not model-facing harness functionality

Stage the legally obtained installer in a root-owned non-user-writable directory;
check its trusted identity there before root execution. For the observed distribution,
installer SHA-256 is
`396b7065b9efb6272093f1bda5eab647081a13d9ccbb4c5cfb0e711346d5af28`.
Retrieve exact help first. The verified command shape was:

```sh
<protected-installer> --installer-language en --mode unattended \
  --unattendedmodeui none --enable-components client_full,ws,ru \
  --disable-components v8_install_deps,desktop_icons \
  --debugtrace <task-evidence>/installer-debug.log
```

The packaged Ubuntu dependencies used were `apache2`, `fontconfig`,
`fonts-dejavu-core`, `libwebkit2gtk-4.1-0`, `libgl1`, `libglu1-mesa`, `libsm6`,
`libx11-6`, `libxxf86vm1`, `libgtk-3-0t64`, `libcups2t64`, `libenchant-2-2`,
`xvfb`, `xauth` (plus ordinary Python/CA/network tools). Do not use this list as
an ABI matrix for all releases. Record repository sources, complete package versions,
installer help/argv/exit and installed hashes. Prevent package auto-start before
loopback/service-user configuration. Do not auto-accept new licenses/font EULAs.

Check `ldd` on `1cv8t`, `webinstt`, `wsap24t.so` **without** a cross-release
`LD_LIBRARY_PATH`; rc0 alone is not enough—there must be no `not found` lines.
That still does not check every dlopen or web route. Keep installed vendor files
root-owned, with no group/world write, and do not move/chown the native runtime
into a user-writable task tree for this web scenario.

Quiesce the source safely, then physically copy the IB to the admitted target.
Do not copy live mutable database files, locks or temporary sessions. Never mount
the source/demo/backup/CF/snapshot writable into the experiment.

Prepare matching Apache architecture/module and one worker process. Publish using
the exact build's native `webinstt -publish -apache24` with explicit publication
name/directory, scratch file-IB reference and actual config path. This observed
build requires the separately admitted UID-zero publisher. Preserve generated
Apache config and VRD **before** hardening; record every derivative change.

The tested derivative kept the generated base (without adding a slash), Alias,
native handler and module. It disabled unnecessary WS/HTTP/OData/analytics and
`AllowOverride`, selected loopback and worker MPM, and provisioned HOME/log/run/lock
and IB access for the unprivileged service user. Do not claim unchanged defaults.
Verify syntax and module admission in the real service environment.

**Service identity includes groups:** setting UID alone can retain GID0 and fail
protected VRD access. Use the admitted UID, primary GID and supplementary groups;
verify actual parent/worker identity. A permission failure before restart is not
restart acceptance.

## 3. Exact-build resource-discovery adaptation (operator only)

Symptom: native root HTML chooses a language prefix, while flat bootstrap JS is
200 and language-prefixed JS returns platform JSON404. This exact build enumerates
`vrscore*_*.res` but parses a fixed `vrscore` prefix; the installed training names
`vrscoret_root.res`/`vrscoret_ru.res` do not match that parsing assumption.
The retained reverse-engineering evidence plus remove/restore causal control
support this local finding, not an official vendor defect notice for every training
version. Do not respond with repeated slash/locale/rewrite experiments.

Only for the verified **8.5.1.1150** bytes:

| Required file | SHA-256 |
|---|---|
| `vrscoret.so` | `29aee4993151419c206bc42dba288e5fdd7ac8b8a70a994023fc5a65131a9612` |
| `vrscoret_root.res` | `2ecc4a5ab85fabd5d56d1c1cb8355d06323f22c954d970d28c528f8154f2525c` |
| `vrscoret_ru.res` | `fd1cbe9d0fa6e9c2d0f319a580a98d5155302aa84f1535d6e6a507124a832b14` |

Before any mutation, check exact version, target hashes, regular-file identity,
root ownership and non-writable ancestors/runtime, and absence of both proposed
names including dangling symlinks. If one name exists unexpectedly, STOP; do not
replace it or use `ln -sf`. On an already adapted runtime, admit only the exact
relative links and matching targets; no write is needed.

Within the operator's approved native runtime directory only:

```sh
ln -s vrscoret_root.res vrscore_root.res
ln -s vrscoret_ru.res vrscore_ru.res
```

Record these two additions separately from the immutable original-file manifest.
Do not introduce foreign resources, binary/HTML/JS patches, UID hooks or request
rewrites. This is a declared compatibility adaptation, **not an untouched vendor
installation**. Restart only the task Apache under the complete service identity,
then check native flat and language-prefixed script status/body hash and actual UI.
Do not apply to a new version from its name alone; test the unadapted native route
first and retire the adaptation when no longer required.

Rollback: quiesce the task service, verify both links' exact names/relative targets
and ownership, remove only those links, then perform the agreed restart. Original
files are never renamed, deleted or edited. A negative control is expected to
restore this build's 404; it is not ordinary operational rollback acceptance.

## 4. Daily agent acceptance, not publisher acceptance

1. Use the existing prepared access route; no guessed remote/loopback replacement.
2. Preserve source/snapshot identity and create only admitted task data.
3. Require native language bootstrap, real client UI, the actual report date and
   business values. Publisher rc0, Apache syntax and initial HTTP200 are prerequisites.
4. Trigger the real Refresh command and retain request/response/trace plus before/after
   server report witnesses. For native tabular output, inspect its iframe response,
   not only outer DOM. Screenshots are supplemental, not the agent's primary interface.
5. After the operator's agreed restart, use a fresh browser context, confirm persisted
   copy state and repeat the report/Refresh. Separate empty-day from nonzero oracle.
6. Account browser response-event ledgers and trace resource-snapshot counts separately:
   they need not be equal. Keep failed intermediate controls and original budgets.
7. Preserve demo/runtime and stop only task-owned controls as agreed. Report source
   checks, externally attested host actions, live checks and unknowns separately.

Keep `open → SnapshotRef → narrow/verify` with the existing companion/transport.
The executor injects the **absolute** `ONE_C_HARNESS_RUNTIME_CONFIG` path; it is not
inferred from cwd or project metadata. Schema v1 remains `platform`, `xvfb`,
`fontconfig`, `libs` plus `schemaVersion`; for a native packaged runtime, a real
vendor libs directory and system fontconfig/Xvfb may satisfy path admission, but
that alone does not prove a cold CF/native cycle. Do not create a second installer,
runtime registry, SSH wrapper or harness to make this web recipe discoverable.

Public ingress/authentication, production rollout, merge and new license decisions
are separate gates. A fresh agent reading this procedure is discovery evidence;
web reproducibility requires that agent to exercise the prepared native target.
