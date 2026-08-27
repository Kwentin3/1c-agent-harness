# Publishing and closing a verified 1C lab issue

Use this reference after a native Linux lab has passed staged-artifact review and the user authorizes publication and closure. It preserves the review-to-delivery evidence chain; it is not a replacement for the GitHub PR workflow skill.

## Close-loop procedure

1. Read the live issue body and full comment thread again. Earlier blocker comments can remain historically correct but stale after the user supplies the missing installer, Workspace, or approval.
2. Sweep open and closed PRs by issue number plus at least two task synonyms before pushing.
3. Confirm the worktree is clean and record the reviewed branch, commit SHA, and intended changed-file list.
4. Push that exact commit. Create a PR whose body records:
   - achieved result;
   - reproducibility evidence and commands;
   - native process exits and 1C `/DumpResult` values;
   - fixture immutability and snapshot identity;
   - limitations and unverified claims;
   - exact handoff for the next stage;
   - `Closes #N`.
5. Read the PR back and verify base branch, head SHA, non-draft state, title, and exact files before merging.
6. Interpret GitHub checks honestly. `gh pr checks` returning "no checks reported" means **no CI is configured**, not green CI and not a failed build. Report that distinction and inspect live mergeability/review requirements.
7. After merge, read both remote objects back. Require PR state `MERGED` and issue state `CLOSED` with reason `COMPLETED`; never infer closure from a successful merge command alone. Closing keywords take effect only when the PR lands on the default branch.
8. Verify the remote feature branch was deleted when requested. Add a concise issue-closing comment that links the PR and records the durable stage handoff, especially when the thread contains an old blocker report.
9. Fast-forward the local default branch, remove the local feature branch, and verify a clean tree. Do not delete ignored `.local/` platform, snapshot, provenance, or log evidence during branch cleanup.

## Evidence wording

- Say "no CI checks configured" when that is what GitHub reports; do not say "CI green".
- Name the merge commit separately from the reviewed feature commit when squash merging changes the SHA.
- Report PR and issue URLs and live final states.
- State explicitly whether push, merge, branch deletion, and issue closure were performed.
