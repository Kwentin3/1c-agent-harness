# External EPF via `ENTERPRISE /Execute`: read-only feasibility audit

Use this before admitting an external data processor (`.epf`) as a headless transport candidate. This is a **capability audit**, not authorization to launch 1C or modify a harness.

## Keep three claims separate

1. **Platform syntax.** Cite the official command-line documentation for the exact platform version when accessible. A documented generic form is typically:

   ```text
   <client> ENTERPRISE /F <disposable-file-IB> /Execute <epf-path> [/C <string>] ...
   ```

   Do not call this exact-runtime support until the target executable/version is present and its applicable documentation or a bounded smoke confirms it.

2. **Repository transport support.** Inspect the actual runner schema, CLI arguments, and argv builder. A runner that hardcodes `ENTERPRISE /F` and exposes only `/C` does **not** support `/Execute`, even if the platform does. State the first concrete locator that excludes an EPF path or arbitrary runtime argument.

3. **Protocol sufficiency.** Opening an EPF, a zero process status, or Designer load success does not prove its entrypoint ran, a request crossed client-to-server, or server code executed. For a required server witness, require independently bound client and server receipts, a server-generated token produced after server entry, and static closure evidence that only server-side instrumentation names the witness path.

## Official-document evidence boundary

When the exact-version ITS page is reachable but its detailed body cannot be recovered (for example, an encoding-sensitive table of contents is retrieved without the parameter clause), record only the document identity and version. Do **not** upgrade a secondary or older-version `/Execute` synopsis into an exact-build fact. Keep these labels distinct:

- **exact-build verified:** an observed invocation/receipt or exact-build source that states the fact;
- **version-family documented:** an official applicable major/minor page with the recovered clause;
- **documentation hypothesis:** a secondary source or another-release documentation describing launch of an *existing* EPF.

The last label supports only a candidate question. It does not prove headless EPF construction/export, non-GUI dispatch, parameter visibility, or a server witness.

## Read-only admission checklist

Before consuming a one-smoke budget, establish all of these:

- exact runtime executable exists at the path the runner will invoke; an installer/archive is not an installed runtime;
- project target identity verifies and the declared immutable source/snapshot paths are present;
- a disposable EPF exists or a deterministic, authorized EPF build/export path is already available;
- preflight can freeze the EPF hash and exact `/Execute` argv;
- the selected runner can carry `/Execute` without bypassing its supported public interface;
- parameter binding to the EPF and its non-GUI entrypoint are documented or explicitly remain capability questions for the single smoke;
- the prepared closure can prove no business object creation/write/posting APIs and excludes forbidden scenario identifiers;
- receipt ownership, stable terminal parsing, and bounded process cleanup satisfy the frozen protocol.

If any item is absent, report `CONTEXT BLOCKED` or a capability failure—not a platform incompatibility—and do not substitute another transport inside that arm.

## Minimal honest result language

- **Admitted but unproven:** platform documentation supports the syntax, while EPF dispatch/parameter visibility/server reach remain for the one bounded smoke.
- **Repository-blocked:** the platform may support `/Execute`, but the repository's supported runner cannot express or verify it.
- **Runtime-blocked:** the exact client or declared target identity is unavailable, so no exact-runtime claim or disposable smoke is possible.

Never infer a universal limitation from a missing local runtime or inaccessible documentation page; record it only as the current audit boundary.
