# Issue #71 — Runtime Diagnostics: KISS design and prototype

## Решение в одном предложении

Добавить в существующий terminal-bound `one-c-harness` одну read-only capability
`investigate` с provider-backed данными: она принимает ограниченный incident window,
детерминированно группирует и связывает нормализованные runtime records, возвращает
короткие findings с evidence refs, а раскрытие конкретных записей оставляет тому же
provider; ни storage, ни scheduler, ни новый transport Harness не строит.

Статус: **design + bounded deterministic prototype**. Это не live-production
интеграция: в данном executor нет 1C cluster, исторических логов, DB access или
преднастроенного monitoring provider.

## 1. Product slice

Первый запрос: «Пользователи сообщают, что 1С тормозила с 08:12 до 09:47; покажи
наблюдаемые аномалии, связанные с фоновыми jobs, сеансами, процессами и timeouts».

`investigate` выполняет внутри одной операции:

1. посылает window и безопасные filters доступному provider;
2. проверяет bounded normalized records;
3. группирует job/session/process identifiers, считает concurrency и timeout counts;
4. агрегирует samples (`avg`, позже `p50/p95/max` при достаточной выборке);
5. возвращает findings, evidence refs и явные unavailable/blocker states;
6. не объясняет причину и не выполняет remediation.

Первый prototype (`one_c_harness.runtime_diagnostics`) доказывает именно эту границу:
нормализованные records -> deterministic finding -> record refs. Он не читает host paths,
не запускает commands, не хранит историю и не содержит vendor-specific collector.

## 2. Source map

| Source | What it establishes | Access / mode | Live or history | MVP |
|---|---|---|---|---|
| RAC/RAS | cluster, work processes, sessions, connections and their known IDs | executor-owned read-only RAC provider | live | yes, where `rac` is available and authorized |
| OS process metrics | PID, start time, CPU/RAM/disk samples | existing OS/Prometheus provider; Windows exporter on Windows, node exporter on Linux | live; history only if monitoring already stores it | optional |
| TechLog | platform events, durations, errors/timeouts and some identifiers | existing read-only log provider or existing log store | historical only when logging existed | optional, primary incident evidence |
| Event log / registration log | business/system events and timestamps | existing log reader/store | historical only when retained | optional |
| DB | waits, locks, slow queries, connection state | DB-engine-specific read-only provider | live or historical only through existing DB monitoring | not MVP core |
| admitted `SnapshotRef` | metadata and BSL source navigation | existing coding domain only | static | optional correlation after a finding |

### Provider rules

* A provider owns credentials, host endpoints, absolute paths, source pagination and raw
  record retrieval. None enters a model-facing request or project contract.
* Core receives only a versioned, bounded normalized record envelope with opaque
  `recordId`; it must reject malformed or out-of-window input.
* `provider_unavailable` means the source cannot be reached or is not installed;
  `history_unavailable` means the requested period was never retained. Neither permits
  invented history or fallback to an unrelated source.
* Providers are adapters, not a plugin framework: add one only after an actual available
  source is selected. MVP needs no universal DB adapter.

## 3. Community findings

* [1C performance center (ЦУП)](https://its.1c.ru/db/kip/content/6/hdoc) is the
  mature reference for combining 1C, OS, DB and TechLog diagnostics. Its documented
  contents include RAS, OS performance counters, OpenSearch and log collection. Reuse
  it as an operational product/provider where installed; do not recreate it.
* [V8LogScanner](https://github.com/ripreal/V8LogScanner) is a MIT-licensed TechLog
  scanner with bounded selection examples. It is a candidate external parser for an
  on-demand file provider, not code to copy into this repository.
* [1c-log-checker](https://github.com/SteelMorgan/1c-log-checker) already builds its
  own Docker + ClickHouse + Grafana + MCP stack and can configure TechLog. It confirms
  that ingestion and historical storage are separate concerns, but is deliberately
  outside this Harness: use an already deployed instance as a read-only provider only;
  do not introduce its MCP, storage or TechLog mutation route here.
* [prometheus_1C_exporter](https://github.com/LazarenkoA/prometheus_1C_exporter)
  reads RAC and exports 1C/OS metrics to Prometheus. Where deployed, query its existing
  monitored history through a provider rather than sampling/scheduling in Harness.
* [windows_exporter](https://github.com/prometheus-community/windows_exporter) has
  OS, process, disk, service and custom performance-counter collectors. It belongs to
  generic executor/OS monitoring. [node_exporter](https://github.com/prometheus/node_exporter)
  is the analogous Linux source.

No third-party source code is copied: this repository has no chosen license
([AGENTS.md](../AGENTS.md)).

## 4. Boundary

| Place | Responsibility |
|---|---|
| Agent | picks symptom/window, compares alternative explanations, states hypothesis versus fact, decides whether to inspect evidence or use coding-domain |
| Runtime core | validates normalized records; deterministic filtering/grouping/counts/statistics; stable refs; response bounds; fail-closed errors |
| Provider adapter | source-specific authenticated read-only collection and expansion; pagination; source ID mapping; redaction before normalized records |
| Environment contract | cluster identity, available providers, DB type, retention and time zone; no credentials, absolute host paths or execution logic in a business project |
| Existing infrastructure | RAS/RAC, TechLog, ЦУП, Prometheus, OpenSearch, ClickHouse, DB monitoring and OS collectors retain collection/storage/retention responsibility |
| Coding domain | opens/admit `SnapshotRef` and resolves source evidence only after a runtime finding contains a confirmed metadata identity |

Runtime must not import or modify coding code. Disabling all runtime providers therefore leaves
`open -> narrow -> verify` unchanged.

## 5. Public contract (proposed schema v1)

The public surface has two operations, not one low-level tool per source:

```json
{
  "schemaVersion": 1,
  "operation": "investigate",
  "arguments": {
    "incident": {"start": "2026-09-18T08:12:00Z", "end": "2026-09-18T09:47:00Z"},
    "focus": ["background_jobs", "sessions", "process_load", "timeouts"],
    "limit": 20
  }
}
```

`investigate` response:

```json
{
  "schemaVersion": 1,
  "status": "ok",
  "incidentRef": "incident:opaque-9c2a",
  "summary": {"recordCount": 59},
  "findings": [{
    "ref": "finding:job-runtime-anomaly:1",
    "classification": "derived_deterministically",
    "observed": {"job": "HonestMarkExchange", "sessionCount": 37, "pid": "8420", "cpuAvgPercent": 71, "timeoutCount": 19},
    "evidenceRefs": ["evidence:rac:…", "evidence:os:…", "evidence:techlog:…"]
  }],
  "unavailable": []
}
```

`expand` accepts exactly one opaque `findingRef` or `evidenceRef`, a level and a bounded
limit. It is served by the provider that owns the handle. Levels are L0 incident summary,
L1 finding, L2 evidence group, L3 individual normalized records and L4 provider-authorized
raw record. Model-visible output never contains absolute host paths, stack traces or secrets.
A ref expires with its source/provider retention; an expired ref is a blocker, never a
silently re-run different query.

The final exact tool names must be added to the existing companion/plugin only after the
provider-selection canary below. The prototype purposefully proves core semantics first,
not a speculative adapter API.

## 6. Provenance and classification

Each evidence group contains record refs, and every finding lists all groups that support
it. The prototype test asserts that all 59 input records remain reachable through those
refs. The core reports only these classifications:

* `observed`: a direct provider field;
* `derived_deterministically`: a count, group, time join or statistic whose input refs are
  supplied;
* `inferred_heuristically`: optional later agent conclusion, never emitted by core;
* `unknown`: source, join or history is missing.

A shared time window and PID establish correlation, not cause. The sample finding supports
"the job is concurrent with saturation and timeouts", not "Honest Mark caused saturation".

## 7. Runtime -> code bridge

Exact bridge is possible only when a provider returns a stable platform metadata/job identity
that the admitted snapshot can locate. The agent then calls existing `open`/`narrow` with
that identity and labels the result `observed` (runtime identity) plus `observed` (source
locator). A BSL procedure is exact only when the configuration provides a direct identity;
otherwise a name match is heuristic. Session/PID/time alone cannot establish a BSL procedure.

This prototype does not claim the bridge because no real RAC/TechLog/configuration source is
available in this executor.

## 8. TechLog and safety

Always prefer read-only TechLog access. Full/verbose permanent logging and automatic
`logcfg.xml` modification are not MVP. Detailed temporary profiles are operator-controlled,
time-boxed and need an explicit later product approval because they affect production volume
and potentially include sensitive data. The 1C troubleshooting material shows targeted
`logcfg.xml` filters for SQL investigation; it is evidence that TechLog is powerful but not a
safe universal always-on feed.

No kill-session, job stop, rphost restart, DB cancellation, live IB write, TechLog change,
arbitrary shell or new scheduler/service is in scope.

## 9. First provider canary and acceptance

The next implementation step is one read-only provider selected by real environment facts:

1. record available `rac`, OS source and historical TechLog/Prometheus retention without
   reading business data;
2. run one bounded morning incident query against an authorized non-production or sanitized
   captured data source;
3. ensure every output finding expands to source records and that unavailable history returns
   the declared blocker;
4. if a job metadata identity is present, use current coding `SnapshotRef` route to cite it;
5. compare output byte bounds and assert no paths/secrets/stack traces.

Success proves the abstraction boundary, not general monitoring. If no provider is available,
stop with `provider_unavailable` / `history_unavailable`; do not add a storage service merely
to make the canary pass.

## 10. Negative scope

No monitoring backend, time-series DB, log store, scheduler, daemon, new MCP, second
Harness/runtime, generic DB product, permanent TechLog collection, remediation action,
Windows-only core or task-specific Honest Mark integration.

## Prototype evidence

Run:

```bash
python3 -m unittest -v tests.test_runtime_diagnostics
```

The tests use 37 normalized RAC session records, three OS samples and 19 TechLog timeout
records. They prove deterministic aggregation, full evidence-ref coverage and fail-closed
rejection of an invalid/out-of-window provider record. They do **not** claim a native 1C,
RAC, OS or production run.
