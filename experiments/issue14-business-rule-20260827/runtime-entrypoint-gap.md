# Runtime entrypoint gap before semantic amendment

This record describes the bounded diagnostic already performed before the corrected semantic-closure gate was published. It is not RED evidence.

- Run root: `.local/runs/issue14-business-rule-primary` (created fresh after the original frozen contract).
- Source/work-copy identity: the production module in the RED work copy remained byte-equal to immutable snapshot SHA-256 `86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c`.
- Entrypoint: managed application `OnStart` called a probe-only exported server procedure.
- Last confirmed marker: `target-before-unposted-write` immediately before the first `Document.InventoryIncrease.Write()`.
- Confirmed completed object writes before that marker: one Unit, one Warehouse, and three Products. Their successful writes are evidenced only by sequential stage markers; no business-result receipt was produced.
- Stop condition: each launch was bounded by a 180-second receipt wait; the client process group was then terminated. No final `complete###true` receipt existed.
- Result: exact gap reproduced — the issue #10 `OnStart → synchronous server probe` path enters the server scenario but does not return from the first document write in this context.
- Immutable post-check: source CF SHA-256 `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`; snapshot manifest SHA-256 `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`; 5,099/5,099 files, no missing, extra, or mismatched files.

The accepted next candidate is a one-off external EPF built and executed by native 1C commands. Any next diagnostic must use a new disposable IB, a unique current-run nonce, stage markers before and after each material operation, and a finite timeout. It remains blocked from full RED until the semantic amendment receives an independent pre-production verdict.
