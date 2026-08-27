# Independent acceptance review of a frozen 1C snapshot

Use this protocol for a second-human/dual-agent acceptance lane where independence from an existing answer, oracle, ledger, or review package is part of the evidence.

## Independence boundary

1. Record the supplied snapshot root, manifest path, and expected content ID.
2. Before interpreting source, verify the manifest digest and every covered file. Require a closed set when the contract promises one: manifest count = actual-file count, with zero absent, extra, or digest-mismatched files.
3. Do **not** open existing answers, oracle, adjudication ledger, evaluation narrative, issue comments, or primary-review notes yet.
4. Search the snapshot from self-chosen product terms. Inspect original XML/BSL and cite exact inclusive `path:start-end` locators. Do not use object names alone as behavioral proof.
5. Build a complete independent view covering:
   - configuration identity and stated purpose;
   - main domains and metadata map;
   - integration surfaces;
   - one meaningful end-to-end static business chain;
   - runtime unknowns;
   - dangerous or unsupported claims.
6. Separate every substantive statement into **fact**, **inference**, or **unknown**. A static chain is never a runtime test.
7. Freeze the independent view before package comparison. When repository writes are forbidden, write it outside the repository (for example under `/tmp`) and record its SHA-256. This creates an auditable independence checkpoint without mutating the candidate.

## Package comparison after the freeze

Only after the independent-view hash exists:

1. Verify the review-package manifest and count the oracle denominator programmatically.
2. Compare for both directions:
   - package facts missing from the independent view;
   - independent findings missing from the package;
   - source-level contradictions;
   - narrower/broader claim scope;
   - dangerous claims not represented in the oracle.
3. Keep **natural-language task satisfaction** separate from **exact oracle-item alignment**. If a visible question permits any valid example but the oracle hard-codes one example, a correct substitute is a construct mismatch, not a source error. Likewise, a conjunctive oracle item can lose exact-item credit for one omitted component without making the stated components false.
4. Treat a package score as oracle alignment unless the task/oracle construct is demonstrably equivalent. Report source correctness separately.
5. An independent reviewer may add a material security or logging risk even when it is outside all frozen oracle items; absence from the oracle is not exculpatory.

## Static 1C claim boundaries

- `ConfigurationExtensionCompatibilityMode` is not the observed runtime platform version.
- HTTP service metadata does not prove publication, route reachability, or successful requests.
- Adapter code does not prove configured credentials, reachable external systems, or successful integration.
- `ScheduledJob` XML proves static `MethodName`, `Use`, schedule, and retry metadata only—not effective production state or execution history.
- For JWT/Bearer review, trace the visible request path. Token issuance/signing elsewhere does not prove request-time cryptographic signature verification.
- Check denial/error logging for full bearer tokens or other secrets; this can be a material independent finding even when authentication semantics match the oracle.

## Final continuity gate

Make the final snapshot operation an unconditional re-verification of:

- manifest SHA-256;
- all entry digests;
- manifest/actual closed-set counts;
- zero candidate-path Git changes when applicable;
- frozen independent-view hash.

Do not inspect candidate files after this gate. Report any non-repository temporary artifact separately and state that the repository/snapshot remained unchanged.