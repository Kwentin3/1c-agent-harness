# Remote executor topology gate

Use this before any 1C materialisation, snapshot opening, or native-budget attempt when canonical inputs are expected to live outside the current Hermes host.

## Read-only discovery

Collect only non-secret topology evidence:

1. Identify the active Hermes terminal backend and whether commands are local or remote.
2. Inspect the effective SSH/backend configuration for the presence of an actual destination and identity reference. Record filenames, permission modes, backend name, and non-sensitive aliases; never print private-key, token, or config contents.
3. If an AgentBridge device inventory is available, treat it as inventory rather than an execution channel. A device is usable only when its status is operational and its contract exposes a handoff/command boundary.
4. Check the target executor itself only through an already configured route. Verify the repository root, canonical target locator, runtime locator, and source identity there.

## Decision rule

Separate **executor-topology admission** from **plugin-product admission**.

A real executor is topology-admitted when all of these are evidenced:

- a reachable, deployment-owned transport — either the Hermes-selected backend **or** an already established direct SSH route with its own pinned-host policy;
- a known remote workspace/repository root;
- a non-secret identity reference owned by the deployment; and
- a target/runtime admission check performed on that executor.

A direct SSH route can therefore prove where the canonical 1C runtime and data actually live even while the current Hermes terminal backend is `local`. It does not by itself prove that a future plugin operates through the active Hermes workspace/backend.

Plugin-product admission additionally requires the selected Hermes terminal boundary to reach that same remote executor and task workspace under an equivalent host-verification policy, followed by a distinguishing workspace-bound canary.

A device marked pending enrollment or a context entry with `handoff_available: false` is not an AgentBridge execution route. It also does **not** disprove a separately evidenced SSH route. Conversely, an SSH configuration without a reachable destination is not an executor. Do not infer an endpoint from a device name, historic local receipts, or a remembered home machine.

## Fail-closed SSH backend canary

When a deployment claims that a mounted `known_hosts` file and a profile policy make the built-in SSH backend strict, do not infer that the backend actually consumes that policy. Before changing generic terminal code or touching 1C, run a no-1C canary through the backend's real SSH command builder in the deployment context.

Use an exact pre-existing deployment pin and an isolated temporary known-host file for the test only; never print host keys, fingerprints, private-key values, endpoint addresses, or config contents. The three required observations are:

1. The exact pre-pinned target/key succeeds and does not mutate the test file.
2. A syntactically valid different key for the **same target and the server-selected key algorithm** is rejected, without mutating the test file. A random key of another algorithm is not a valid substitution oracle: SSH can negotiate a different host-key algorithm.
3. An absent pin is rejected. If it succeeds and writes a new record, the backend permits TOFU and does not satisfy a strict deployment policy.

Isolate both connection and host-key state per case. SSH ControlMaster can reuse a previously authenticated connection and hide a later mismatch; disable it or use a distinct control socket for every case. Also pass an explicit temporary `UserKnownHostsFile`: setting `HOME` alone may not affect OpenSSH's expansion of `~` for the effective account. Confirm that persistent user known-host files were unchanged after the canary.

A mount merely existing is not enough: confirm that it has an applicable pin for the exact host/port form selected by the backend. If the canary shows TOFU, the minimal product remedy is a generic terminal configuration seam that passes one configured known-host file plus `StrictHostKeyChecking=yes` consistently to both `ssh` and `scp`; it must fail closed when only one half of that policy is configured. The 1C plugin must still not know host-key paths or open SSH itself.

## Failure handling

If neither a direct route nor a selected remote backend can be evidenced, report `context blocked` before creating a local lab, copying a CF/snapshot to the VPS, or writing a parallel remote runner. The minimal unblocker is the owner-provided/enrolled execution route; after it exists, rerun this gate from scratch. This is an access/topology blocker, not a failed native attempt and consumes no native budget.

If direct SSH establishes topology but the selected Hermes backend cannot carry its pinned host verification or selected workspace, report that precise public seam as a product blocker. Do not bypass it by embedding SSH in the plugin.

## Boundary selection

Prefer Hermes' selected terminal backend as the single **product** execution boundary. Before declaring it unavailable to a plugin, inspect the documented `PluginContext.dispatch_tool()` contract and whether `terminal` resolves task/session CWD; a public dispatch seam may exist even when plugin handlers do not receive a filesystem object. A plugin must not reach into private environment state or implement a second SSH execution path. If a new backend is genuinely needed, use Hermes' documented terminal-environment provider interface and separately prove it before native work.
