# Knowledge handoff после 1C write-cycle экспериментов

Этот документ — versioned project memory для issue #16. Он фиксирует, что продукт уже доказал, где границы доказанного, какую стоимость показали issue #10/#14 и какие узкие швы автоматизации стоит проверять во второй отличающейся задаче.

Документ **не** является runbook, evidence package, tool spec или разрешением на новый framework. Точные hashes, receipts, nonce, native argv, chronology и reviewer verdicts остаются в experiment/GitHub evidence.

## Authoritative sources

| Источник | Роль |
|---|---|
| [Issue #10](https://github.com/Kwentin3/1c-agent-harness/issues/10), [PR #11](https://github.com/Kwentin3/1c-agent-harness/pull/11) | Принятый технический Jet write/runtime slice: локальная BSL-функция, native RED/GREEN, fail-closed evidence. |
| [`docs/issue-10-write-cycle.md`](issue-10-write-cycle.md) | Единственный авторитетный исполнимый runbook issue #10. |
| [`experiments/issue10-write-cycle-20260826/`](../experiments/issue10-write-cycle-20260826/README.md) | Frozen evidence issue #10: task contract, diffs, receipts, manifest. |
| [Issue #14](https://github.com/Kwentin3/1c-agent-harness/issues/14), [PR #15](https://github.com/Kwentin3/1c-agent-harness/pull/15) | Принятый прикладной data-backed write-cycle: `InventoryWriteOff` quantity rule, final independent PASS, merge с сохранением Git-истории. |
| [`experiments/issue14-business-rule-20260827/`](../experiments/issue14-business-rule-20260827/README.md) | Frozen evidence issue #14: semantic contracts, reviews, RED/GREEN/repeat receipts, native bindings, validators. |
| Skill `1c-enterprise-linux` | Переносимые operational/semantic instructions. Не хранит run-specific identities. |

## Классификация знаний

Каждый существенный вывод из issue #10/#14 имеет один основной слой.

| Вывод | Основной слой | Почему |
|---|---|---|
| Физическое разделение immutable snapshot/manifest/CF, writable work copy, disposable file ИБ и evidence/logs | Skill | Это reusable safety discipline для будущих write-cycle задач. |
| Native lifecycle `CREATEINFOBASE` → `DESIGNER /LoadConfigFromFiles /UpdateDBCfg` → `ENTERPRISE` runtime receipt | Skill | Командная форма и stop conditions повторяются; exact argv конкретного run остаётся evidence. |
| Успешная загрузка конфигурации не доказывает бизнес-поведение | Skill | Это reusable stop condition: platform acceptance ≠ runtime behavior. |
| Receipt должен быть машинно-проверяемым: terminal marker, уникальные labels/keys, value+type или domain observations, stable hash | Skill | Это переносимый критерий полного run; конкретные hashes не переносимы. |
| Data-backed posting probe должен наблюдать draft/posting state, `Posted`, recorder movements и balances по affected registers | Skill | Это reusable pattern для document posting semantics. |
| Semantic-contract sequence: business rule → formal predicate → plausible counterimplementations → distinguishing observations → minimal target/control/preservation cases → adversarial review before patch → RED/GREEN | Skill | Главный переносимый результат issue #14. Это не “добавить ещё один multi-row test”, а порядок построения oracle. |
| Capability ladder, non-claims и следующий gate | Project memory / docs | Это продуктовый статус, который должен жить в versioned документации. |
| Exact commits, trees, receipt hashes, nonces, native argv arrays, local run roots, reviewer chronology | Experiment/GitHub evidence | Эти факты проверяют конкретные claims, но не являются универсальными инструкциями. |
| Повторяющаяся механика native lifecycle, runtime polling, receipt parsing и identity checks | Tool candidates | Эти операции детерминированы и могут стать tools только после повторения боли на второй отличающейся задаче. |

## Capability ladder

Подтверждённые способности:

1. **Прийти → открыть → понять.** Read-only исследование одной feature-rich конфигурации доказано по frozen SDMS evaluation и независимой dual-agent приёмке; см. [`docs/sdms-evaluation.md`](sdms-evaluation.md).
2. **Локальная BSL-функция → native RED/GREEN.** Issue #10 доказала один технический write/runtime slice на Jet: минимальная правка одной функции, native load/update и runtime receipts с точным значением и типом.
3. **Один data-backed business rule → native RED/GREEN/repeat.** Issue #14 доказала один прикладной цикл на `InventoryWriteOff`: semantic contract, pre-production adversarial review, native RED, минимальный production patch, GREEN и clean repeat того же правила.
4. **Evidence can be made fail-closed for reproduced false positives.** Issue #14 validators закрыли конкретно воспроизведённые false-positive classes: summary mutation, native output identity mutation и native argv mutation with refreshed manifest.

Неподтверждённые способности:

- дешёвая повторяемость на **другой** прикладной задаче;
- универсальная write-среда разработки;
- metadata-object write support beyond bounded experiments;
- GUI/E2E validation, пользовательские сообщения, imports, undo/reposting semantics;
- production deployment или работа с live/production ИБ;
- переносимость на другие конфигурации, версии платформы и агентные клиенты.

Read-only остаётся режимом по умолчанию. Каждое новое write-изменение требует отдельной issue, физически отделённой work copy и disposable test ИБ.

## Baseline стоимости #10/#14

Это baseline, а не KPI. Где evidence не фиксирует фазовое время, документ не подставляет ложную точность.

| Метрика | Issue #10 | Issue #14 |
|---|---:|---:|
| Тип задачи | Локальная BSL-функция `StringToNumber` | Data-backed document posting rule `InventoryWriteOff` |
| Production diff | `+4/-0`, 1 файл | `+6/-0`, 1 файл |
| Task-specific instrumentation | `+35/-0`, 1 файл | `+328/-0`, 2 файла |
| Frozen package artifacts | 8 | 24 |
| Manifest artifact bytes | ~15 KB | ~141 KB |
| Runtime receipts | RED + GREEN | RED + primary GREEN + canonical GREEN #1 + canonical GREEN #2 |
| Clean repeat evidence | final clean run byte-matched committed runbook receipts | canonical repeat matched patched production bytes and meaningful observation vector |
| Временной сигнал | Фазовое время до RED/GREEN отдельно не зафиксировано; cost виден по runbook/package/review rounds | README issue #14 фиксирует rough ranges: reconnaissance ~20–40 min; entrypoint diagnostics ~1–2 h; accepted RED ~20–40 min; patch+primary GREEN ~15–30 min; repeat/binding/package hardening ~1–2 h |

Вывод: стоимость доминирует не production BSL patch. Самые дорогие повторяющиеся участки — native lifecycle orchestration, надёжный runtime probe, receipt/observation normalization, identity binding и fail-closed review against false positives.

## Tool candidates, без реализации в #16

### 1. Disposable IB bootstrap / native load-update helper

- Повторившаяся ручная работа: создать run root, скопировать snapshot в work copy, создать file ИБ, загрузить конфигурацию, выполнить `/UpdateDBCfg`, собрать DumpResult/log identities.
- Не должен скрывать: выбор business rule, production patch, instrumentation и oracle.
- Возможный контракт: `{platform, libs, snapshot, work_copy, infobase, env}` → `{argv, dump_result, log_sha256, success_markers}`.
- Ожидаемая экономия: несколько ручных command blocks и path substitutions на каждый RED/GREEN/repeat; вероятно десятки минут при повторении.
- Проверка полезности: вторая отличающаяся бизнес-задача должна пройти bootstrap/load/update без изменения helper-контракта.
- Почему не framework: операция детерминированна; semantic reasoning остаётся вне tool.

### 2. Runtime scenario runner / receipt polling helper

- Повторившаяся ручная работа: запуск `ENTERPRISE` под Xvfb, ожидание terminal marker, проверка hash stability, останов process group, сбор run result.
- Не должен скрывать: probe source, receipt schema и expected domain observations.
- Возможный контракт: `{infobase, receipt_path, timeout, complete_marker}` → `{completed, receipt_sha256, run_log_sha256, process_status}`.
- Ожидаемая экономия: меньше ошибок со stale client child, connection slots, неполными receipts и ручным polling.
- Проверка полезности: второй прикладной сценарий должен переиспользовать launch/poll/kill semantics без изменения.
- Почему не framework: lifecycle механика повторяема, смысл теста — нет.

### 3. Receipt / observation normalizer

- Повторившаяся ручная работа: парсинг `label###value###type` и `case###key###value`, duplicate/missing/extra rejection, нормализация nonce/document numbers/timestamps.
- Не должен скрывать: список cases, invariant fields, domain-specific assertions.
- Возможный контракт: `{receipt, schema}` → `{normalized_observation_vector, parse_errors}`.
- Ожидаемая экономия: меньше bespoke validator code и проще mutation tests.
- Проверка полезности: второй сценарий добавляет свои observation keys, но использует тот же parser semantics.
- Почему не framework: parser детерминирован; oracle остаётся задачеспецифичным.

### 4. Evidence identity/completeness checker

- Повторившаяся ручная работа: closed-set manifest, file hashes, private-path scan, summary-vs-receipt consistency, native argv/output binding.
- Не должен скрывать: какие artifacts являются authoritative и какие domain expectations применяются.
- Возможный контракт: `{package_dir, manifest, declared_schema}` → `{closed_set_ok, identity_ok, private_path_ok, binding_errors}`.
- Ожидаемая экономия: меньше review churn из-за refreshed-manifest false positives.
- Проверка полезности: второй сценарий должен доказать хотя бы одну refreshed-manifest mutation rejection без нового bespoke hardening framework.
- Почему не framework: это узкая completeness/identity проверка; не parser/index/RAG/plugin.

Статус всех candidates: **не реализовывать в #16**. Tool issue создавать только после второй отличающейся задачи, если та же механическая боль повторится.

## Контракт следующего low-cost эксперимента

Следующая отдельная issue должна выбрать другое содержательное бизнес-правило и пройти тот же путь:

1. frozen semantic contract;
2. native RED;
3. minimal production patch;
4. native GREEN;
5. clean repeat;
6. independent review.

Обязательные метрики:

| Метрика | Как измерять |
|---|---|
| Время поиска и первого honest RED | От старта read-only reconnaissance до первого complete native RED receipt. Отдельно отметить, была ли повторная entrypoint диагностика. |
| RED → GREEN | От accepted RED до complete GREEN; production patch time отдельно от evidence/package work. |
| Новая task-specific instrumentation | Files/LOC/bytes только для новой задачи. Цель — materially меньше #14 `+328`, если новая область не требует большего observation surface. |
| Reuse без изменений | Какие части native lifecycle/probe/evidence path использованы unchanged; каждое отклонение требует gap locator. |
| Manual operations | Количество ручных команд/подстановок/manifest updates/comments. |
| Повторившаяся боль | Одна конкретная механическая боль, повторившаяся второй раз и пригодная для узкого tool. |
| New abstractions | Должно быть `0`; исключение только через опубликованный blocker/gap и отдельное решение владельца. |

Не назначается произвольный процент улучшения. Бюджет выводится из #10/#14: второй проход должен показать, что уже найденный native/probe/evidence путь снижает entrypoint/review churn, либо честно доказать, какая детерминированная боль осталась.

## Текущий ответ на главный вопрос

- **Что теперь умеем повторять:** безопасное разделение source/work/IB/evidence, native create/load/update/runtime receipt lifecycle, fail-closed evidence packaging, semantic-contract review discipline.
- **Что пока умеем только один раз:** end-to-end изменение реального data-backed бизнес-правила на Jet; есть repeat того же правила, но нет второй отличающейся задачи.
- **Какая повторная боль первой заслуживает tool:** native lifecycle + runtime receipt polling/cleanup, если во второй задаче снова съест сопоставимое время. Пока это candidate, не implementation permission.
