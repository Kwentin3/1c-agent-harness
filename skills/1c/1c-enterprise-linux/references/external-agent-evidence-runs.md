# External-agent evidence runs for 1C snapshots

Use this procedure when an isolated LLM runner must inspect an immutable 1C XML/BSL snapshot and return a large evidence-backed answer through a constrained transport envelope.

## Artifact admission

- A path or URI in a prompt does not transfer bytes across execution environments. Build a content-addressed input bundle and admit it explicitly into the runner.
- Expose only the required snapshot/questions, read-only. Keep secrets, other arms, oracle material, and host-local paths out of the bundle.
- Record hashes before execution and rehash both the admitted bundle and authoritative source snapshot afterward. Task completion without post-run integrity evidence is not artifact completion.

## Unit protocol

```text
immutable snapshot/questions
→ one question per runner task
→ one typed answer unit
→ immediate schema + locator verification
→ deterministic assembly in frozen question order
→ full-answer verification
```

- The LLM owns only semantic fields for one question: answer, facts, inferences, assumptions, unknowns, and locators.
- The experiment/runtime owns IDs, hashes, client identity, metrics, ordering, provenance, and final serialization. Do not ask the model to regenerate system facts.
- A client adapter may extract an exact JSON object from the native transport envelope. It must not repair malformed JSON, rename claims, add defaults, reclassify statements, or know a particular fixture/question set.
- Fail closed on malformed or competing transport fields; publish no unit output on failure.
- Verify every unit immediately against the frozen question set and original XML/BSL locators.
- Assemble only the exact frozen set: no missing, extra, or duplicate question IDs. Arrival or CLI argument order is not authoritative.
- Re-run the full verifier after assembly. A successful transport response is not a verified domain artifact.

## Retriever admission

Treat every metadata index, AST index, parser, graph, RAG layer, or additional skill collection as optional until a frozen comparison proves value.

1. Compare against direct XML/BSL search on the same snapshot, questions, evidence contract, and source-fallback policy.
2. Measure answer quality, dangerous false claims, elapsed time, and tool operations—not merely index build success or feature count.
3. Keep source files authoritative. Indexes narrow navigation but never replace source locators.
4. Same-name procedure usages and platform lifecycle dispatch are navigation candidates, not a proven call graph.
5. One run may justify `HOLD` or another experiment; it cannot establish universal superiority or uselessness.
6. If a candidate does not improve the frozen run, keep it optional rather than expanding the mandatory stack.
7. Prefer a small typed extension to an already-adopted skill pool over importing another overlapping repository. Before copying, check exact-file overlap, provenance, and license; evaluate only genuinely new components.

## Reporting

- Separate confirmed facts, inferences, assumptions, and unknowns.
- State whether post-run hashes passed.
- Report index blind spots and source fallbacks.
- Preserve invalid attempts under new filenames; do not overwrite failed evidence.
- Return artifact paths and hashes only after unit and final verification report success.
