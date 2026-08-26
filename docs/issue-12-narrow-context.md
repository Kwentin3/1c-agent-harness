# Issue #12 — минимальный достаточный контекст больших XML/BSL-выгрузок

**Статус:** эксперимент выполнен. Для проверенных задач достаточно стандартного direct-source подхода; новый компонент не добавлен.

Review package: [`experiments/issue12-narrow-context-20260826/`](../experiments/issue12-narrow-context-20260826/README.md).

## 1. Вопрос и границы

Проверялось, нужен ли агенту новый инструмент для сбора узкого, но достаточного контекста из больших split-выгрузок 1С. Симметричный baseline использовал обычные filename/content search и чтение исходника. Минимальный candidate использовал те же инструменты плюс bounded context-frontier protocol: identity binding → термины задачи → журнал выбранных hits → locator/bytes/rationale/claim → ограниченное расширение по owners/callers/effects → sufficiency checklist → stop.

Candidate не включал parser, индекс, graph, RAG, daemon, MCP, live-ИБ или новую зависимость. Результат ограничен двумя новыми задачами и не является универсальной оценкой всех конфигураций 1С.

Prior evidence issue #10 переиспользовано для класса локальной BSL/write-задачи без повторного прогона: [`docs/issue-10-write-cycle.md`](issue-10-write-cycle.md).

## 2. Дизайн до результатов

До открытия arm outputs были заморожены дизайн, output contract, task identities, candidate и threshold. Независимое Antigravity-review вернуло `FAIL` исходной методике до результатов. Поправка зафиксировала:

- только signed reduction считается улучшением;
- ≥25% reduction засчитывается, только если каждая другая наблюдаемая efficiency-метрика ухудшается не более чем на 10%;
- candidate-only essential relation также требует ≤10% regressions;
- добавляется same-term distractor negative;
- `/LoadConfigFromFiles /UpdateDBCfg` доказывает acceptance/schema consistency, не runtime semantics.

Хэши frozen design приведены в [`design.json`](../experiments/issue12-narrow-context-20260826/design.json).

## 3. Задачи

### SDMS: сквозной бизнес-путь

Из 2,581-файлового snapshot требовалось восстановить HTTP-запрос создания задачи по заявке на разработку, условия отказа, создаваемый объект и ключевые поля. Существенные source locators, независимо подтверждённые adjudicator'ом:

- HTTP metadata и POST binding: `HTTPServices/API.xml:459-526`;
- operation dispatch: `HTTPServices/API/Ext/Module.bsl:262-281`;
- API guards/parameters/manager call: `CommonModules/API/Ext/Module.bsl:995-1020,5085-5088`;
- business conditions, task write и inherited data: `Documents/ЗаявкаНаРазработку/Ext/ManagerModule.bsl:376-473,813-869`;
- same-term distractor, не являющийся путём создания: `Reports/ЗадачиПоЗаявкам.xml:3-26`.

### Jet: минимальная metadata/write-задача

Первый исторический кандидат был отклонён до arms: 18 файлов и полный report subsystem не изолировали metadata capability. Заморожена синтетическая задача: один item-level Boolean `AllowNegativeInventoryBalance` в `Catalog.Warehouses`, false by default, без forms/BSL/runtime enforcement.

Исходный owner: `Catalogs/Warehouses.xml:26-40,344-365`; локальный пример сериализации Boolean: `Catalogs/EmailAccounts.xml:528-580`. Оба arm изменили только `Catalogs/Warehouses.xml` и прошли нативный Designer gate.

## 4. Результаты

### SDMS

| Метрика | Baseline | Candidate | Candidate к baseline |
|---|---:|---:|---:|
| Oracle items | 9/9 | 9/9 | tie |
| Dangerous claims / invalid locators | 0 / 0 | 0 / 0 | tie |
| Context bytes | 24,966 | 30,448 | **+21.96%** |
| Navigation operations | 49 | 56 | **+14.29%** |
| Wall clock | 386 s | 342 s | −11.40% |

Candidate не дал новой oracle-essential связи и не достиг 25% reduction. Он отклоняется и по исходному, и по исправленному threshold. Полный ledger: [`adjudication/sdms-review.md`](../experiments/issue12-narrow-context-20260826/adjudication/sdms-review.md).

### Jet

| Метрика | Baseline | Candidate | Candidate к baseline |
|---|---:|---:|---:|
| Correct semantic fields | 11/11 | 10/11 (`FullTextSearch=Use`) | candidate hard-gate fail |
| Native create/load/update | PASS | PASS | tie |
| Selected source files / fragments | 2 / 3 | 3 / 5 | regression |
| Selected source lines / bytes | 90 / 2,860 | 218 / 7,438 | **+160.07% bytes** |
| Observed wall clock | 480 s | 347.93 s | **−27.51%** |

Candidate включил полнотекстовый поиск для нового реквизита, хотя задача просила минимальный metadata-флаг и baseline использовал `DontUse`. Нативный load подтверждает допустимость XML для платформы, но не устраняет лишнюю семантику. Поэтому candidate проигрывает исходный hard coverage gate. Дополнительно поправка, замороженная до результатов, отклоняет efficiency signal: source-context regression 160.07% значительно превышает Pareto ceiling 10%, а сравнимый operation count candidate не был сохранён.

Обе нативные проверки использовали физически разные work copies и disposable ИБ на 1C training 8.5.1.1150. `CREATEINFOBASE` и `DESIGNER /LoadConfigFromFiles /UpdateDBCfg` дали process exit 0, exact DumpResult 0 и success marker; snapshot до/после: 5,099 listed/actual, missing/extra/mismatch/symlink = 0. Санитизированные receipts: [`evidence/`](../experiments/issue12-narrow-context-20260826/evidence/).

## 5. Дефект Jet oracle

Private oracle требовал конкретный UUIDv5, одновременно public blind task запрещал раскрывать algorithm и expected UUID. Это произвольное скрытое условие невозможно честно вывести из задачи. Oracle не переписан задним числом: дефект явно оставлен в adjudication. Для arm comparison принято семантически корректное условие — UUID уникален, синтаксически валиден, не конфликтует, а полный source нативно загружается и обновляет disposable ИБ. Оба arm его выполнили.

## 6. Негативные сценарии

Fail-closed тесты реально отклоняют:

1. **stale binding** — другой content ID;
2. **insufficient context** — удалён essential fragment request manager из SDMS packet;
3. **same-term distractor** — report `ЗадачиПоЗаявкам` подставлен как evidence HTTP creation chain;
4. **scope expansion** — Jet context включает form/BSL или serialization registration;
5. **package contamination** — missing, changed или unlisted artifact.

Проверки находятся в [`tests/test_issue12_evidence.py`](../tests/test_issue12_evidence.py).

## 7. Решение

**Оставить direct-source baseline. Не добавлять новый инструмент или runtime component.**

Bounded-frontier полезен как дисциплина рассуждения и источник checklist, но в этих runs он не оправдал измеренную стоимость. Это не запрещает будущую проверку parser/index/graph на задаче, где direct source воспроизводимо теряет essential relation; такой gap в issue #12 не обнаружен.

Machine-readable verdict: [`decision.json`](../experiments/issue12-narrow-context-20260826/decision.json).

## 8. Воспроизведение и ограничения

```bash
python3 -m unittest tests.test_issue12_evidence -v
python3 -m unittest discover -s tests -v
git diff --check
```

Native replay требует лаборатории из [`docs/lab.md`](lab.md) / [`docs/lab-bootstrap.md`](lab-bootstrap.md), нового уникального run root, writable copy snapshot и disposable file ИБ. Подробная последовательность и patches находятся в package README. Исходные CF, snapshots, manifests и живые ИБ не изменяются.

Не доказаны: статистическое преимущество подхода, переносимость на другие metadata kinds/конфигурации/платформы, runtime enforcement нового Jet-реквизита, production write support или поддержка произвольных изменений. Read-only остаётся режимом по умолчанию.
