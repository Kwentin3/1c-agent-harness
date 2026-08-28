# Issue #20 low-cost prepared-tree native lifecycle evidence

This closed package proves the supported `run-prepared` path on Linux 1C:Enterprise 8.5.1.1150 for candidate commit `41ced17f3f01c0661bb50dfa69bcd36ca3bfb109` / tree `12e34ae765628954cc7f1895ceab1e3d76cd26d1`. It is separate from the historical bounded-executor package.

## Result

- The same caller command completed success and clean repeat.
- Full preparation-inclusive timing: success `176.030 s`; repeat `169.239 s`.
- The runner generated unique invocation roots, frozen inputs, fingerprints, specs, and `/C` receipt bindings.
- Both receipts matched the accepted issue #18 semantic key order and terminal `complete###true` contract with no unexpected behavior differences.
- Prepared source identity was unchanged before and after both runs.
- The exact post-repeat process scanner output is empty.
- Immutable snapshot verification remained 5099/5099 with no missing, extra, mismatched, or symlink entries.

`runtime_contract_completed` remains a mechanical result. Semantic acceptance is separately recorded in each `*-acceptance.json`. Task-specific BSL patch/probe authoring and semantic-oracle authoring remain outside the common tool.

## Cost verdict

**LOW-COST PREPARED-TREE LIFECYCLE PASS; TASK-SPECIFIC PREPARATION AND SEMANTIC ORACLE REMAIN OUTSIDE THE CAPABILITY.**
