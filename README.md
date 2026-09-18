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

Для этого проекта target — canonical JetTr `1.0.3.1`. Полученный data-only `SnapshotRef`
передаётся следующим read-only инструментам.

### Поиск по admitted snapshot (V1)

Готовый маршрут для fresh executor — `open → search`. Сначала сохранить единственный
machine-readable `SnapshotRef`, затем передать именно этот файл поиску:

```bash
mkdir -p .local/search-session
python3 scripts/project_target.py open --repo-root . \
  > .local/search-session/snapshot-ref.json

python3 scripts/snapshot_search.py \
  --repo-root . \
  --snapshot-ref .local/search-session/snapshot-ref.json \
  --query 'Procedure\\s+Posting' \
  --mode regex \
  --path-prefix Documents/SalesInvoice/Ext
```

`open` остаётся единственным владельцем source, contract, retained storage и admission.
`search` принимает только точный data-only `SnapshotRef`, разрешает его через target boundary и
читает manifest-declared файлы. V1 намеренно ищет только `.bsl` и `.xml`; системный `rg`, сеть,
1С, индекс, cache и parser не требуются. Результат — deterministic JSON с relative `path`, `line`,
bounded `fragment` и явным `truncated`; доступны `literal` и `regex` modes и относительный
`--path-prefix`.

Для разрешённых прикладных write-проверок task-specific копия размещается отдельно под `.local/prepared/`. Единственная продуктовая команда такой проверки —
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

### Установленный executor companion и Hermes plugin

`one-c-harness` — один installable companion из этого же canonical tree. Он устанавливается
один раз **у executor рядом с уже подготовленным 1С runtime**, а не копируется в business
workspace:

```bash
python3 -m pip install --no-deps /immutable/source/revision
```

Его entrypoint `one-c-harness --request-stdin` принимает один closed JSON envelope
`{schemaVersion: 1, operation, arguments}` и берёт project root только из текущего `cwd`
terminal backend. Доступны `open`, `narrow` и `verify`; `narrow` и `verify` принимают только
точный admitted `SnapshotRef`, а task artifacts для `verify` должны быть repository-relative.
Он использует уже существующий executor locator `.local/one-c-runtime.json`, поэтому не требует
`.local/platform`, Harness checkout или SSH credential в business workspace.

Standalone Hermes plugin лежит в [`hermes-plugin/`](hermes-plugin/). Он регистрирует только
`one_c_open`, `one_c_narrow_context`, `one_c_native_verify` и короткую plugin skill. Plugin
формирует тот же JSON, вызывает только public `ctx.dispatch_tool("terminal", ...)` и не
реализует SSH, executor discovery или workspace mapping. Версия plugin и companion сейчас
`0.1.0`; operator обязан pin-ить оба install sources к одному immutable Git revision. Любой
несовпадающий `capabilityVersion` блокируется fail-closed.

Эти source artifacts сами по себе не включают SSH backend и не выполняют deployment/restart.
Remote executor и его selected workspace должны быть явно настроены terminal boundary до
установочного canary.

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
