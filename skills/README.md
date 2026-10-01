# Canonical Hermes skill sources

This directory is the versioned source of truth for three non-plugin skill domains. `$HERMES_HOME/skills/` is an installed copy, not an authority.

## Domain map

| Canonical package | Owns | Does not own |
|---|---|---|
| `1c/1c-enterprise-linux/` | 1C/Linux create/load/update/runtime mechanics, isolated work copy and disposable IB, Xvfb/process/environment handling, 1C-specific posting observations | Generic business-rule semantics, project capability/cost status, run-specific evidence |
| `1c/headless-1c-probing/` | Executor admission, headless client/server witness and bounded probe lifecycle | Business-rule correctness, live deployment permission |
| `software-development/semantic-contract-testing/` | Business statement/predicate, counterimplementations, distinguishing observations, minimal target/control/preservation cases, anti-tautology/pre-patch challenge, core-loop vs milestone evidence policy | Platform lifecycle, 1C fixture/runtime details, project status, exact run evidence |

Project product memory stays in `docs/write-cycle-knowledge-handoff.md`. Exact commands, receipts, hashes, identities, and chronology stay in experiment/GitHub evidence.

## Source reconciliation

The finalization recovers the existing Hermes-authored installed additions into
Git, rather than treating installed bytes as a permanent authority:

- `1c-enterprise-linux`: installed 1.6.0 plus the additive routing-description
  correction, now 1.6.1; 36 resources;
- `headless-1c-probing`: installed 1.0.1; 6 resources, previously absent here;
- `semantic-contract-testing`: installed 0.3.0 plus the reviewed trigger and detailed
  pre-native checklist alignment, now 0.3.1; 2 resources.

The bytes are admitted by this PR and its exact-tree review. Their presence in
an installed profile is not proof that every described native procedure was
re-executed during recovery. Existing references retain their own historical
scope; no native budget, deployment or production write follows from admission.
`tests/test_skill_sources.py` checks versions, complete file sets, sizes, hashes,
package identities, reference existence and both primary 1C routing triggers.
The reconstructed packages were compared with installed copies during this
finalization; that is byte parity, not a fresh-executor discovery/native canary.

The plugin skill is not a fourth standalone manifest package. Its canonical
source is `hermes-plugin/skills/one-c-harness/SKILL.md`, covered by the plugin
release contract. No third-party source import or new project license decision
is made by this recovery.

## Identity

`manifest.json` closes each package over its exact relative file set, byte size, and SHA-256. The canonical Git identity is the exact commit/tree containing that manifest; after any resource change, regenerate the manifest and obtain a new review for the new Git identity.

The repository currently has no declared project-wide license. These files do not add a project license grant or publish a separate package/release.

## Bounded recovery check

A recovery verification must use the canonical Git tree, not the existing installed bytes:

1. Check out the exact reviewed Git commit into a fresh temporary directory outside `$HERMES_HOME`.
2. Validate every package resource against `skills/manifest.json`, including closed file set, size, and SHA-256.
3. Copy each validated package into a fresh temporary install root using the manifest's `install_root` relative to that root.
4. Compare the reconstructed temporary install byte-for-byte and file-set-for-file-set with the canonical source.
5. Install/update the active profile through Hermes skill management, then compare `$HERMES_HOME/<install_root>` against the same canonical package.
6. From a new isolated agent context, verify independent discovery and `skill_view` reads for both skill names.

A fresh context reading the same `$HERMES_HOME` proves discovery only. Recovery PASS additionally requires reconstruction from the exact Git source and parity with both the temporary and active installed copies.
