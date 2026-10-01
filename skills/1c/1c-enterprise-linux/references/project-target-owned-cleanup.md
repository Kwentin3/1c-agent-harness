# Project-target owned cleanup

Use this for the retained-snapshot materialization path only.

## Invariant

A cleanup routine that receives an owned root may modify or delete only directory entries beneath that root. A symlink is an owned directory entry, not permission to touch its referent.

## Canonical behavior

1. Reject a symlink or non-directory passed as the cleanup root.
2. Enumerate entries bottom-up and classify with `lstat`, never `Path.is_file()` / `Path.is_dir()` followed by `chmod()`.
3. Unlink an in-root symlink itself; do not chmod, read, recurse into, or remove its referent.
4. For regular files, make only that directory entry owner-writable if needed, then unlink it.
5. For directories, make only that directory entry owner-accessible, then remove it after children.
6. Reject special entries fail-closed. Do not attempt a broad recursive cleanup that could reinterpret them.
7. Do not maintain a second near-equivalent cleanup implementation in the CF materializer: delegate to the one canonical owned-cleanup function.

## Required regression proof

Create an external sentinel file with non-default mode and bytes, create a symlink to it inside an owned staging/work root, invoke cleanup or the failure path, and assert:

- the owned root is removed when cleanup succeeds;
- sentinel bytes are unchanged;
- sentinel mode is unchanged.

Also keep representative contract tests that reject source-tree symlinks/hardlinks and prove ordinary `.local/runs` / `.local/prepared` cleanup cannot remove a retained target.
