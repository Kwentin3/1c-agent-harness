# Post-adjudication native provenance remediation

The independent Jet adjudication correctly reported that the first receipts named mutable work-copy paths but did not content-bind the exact input tree. Those original runs remain historical evidence only.

After that finding, both arms were replayed in new disposable infobases with receipt schema v2. Before invoking 1C, the runner:

1. verified the immutable 5,099-file snapshot against manifest SHA-256 `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`;
2. hashed every work-copy file into a canonical sorted manifest;
3. required exactly `Catalogs/Warehouses.xml` to differ, with no missing, extra, or symlink entries;
4. bound the public task ID, snapshot content ID, published patch/diff hashes, the sole diff-header path normalization, changed owner bytes and complete work-copy manifest before invocation;
5. retained exact argv and relevant environment in the local receipt, then published the same structure with one `${REPO}` placeholder;
6. required process exit 0, exact-zero DumpResult and an actual success marker for both create and load;
7. reverified immutable snapshot closure after execution.

The public package retains, in explicit Base64 transport:

- the host-path-sanitized v2 execution receipt for each arm;
- the complete immutable source manifest;
- original and per-arm changed owner XML bytes;
- sanitized create and load logs;
- exact DumpResult bytes.

`tests/test_issue12_evidence.py::test_native_receipts_bind_exact_inputs_commands_and_outputs` decodes these bytes, verifies fixed sanitized receipt/output anchors outside the refreshable package manifest, validates all hashes and markers, parses strict single-file/single-hunk unified diffs, enforces declared old/new counts, and applies only the declared header-path normalization. Record terminators are framing rather than a content transform: the published patch retains CRLF payload bytes required by the CRLF source, must pass real `git apply --check`, is applied byte-for-byte, and must produce the retained changed owner bytes. The test then reconstructs the complete 5,099-file work-copy manifest hash and validates the complete arm-specific CREATEINFOBASE/DESIGNER argv, normalized confined run/work-copy paths, and environment contract. Integration negatives mutate patch, diff, changed owner/work-copy identity, receipt binding, consuming work-copy path, and retained outputs, refresh the package manifest, and still require fail-closed rejection.

The local unsanitized receipts are not published because they contain host paths. Their former bare SHA-256 fields could not authenticate the sanitized derivation without the raw bytes, so those fields and that claim were removed. Public verification is deliberately limited to the exact committed sanitized receipt/output bytes anchored by the exact Git tree.

A decoded-payload privacy test rejects unexpected absolute host paths. The sole explicit exception is the two path values inside `tasks/sdms-frozen-original.json.b64`: those exact bytes are required to reproduce the pre-arm task digest and are mechanically normalized to repository-relative values before comparison with the published task. Native receipts and logs have no such exception.

This remediation supersedes only the provenance caveat at `adjudication/jet-review.md:71-72`; it does not alter the independent semantic scoring or the bounded platform-acceptance interpretation.
