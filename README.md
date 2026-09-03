# 1C Agent Harness

Экспериментальный harness, который помогает кодовому агенту безопасно исследовать незнакомые конфигурации 1С:Предприятия и давать проверяемые ответы о коде, метаданных и бизнес-процессах.

> Статус: этапы 0 и 1 подтверждены. На открытой функционально насыщенной SDMS
> direct-source baseline прошёл frozen eval, а последующая делегированная
> dual-agent приёмка независимо подтвердила способность «прийти → открыть →
> понять» по исходным XML/BSL. Индексный arm не показал преимущества в этом run.

> Это не экспертная приёмка владельцем SDMS, не runtime-проверка и не гарантия
> переносимости. Обобщение требует повторов на других конфигурациях. Следующие
> этапы также имеют внешние prerequisites: точная старая платформа и второй
> arm-proven coding-agent client.

> Дополнительно (issue #10): выполнен и задокументирован **один узкий write/runtime vertical
> slice** на учебной конфигурации Jet — минимальная BSL-правка одной функции,
> нативная загрузка в одноразовую ИБ, RED/GREEN runtime-прогон с точным значением и типом
> и fail-closed evidence package
> ([experiments/issue10-write-cycle-20260826](experiments/issue10-write-cycle-20260826/README.md)).
> Это НЕ универсальная write-платформа и не доказательство переносимости на
> metadata-объекты, другие конфигурации, старые платформы или другие агентные клиенты.
> Технический Jet write/runtime slice issue #10 принят, PR #11 смержен. Read-only остаётся
> режимом по умолчанию: этот результат подтверждает только один узкий сценарий, а каждое
> следующее write-изменение требует отдельной issue, отделённой work copy и disposable test ИБ
> (см. AGENTS.md).

> Дополнительно (issue #14 / PR #15): выполнен один прикладной data-backed write-cycle
> на Jet `InventoryWriteOff` — semantic contract до production patch, native RED,
> минимальный production patch, native GREEN и clean repeat того же правила. Это доказывает
> один реальный бизнес-правило-срез, но ещё не доказывает дешёвую повторяемость на другой
> задаче, универсальную write-среду, metadata changes, GUI/E2E или production deployment.
> Knowledge handoff и следующий gate зафиксированы в
> [`docs/write-cycle-knowledge-handoff.md`](docs/write-cycle-knowledge-handoff.md).

## Открытие project target

Из корня репозитория единственная входная команда получает или восстанавливает проверенный
`SnapshotRef`:

```bash
python3 scripts/project_target.py open
```

[`project-target.json`](project-target.json) объявляет ровно один source и ожидаемую identity.
Поддержаны существующий admitted snapshot, полная hierarchical выгрузка и `.cf`. Hierarchical
source принимается без 1С; `.cf` материализуется встроенным repo-owned маршрутом
`CREATEINFOBASE → /LoadCfg → /DumpConfigToFiles -Format Hierarchical`. Внешними остаются только
платформа 1С, Xvfb/libs и лицензия. При их отсутствии команда возвращает один
`materializer_unavailable` с locator на [`docs/lab-bootstrap.md`](docs/lab-bootstrap.md); она
ничего не скачивает и не устанавливает.

Единственный executor-level locator — игнорируемый Git файл `.local/one-c-runtime.json`. Он не
является project contract и не попадает в `SnapshotRef`; schema v1 содержит абсолютные пути
`platform`, `xvfb`, `fontconfig`, `libs`. Это позволяет executor выбрать заранее подготовленный
runtime без зашивания конфигурации, её версии или provider route в harness.
EDT, CFE, CFU, DT, EPF, живые ИБ и remote executors в v1 возвращают `unsupported_source`.

Admission в `project_target.py` проверяет закрытый manifest/file set, hashes, read-only режим и
`Configuration/Properties`. Только после него snapshot и manifest атомарно публикуются вместе под
`.local/targets/`, вне disposable `.local/runs/` и `.local/prepared/`. Повторный `open` строго
проверяет и переиспользует тот же retained target без source и native-запуска; повреждённый target
не исправляется и не перезаписывается.

Для этого проекта target — canonical JetTr `1.0.3.1`. Полученный `snapshot.root` передаётся
следующим read-only инструментам. Для разрешённых прикладных write-проверок task-specific копия
размещается отдельно под `.local/prepared/`. Единственная продуктовая команда такой проверки —
[`scripts/shared_task_route.py run`](scripts/shared_task_route.py). Она сама создаёт disposable
prepared path, применяет task-owned exact patches, вычисляет derived identities, вызывает
низкоуровневый `native_cycle.py run-prepared`, передаёт raw receipts предметному oracle, возвращает
короткий receipt и удаляет prepared tree. `native_cycle.py` остаётся внутренним lifecycle owner,
а исторический `issue38_frontdoor.py` — только compatibility alias той же команды, не второй route.

```bash
python3 scripts/shared_task_route.py run \
  --repo-root . \
  --input-tree .local/runs/training-jet-review-final/snapshot \
  --request experiments/<task>/request.json \
  --production-patch experiments/<task>/exact-production.patch \
  --instrumentation-patch experiments/<task>/exact-instrumentation.patch \
  --oracle experiments/<task>/oracle.py \
  --receipt .local/<task>/receipt.json
```

Перед командой не нужен отдельный prepare, replay или расчёт `changedPaths`/`treeIdentity`.
Стандартный receipt связывает canonical base, exact patch hashes, prepared/frozen input, свежий
request, raw 1C receipts, oracle result и cleanup. Полный representative task layer —
contract, request, exact production patch, exact instrumentation patch и maintainable oracle —
показан в [`experiments/issue48-kiss-receipt`](experiments/issue48-kiss-receipt/).
Исторические packages не переписываются, а candidate commit/tree и CI остаются ответственностью
GitHub, не task validator.

## Контекст одного документа

Когда exact `Document.<Name>` уже найден обычным `rg`, команда принимает только сериализованный
`SnapshotRef`, ранее выданный `project_target.py open`, и повторно проверяет его через тот же
retained-target admission boundary:

```bash
python3 scripts/project_target.py open > .local/snapshot-ref.json
python3 scripts/object_context.py inspect \
  --snapshot-ref .local/snapshot-ref.json \
  --object Document.SupplierInvoice \
  --focus Warehouse
```

JSON содержит descriptor, реквизиты и табличные части, принадлежащие XML/BSL/form/template
артефакты, короткий outline процедур с line locators, `DataPath`/события/команды форм и
одношаговые конфигурационные связи. `Document` — единственный поддержанный тип v1; прочие
canonical metadata identifiers возвращают `unsupported`. Полные BSL/XML, рекурсивный граф,
семантические выводы и постоянный index не строятся. Все списки детерминированно ограничены:
`truncated` и `diagnostics` обязательны, когда часть ответа не помещается.

## Цель MVP

Кодовый агент в Linux-окружении получает снимок конфигурации 1С и может:

- определить назначение конфигурации и основные предметные области;
- найти значимые объекты метаданных, модули и связи между ними;
- проследить ограниченный бизнес-сценарий от точки входа до последствий;
- подкрепить существенные выводы точными ссылками на источники;
- явно отделить подтверждённые факты от предположений и неизвестного;
- завершить исследование, не изменив конфигурацию или информационную базу.

MVP считается полезным не потому, что агент написал убедительный отчёт, а потому, что его ответы воспроизводимы и выдерживают проверку по заранее определённым критериям.

## Подход

- **Native-first:** платформа 1С остаётся источником истины и по возможности сама создаёт и проверяет снимок.
- **Файловая рабочая модель:** агент исследует воспроизводимую выгрузку, а не GUI Конфигуратора.
- **Read-only по умолчанию:** изменение конфигурации не входит в первую стадию MVP.
- **Композиция до форка:** сначала используем готовые инструменты как внешние зависимости и форкаем только при доказанной несовместимости.
- **Независимость от агента:** формат снимка и evidence-контракт не зависят от клиента; готовность каждого конкретного клиента доказывается отдельным arm.
- **KISS:** каждая зависимость, абстракция и служба должна закрывать уже наблюдаемую потребность.

## Hermes Workspace

Основная папка Hermes Project Workspace используется непосредственно как корень этого Git-репозитория и `cwd` агентной сессии. Отдельный workspace внутри неё не создаётся.

Дистрибутивы, тестовые конфигурации, снимки, индексы и другие машинно-локальные данные размещаются в `.local/`, который исключён из Git. Место установки платформы зависит от фактического terminal backend Hermes и определяется на нулевом этапе.

## Документы

- [Продуктовый бриф](docs/product.md)
- [Архитектура и контрактные границы](docs/architecture.md)
- [Методика оценки](docs/evaluation.md)
- [Обзор существующих решений](docs/research.md)
- [Дорожная карта](ROADMAP.md)
- [Нативная лаборатория 1С под Linux](docs/lab.md)
- [Runbook read-only эксперимента](docs/experiment-runbook.md)
- [Client-neutral протокол](docs/client-protocol.md)
- [Результат SDMS A/B](docs/sdms-evaluation.md)
- [Публичный SDMS review package](experiments/sdms-product-eval-20260825-review/README.md)
- [Подтверждённая граница совместимости](docs/compatibility.md)
- [Готовность агентных клиентов](docs/client-readiness.md)
- [Headless request/response baseline (issue #38)](docs/issue-38-headless-request-response.md)
- [Knowledge handoff write-cycle экспериментов](docs/write-cycle-knowledge-handoff.md)
- [Правила работы кодового агента](AGENTS.md)

## Evidence harness

`scripts/harness.py` не запускает модель и не парсит 1С. Он проверяет frozen snapshot/question contracts, существование locators, сопоставимость двух arms и неизменность снимка при запечатывании evidence:

```bash
python3 scripts/harness.py --help
python3 -m unittest -v tests/test_harness.py
```

Крупные snapshots, raw transcripts и индексы остаются в `.local/`. Для открытого SDMS в Git опубликован только небольшой review package из авторских вопросов, oracle items, ответов, per-item ledger и hashes — без исходного XML/BSL, закрытого кода и секретов.

## Как работать с репозиторием

Кодовый агент должен сначала прочитать `AGENTS.md` и документы, на которые ссылается выбранная GitHub issue. Issue задаёт конечную цель, критерии приёмки и границы полномочий, но не предписывает реализацию. Агент самостоятельно исследует варианты, выбирает путь, проводит эксперименты и доводит результат до проверяемого состояния. Начинать следует с этапа 0, даже несмотря на исторический номер issue `#2`.

## Лицензия

Лицензия проекта пока не выбрана. До её выбора нельзя копировать в репозиторий код сторонних проектов. Внешние инструменты следует запускать отдельно и фиксировать их версии и лицензии.
