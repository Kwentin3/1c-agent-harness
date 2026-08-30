---
name: semantic-contract-testing
description: Design semantic business-rule contracts before coding.
version: 0.3.0
author: Kwentin3, Hermes Agent
license: UNLICENSED
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [testing, semantic-contracts, business-rules, countermodels]
    related_skills: [test-driven-development, systematic-debugging]
---

# Semantic Contract Testing

Design a falsifiable behavior contract before implementing a business-rule change. This skill owns generic semantic/test-design policy; domain skills own platform execution and domain observations.

## When to Use

Use when a change depends on business meaning, boundaries, quantifiers, persisted state, side effects, or preservation of existing behavior.

Do not use it to choose a product rule for the user, invent missing requirements, or replace domain-specific execution guidance.

## Domain Boundary

This skill owns:

- business statement → explicit semantic model;
- plausible counterimplementations;
- distinguishing observations;
- minimal target, control, boundary, and preservation cases;
- anti-tautology and independent pre-patch challenge;
- the policy split between a cheap developer loop and milestone acceptance.

A domain skill owns:

- platform lifecycle and process handling;
- fixture creation and domain APIs;
- domain-specific persisted state and side effects;
- environment cleanup and runtime pitfalls.

Project docs own capability status, measured cost, candidates, and the next gate. Run evidence owns exact commands, hashes, receipts, identities, and chronology.

## Pre-native context gate

Before spending a native/runtime budget on a small change in an unfamiliar codebase, publish a short human-readable Markdown preflight. It is an orientation aid, not a schema or a proof of correct understanding. Show only the structure needed for this task:

- **Change:** one sentence, current behavior → required behavior.
- **Context:** concrete objects, entry points, data path, and reproducible source locators.
- **Current scenario:** one explained scenario grounded in the current sources.
- **Preserved behavior:** neighboring rules or valid shapes the change must not break.
- **Wrong implementations:** at least two plausible changes that could look correct while violating the task.
- **Cases and observations:** for every distinguishing case, state the relevant **pre-state → input/action → expected persisted/business post-state**. Command success alone is not enough.
- **Unknowns and verdict:** state material unknowns, then finish with exactly `READY FOR NATIVE` or `CONTEXT BLOCKED`.

Trace omitted/default values and every normalization step to the predicate they affect; do not state a default branch without the pre-state that makes its result distinguishing. Limit each claim to the proven API and execution layer, and name the nearest bypass/write surfaces that the claim does not cover.

Do not silently weaken task language. In particular, when a task says `no-op` and means no write or no side effect, unchanged persisted scalar alone is not a substitute. State a reproducible runtime witness or a static acceptance constraint that proves the required absence; if neither is available before the bounded experiment, retain the requirement as unknown and finish `CONTEXT BLOCKED` rather than redefine it. Do not force seven identical sections when some items combine naturally, and do not add irrelevant domain ceremony. Use `READY FOR NATIVE` only when every retained wrong implementation is distinguished and the cited context is sufficient for the next bounded experiment. Otherwise name the missing evidence and use `CONTEXT BLOCKED`. Do not run the native loop merely to compensate for missing source understanding.

## Procedure

1. State the rule without implementation terms and identify domain, quantifier, predicate/boundary, operation scope, failure semantics, side effects, preserved behavior, and unknowns.
2. List materially wrong but plausible implementations. Explain why each is plausible; do not copy a stock checklist blindly.
3. Define one observable difference for every retained counterimplementation. Express it as pre-state → input/action → expected persisted/business post-state; prefer current domain state over process success.
4. Trace omitted/default values and normalization before the predicate, then add only the smallest cases needed to kill the named counterimplementations. Include preservation controls for every negative shape dimension introduced.
5. Ask which wrong implementation still passes the whole matrix. Add one distinguishing observation/case or narrow the claim.
6. State the proven API/execution-layer scope and nearest bypass/write surfaces. For any claimed no-write/no-side-effect no-op, freeze a witness or static acceptance constraint; otherwise narrow neither the task nor the word `no-op` and use `CONTEXT BLOCKED`.
7. Freeze the contract before production code. If review finds a gap, amend transparently before RED/GREEN rather than rewriting history.
8. Run an independent pre-patch challenge when the issue or risk requires it. The reviewer must try to construct a wrong implementation that still passes.
9. Then use the domain execution skill and ordinary RED/GREEN implementation loop.

Read `references/semantic-business-rule-contracts.md` for the detailed model and verification checklist.

## Core Loop vs Milestone Acceptance

**Core developer loop:** use the smallest semantic model, countermodel set, observations, and RED/GREEN cases that distinguish the authorized change. Do not require canonical repeat, a closed evidence package, exact release-tree binding, or independent final review by default.

**Milestone/R&D acceptance:** add the heavier layer only when claiming reproducibility/new capability, closing a benchmark/R&D gate, publishing independently auditable evidence, or addressing a concrete high-risk boundary. That layer can include canonical repeat, a closed package and fail-closed validator, adversarial mutations for reproduced false positives, exact HEAD/TREE/CI binding, and independent review before owner acceptance.

Automate repeated core-loop mechanics first. Do not make routine engineering pay benchmark ceremony unless issue scope or concrete risk requires it.

## Pitfalls

- Examples without countermodels can validate the wrong rule.
- A rejected negative case does not prove valid values/shapes remain accepted.
- Process success is not domain behavior; use persisted state and side effects.
- `No-op` is not synonymous with unchanged scalar when the task preserves absence of writes or side effects.
- A test that passes without the production change is tautological or targets the wrong seam.
- A milestone evidence package is not a default developer workflow.
- Reviewers and tools do not choose the business rule, oracle, production patch, or acceptable unknowns.

## Verification

Before implementation, confirm:

- every rule clause has at least one distinguishing observation;
- every distinguishing case records pre-state → input/action → expected persisted/business post-state;
- omitted/default normalization is traced before its predicate;
- every retained counterimplementation is killed or the claim is narrowed;
- target, boundary/negative-control, and preservation behavior are covered;
- API/execution-layer scope and nearest bypass/write surfaces are explicit;
- every required no-write/no-side-effect no-op has a witness or static acceptance constraint; otherwise verdict is `CONTEXT BLOCKED`;
- predicted behavior is frozen before RED;
- domain-specific observations come from the relevant domain skill/source;
- the selected evidence tier is justified by issue scope or concrete risk.
