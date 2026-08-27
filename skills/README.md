# Canonical Hermes skill sources

This directory is the versioned source of truth for the two issue #16 skill domains. `$HERMES_HOME/skills/` is an installed copy, not an authority.

## Domain map

| Canonical package | Owns | Does not own |
|---|---|---|
| `1c/1c-enterprise-linux/` | 1C/Linux create/load/update/runtime mechanics, isolated work copy and disposable IB, Xvfb/process/environment handling, 1C-specific posting observations | Generic business-rule semantics, project capability/cost status, run-specific evidence |
| `software-development/semantic-contract-testing/` | Business statement/predicate, counterimplementations, distinguishing observations, minimal target/control/preservation cases, anti-tautology/pre-patch challenge, core-loop vs milestone evidence policy | Platform lifecycle, 1C fixture/runtime details, project status, exact run evidence |

Project product memory stays in `docs/write-cycle-knowledge-handoff.md`. Exact commands, receipts, hashes, identities, and chronology stay in experiment/GitHub evidence.

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
