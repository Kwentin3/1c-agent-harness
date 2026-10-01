# Observable headless server probes

Use this reference when a native 1C experiment must execute server-side code from a headless managed client and preserve useful diagnostics.

## Verified narrow route

In a disposable file IB on the training edition, an instrumented managed application module can:

1. enter `OnStart` when `/C <receipt-path>` is nonblank;
2. write a client-side stage receipt;
3. synchronously call an exported procedure/function in a common module declared `Server=true` and `ServerCall=true`;
4. create/write ordinary fixture objects on the server and call a document object's real `Fill(Source.Ref)` method;
5. append client observations only after the server call returns; then write a terminal completion marker and `Return` before standard subsystem startup.

This proves only that bounded early-return route. It does not prove normal application startup, interactive behavior, or business semantics.

## Recommended probe shape

Keep three layers separate in the disposable prepared copy:

- **Production change:** only the authorized target BSL module.
- **Client instrumentation:** `OnStart` and a receipt writer in `Ext/ManagedApplicationModule.bsl`.
- **Server instrumentation:** one exported server-call procedure/function in a dedicated server-call common module.

For a multi-case business probe, execute **one server call per case**. The client appends a case's observations only after that call returns. A terminal receipt then shows exactly which cases returned before a later timeout/error; do not infer results for an unreturned case. The runner's declared, descriptor-bound client receipt is the acceptance channel. A server-side sibling file is optional forensic evidence only; never treat it as a substitute for a complete client receipt.

Return actual primitive observations (for example booleans about header values and real tabular-row fields) from server code. Do not pass expected outcomes into the server function; compare returned observations with the frozen contract outside the product path.

## Compile boundary pitfall

A successful `DESIGNER /LoadConfigFromFiles /UpdateDBCfg` proves the platform accepted the configuration, but it may not compile every managed-client instrumentation path. A BSL syntax error in a procedure reached only at client startup can therefore appear later as ENTERPRISE exit with no receipt.

Before spending a business RED/GREEN budget on newly written instrumentation, run a separate small disposable smoke that invokes the exact client procedure and its server-call boundary. Its receipt must use a unique terminal marker. Treat a runtime compile error as an instrumentation failure, not a business result. When `/Out` names a generated-module line, preserve that locator as a symptom; do not claim which subexpression or BSL rule caused it until a separate minimal compile smoke isolates the cause.

For exception diagnostics in temporary BSL, prefer a minimal constant error marker unless a syntax/API pattern has been verified in the same configuration. Do not make receipt emission depend on unverified exception-formatting helpers.

## Evidence to retain

For every such probe, retain under `.local/`:

- frozen contract SHA-256;
- prepared-tree changed-file closure and base/prepared hashes;
- exact `OnStart` excerpt proving `Return` precedes standard startup;
- exact server-call excerpt proving the invoked production method and source reference;
- raw client receipt, any server diagnostic receipt, native result JSON and `/Out` log;
- prepared input before/after identity and canonical target continuity.

This is a troubleshooting and observability pattern, not authorization to alter canonical source or to rerun a failed frozen contract.
