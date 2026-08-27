# Semantic contract checklist

A small pre-production review pattern validated by issue #14:

1. **Business rule** — state the rule without implementation terms.
2. **Formal clauses** — identify subject/domain, quantifier, exact predicate and boundary, operation scope, failure semantics, atomicity/side effects, preserved behavior, and unknown/out-of-scope behavior.
3. **Plausible countermodels** — list materially wrong interpretations grounded in the selected application's semantics.
4. **Distinguishing observations** — for every countermodel, define a domain observation that differs from the required rule; process success and `Posted=false` alone are insufficient.
5. **Minimal cases** — add a case only to kill a named surviving countermodel and map each observation to its clause.
6. **Self-challenge** — ask which materially wrong implementation still passes the full matrix; narrow claims or add one justified case if one survives.
7. **Independent pre-production challenge** — give the frozen contract and source semantics, but no implementation, to a reviewer who attempts to produce a surviving countermodel.

This is a checklist, not a DSL, generator, schema engine, runner, or test framework.
