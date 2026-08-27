# Semantic closure for business-rule changes

Use this reference before changing validation, posting, eligibility, calculation, authorization, or other application logic whose correctness depends on business state.

## Why example-only contracts are insufficient

A correct prose statement can still be represented by cases that permit a materially wrong implementation. One invalid example rarely proves the exact boundary, quantifier, operation scope, failure state, atomicity, or preserved positive domain.

Freeze semantic closure before production code and before accepting RED/GREEN evidence.

## Required sequence

### 1. Business statement → semantic model

Record:

- **subject/domain** — governed objects, rows, values, actors, or events;
- **quantifier** — every, any, at least one, aggregate, or object-level;
- **predicate and boundary** — exact valid set and inclusive/exclusive bounds;
- **operation scope** — which transition or entry point is governed;
- **failure semantics** — observable persisted state that proves rejection;
- **atomicity and side effects** — state that must remain absent or unchanged;
- **preserved behavior** — ordinary valid behavior and existing rejection paths;
- **unknown/out-of-scope** — behavior the requirement does not authorize.

Example shape, not a universal rule:

```text
Allowed(operation) ⇔ ∀ item ∈ operation.Items: predicate(item)
```

### 2. Semantic model → plausible counterimplementations

Construct realistic wrong interpretations grounded in the active domain. Common classes include:

- wrong boundary;
- aggregate validation instead of per-item validation;
- first/last-item-only validation;
- operation scope widened or narrowed;
- rejection after partial side effects;
- valid domain narrowed beyond the requirement;
- enforcement only at a bypassable entry point;
- constant/stale oracle output;
- test instrumentation that succeeds without the production change.

Explain why each retained counterimplementation is plausible and material. Remove speculative cases that do not affect the claim.

### 3. Counterimplementations → distinguishing observations

For each counterimplementation, freeze an observation that differs from required behavior. Prefer domain state and exact side effects over exit codes, successful imports, or parsed files.

Useful generic observation classes:

- persisted object/transition state;
- exact created, changed, or absent records;
- before/after balances or aggregates;
- durable error/refusal category;
- current-run identities proving the observation is not stale.

### 4. Observations → minimal cases

Add a case only to kill a named surviving counterimplementation. Typical roles:

- target case;
- exact boundary case;
- negative control for an existing rejection path;
- ordinary preservation case;
- shape-preservation case matching a negative case's cardinality, ordering, duplicate identity, or type mix.

Map `clause/counterimplementation → observation → case`. A case can cover several clauses only when its observations independently distinguish each one.

### 5. Anti-tautology challenge

Ask:

> Which materially wrong implementation can still pass every case and observation?

If one survives, add the smallest distinguishing observation/case or narrow the claim. Require RED to differ because the production behavior is absent, not because the fixture, parser, or probe is broken. A probe that succeeds without the production patch is not mutation-power evidence.

### 6. Transparent freeze and amendment

Freeze predicted behavior before production code. If review finds an incomplete contract:

1. preserve the original freeze;
2. publish a normal amendment that identifies what it supersedes;
3. state whether production code or complete RED/GREEN existed;
4. change only deficient clauses/cases;
5. keep ordering visible.

### 7. Independent pre-patch challenge

When issue scope or risk requires independent challenge, provide the business statement, source locators, semantic model, counterimplementations, observation/case matrix, and exact frozen identity—but no future implementation.

Require the reviewer to restate the rule independently and construct a plausible wrong implementation that passes the matrix. A survivor is a contract blocker, not a production-code defect.

This review is distinct from final implementation/release acceptance.

## Evidence tiers

### Cheap core developer loop

Use the minimum semantic closure and RED/GREEN observations needed to distinguish the authorized rule. Stop when the implementation is correct at the requested domain seam and limits are honest.

Do not automatically add:

- canonical repeat;
- a complete publication/evidence package;
- exact release-tree/CI binding;
- independent final review.

### Milestone/R&D acceptance

Add heavier evidence only for a reproducibility/new-capability claim, benchmark/R&D closure, independently auditable publication, or a concrete high-risk boundary. Depending on the claim, require:

- canonical repeat;
- closed artifact set and fail-closed validator;
- adversarial mutations for reproduced false-positive classes;
- exact candidate/tree/CI identity;
- independent final review before owner acceptance.

Evidence hardening is not new product capability. Stop adding ceremony once reproduced false positives are closed unless another concrete bypass appears.

## Domain adaptation rule

This generic contract never supplies domain truth. The domain skill/source must define:

- how state is created and observed;
- which side effects establish atomicity;
- which entry points can bypass validation;
- which valid shapes must be preserved;
- how execution and environment cleanup work.

For 1C document posting, load `1c-enterprise-linux` and its data-backed document probe reference rather than copying 1C-specific `Date`, `Posted`, movement, or register-balance rules here.

## Verification checklist

Before implementation:

- business statement and source locators support the model;
- quantifier, boundary, operation scope, failure semantics, side effects, preservation, and unknowns are explicit;
- every retained counterimplementation has a distinguishing observation;
- target, control/boundary, and preservation cases close the stated claim;
- predicted behavior is frozen before RED;
- any required independent pre-patch verdict binds the frozen identity;
- the chosen evidence tier is justified by issue scope or concrete risk.
