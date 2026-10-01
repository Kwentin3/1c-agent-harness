# Reviewable GitHub boundary for native 1C product work

Use this note when a 1C task is expected to end in an owner-reviewed PR rather than a local experiment.

## Working rule

GitHub is the persistent verification boundary, not merely the final showcase. As soon as the first coherent code/evidence candidate exists:

1. Commit it on a dedicated task branch.
2. Non-force push that exact branch and open a draft/open PR immediately when the issue pre-authorizes ordinary publication mechanics.
3. Keep subsequent reviewable states in the same PR; do not leave the only candidate in an executor-local worktree.
4. At every review request, prove exact equality of:
   - local `HEAD`;
   - remote task-branch SHA;
   - PR `headRefOid`;
   - published commit tree.
5. Bind CI, tests, evidence hashes and review findings to that same published head/tree.
6. Read the PR back from GitHub: base/head, state, title/body, files and checks. Local tests and reviewer self-reports do not replace this read-back.
7. Leave the PR open/unmerged unless the owner separately authorizes merge.

## Approval gates

If the live issue explicitly pre-authorizes normal non-force push, PR create/update, read-back and CI, treat those as ordinary reversible work. If an environment approval gate still appears, cite the exact live owner contract and request that system confirmation; never bypass the gate via another transport and never relabel a local-only candidate as ready for review.

## Native evidence handoff

Publish only compact, reviewable evidence:

- exact head/tree and canonical target/runtime identities;
- native invocation count and measured elapsed time;
- RED, GREEN and clean-repeat business observations;
- current request/receipt bindings and negative false-PASS checks;
- cleanup/continuity and honest limits;
- direct PR and exact-head CI links.

Keep heavy raw logs, disposable IBs, prepared trees and executor-local paths out of Git. Preserve compact receipts/results/patches behind an exact package manifest and fail-closed validator when milestone acceptance requires it.

## Pitfalls

- Waiting until the end to push makes owner review impossible during the work and can turn a completed local candidate into a blocker.
- Saying “READY FOR OWNER REVIEW” before local/remote/PR identity and CI agree is false completion.
- A successful push does not prove PR contents; always perform GitHub read-back.
- Issue-level publication authorization does not authorize force-push, merge, issue closure or new native/product scope.
