# Issue 12 — independent SDMS adjudication

## Verdict: DONE — retain the direct-source baseline

Both frozen arms are semantically complete against the nine uniformly weighted Q3 oracle items:

| Arm | Correct | Dangerous false claims | Invalid locators | Context |
|---|---:|---:|---:|---|
| Direct-source baseline | 9/9 | 0 | 0 | Sufficient |
| Bounded-frontier candidate | 9/9 | 0 | 0 | Sufficient |

The candidate is **not useful under either frozen decision design**. It adds statically supported lifecycle detail, but no oracle-essential fact missed by baseline and no qualifying efficiency reduction. The direct-source baseline remains selected; no component should be added from this SDMS result.

## Frozen identity and normalization

- Snapshot manifest/content ID: `3357ee63204ff863aac116417927240930084dce0eb7613126ad88cff68a424d`.
- Re-executed `sha256sum -c` against all 2,581 manifest entries: exit 0.
- Oracle binding: `c48c3f8cf2e24dfe542f591098d950f3617cec7efd3894eb58e52d1101fd2ac4`.
- Source oracle: `761cb235b9fd2d984a4c4817104f26b58760062bc9d863f03600aec53b0f674f`.
- Source detailed adjudication: `e8406bb12605bae9a2bbf95bba1a05ff6cc995a033f247a5a66e9e9bac58754c`.
- Independently reproduced all three binding subobject hashes: Q3 question `b9b2403a…`, Q3 oracle `c8ee5ceb…`, and prior Q3 adjudication `09f3671f…`.
- Candidate raw answer: `eb25400c36d89f2ad332a0212ca35f16647a182491480e3afe35233b09036547`.
- Candidate normalized answer: `814e471300124b1e86a035837fa07d7879f0101efe7e1c50ca5f8f2292e99976`.
- Structural comparison confirmed that substituting the canonical `experimentId` into the raw candidate makes it equal to the normalized candidate. No semantic answer, locator, or metric changed.

Identity caveat: `pre-results-manifest.json` records an earlier `sdms/experiment.json` hash (`8eb79064…`), whereas the canonical experiment now hashes to `fd0c913c…`. The retained preflight artifacts likewise show the earlier `issue12-sdms-context` ID followed by the canonical ID. The supplied contract-normalization record explains the ID alignment, and the candidate semantic payload was independently shown unchanged. This does not alter semantic scoring, but the pre-results manifest is not byte-closed over the current canonical experiment.

## Atomic oracle ledger

1. **POST handler chooses `method=tasks` — both correct.** `HTTPServices/API.xml:459-526` binds POST to `devRequestsIdPOST`; `HTTPServices/API/Ext/Module.bsl:262-281` lowercases `method` and dispatches `tasks`.
2. **Calls `API.СоздатьЗадачуОтЗаявки` — both correct.** Exact call at `HTTPServices/API/Ext/Module.bsl:270-271`.
3. **Rejects service user — both correct.** `CommonModules/API/Ext/Module.bsl:995-999`.
4. **Resolves request reference and parameters — both correct.** Request reference and parameter failure gates are at `CommonModules/API/Ext/Module.bsl:1001-1010`; operation mapping is at `:5085-5088`.
5. **Calls document manager `СоздатьЗадачуПоСистеме` — both correct.** Caller at `CommonModules/API/Ext/Module.bsl:1013`; implementation begins at `Documents/ЗаявкаНаРазработку/Ext/ManagerModule.bsl:376`.
6. **Author must belong to IT — both correct.** `Documents/ЗаявкаНаРазработку/Ext/ManagerModule.bsl:381-398`.
7. **Rejects draft or rejected selected system — both correct.** `Documents/ЗаявкаНаРазработку/Ext/ManagerModule.bsl:409-417`, with selected-system binding at `:813-869`.
8. **Due date must be later than current day — both correct.** `Documents/ЗаявкаНаРазработку/Ext/ManagerModule.bsl:419-425`.
9. **Creates and writes `Документ.Задача` with New status, base request, and core fields — both correct.** `Documents/ЗаявкаНаРазработку/Ext/ManagerModule.bsl:436-471` plus inherited request data at `:813-869`.

No conjunctive item required partial credit. Both answers also correctly separate static reachability from runtime publication, authentication, live values, actual write success, and durable side effects.

## Locator and context validation

Every answer/context locator was checked against the immutable snapshot. All paths exist, all line ranges are in bounds, context full-file hashes match, and each declared fragment byte count equals a fresh CRLF-preserving inclusive-range read.

Fresh totals (not accepted from self-report):

| Metric | Baseline | Candidate | Candidate vs baseline |
|---|---:|---:|---:|
| Selected files | 6 | 7 | +1 |
| Fragments | 9 | 13 | +4 |
| Inclusive lines | 393 | 462 | +69 |
| **Context bytes** | **24,966** | **30,448** | **+21.96%** |
| Navigation operations | 49 | 56 | +14.29% |
| **Wall clock** | **386 s** | **342 s** | **−11.40%** |

The candidate's extra object-module fragments (`Documents/Задача/Ext/ObjectModule.bsl:51-63,281-335`) validly support pre-write revalidation and statically reachable process/deadline/relationship/queue actions. They are useful explanatory extras, not additional oracle credit and not proof that runtime side effects completed.

## Dangerous claims and invalid evidence

- Baseline dangerous false claims: none.
- Candidate dangerous false claims: none.
- Baseline invalid locators: none.
- Candidate invalid locators: none.
- Neither arm claims the endpoint was published, a live request succeeded, or a database commit/secondary effect was observed.

## Distractor negative

`Reports/ЗадачиПоЗаявкам.xml:3-26` is a plausible same-term hit: it defines the report **“Задачи по заявкам”** and its data-composition schema. It is not the HTTP request-to-task creation implementation.

Both packets avoided treating it as evidence: it appears in neither context nor answer locator set. The candidate search log additionally records that unrelated reports/forms were not used. Both instead close the chain through owning HTTP service metadata, API/common-module code, and request/task document modules.

## Usefulness under both designs

### Original preregistered design

Design hash: `f071e67d7d365660f6a8ccd92d7d8529eb28d39a00ad8ec1aa639ee8fd91cf66`.

**Decision: NOT USEFUL — keep baseline.** The SDMS correctness/evidence gates pass, but no positive signal passes:

- coverage is tied 9/9, so there is no candidate-only oracle-essential relation;
- context bytes increase rather than fall ≥25%;
- operations increase rather than fall ≥25%;
- wall clock falls only 11.40%, not ≥25%.

Candidate `preparationSeconds` is `null`, so the original preparation-cost ceiling is not independently demonstrated. This uncertainty cannot rescue the result because the required positive signal already fails.

### Stricter pre-results amendment

Amendment hash: `a3844715972c19e9e7f055c97b171c50cf395bd5a60df66bb387b67143874c2a`.

**Decision: NOT USEFUL — keep baseline.** Neither amended branch passes:

- **Signed-reduction branch:** no observed efficiency metric improves by ≥25%.
- **Pareto/non-regression:** context bytes regress 21.96% and navigation operations regress 14.29%, both beyond the allowed 10%; wall clock improves only 11.40%.
- **Essential-relation branch:** coverage is tied, not higher for candidate.

## Final scope

This establishes only that, for this frozen SDMS task and these two model runs, both approaches produced complete and valid static answers, while the bounded-frontier protocol did not justify its extra context/navigation cost under either predeclared rule. It does not establish universal 1C navigation superiority or inferiority.
