# SDMS: доказательный read-only эксперимент

Дата: 2026-08-25. Полный snapshot, transcripts и индексы остаются в `.local/`.
Небольшой пакет вопросов, oracle, точных answers, 47-item ledger и hashes
опубликован в
[`experiments/sdms-product-eval-20260825-review/`](../experiments/sdms-product-eval-20260825-review/);
он не содержит исходный XML/BSL.

## Объект исследования

Использована открытая конфигурация
[DNS Technologies / SDMS](https://github.com/dns-technologies/SDMS) на commit
`eb372065e273ceade9939542ce56565c4d422e91`, лицензия GPL-3.0.

| Артефакт | Значение |
|---|---|
| Исходный CF SHA-256 | `426d2049ff87af8e987b4d542ce3f75f3c4f73713d5a69cc5085aecb489722f8` |
| Платформа лаборатории | официальная учебная 1С `8.5.1.1150`, Linux x86_64 |
| Snapshot | штатный `LoadCfg → DumpConfigToFiles -Format Hierarchical` |
| Snapshot content ID | `sha256:3357ee63204ff863aac116417927240930084dce0eb7613126ad88cff68a424d` |
| Размер | 2581 файл, 646 BSL |
| Основные объекты | 54 Catalog, 10 Document, 100 CommonModule, 103 InformationRegister, 24 ScheduledJob, 1 HTTPService |

Две последовательные штатные выгрузки дали одинаковые 2581 пути и содержимое.
Исходный CF и snapshot после эксперимента повторно совпали с закреплёнными
SHA-256. Управление GUI и запись в исследуемую конфигурацию не применялись.

## Зафиксированный протокол

До runs в локальной сессии были записаны и сделаны read-only семь вопросов:
паспорт, назначение и масштаб, статическая
цепочка HTTP API → общий модуль → менеджер документа, проведение трудозатрат,
регламентный механизм и мессенджеры, Bearer/JWT-проверка и обязательные
неизвестные о runtime.

- question-set SHA-256:
  `3eba62e70085d74f954968832f5c5d9ab06db0c0da44e83af6bf22651fcbcd90`;
- oracle SHA-256:
  `761cb235b9fd2d984a4c4817104f26b58760062bc9d863f03600aec53b0f674f`;
- oracle подготовлен до runs по upstream-документации и XML/BSL snapshot;
- оба arm были запущены с одинаковыми snapshot, вопросами, answer contract и
  запретом читать oracle/ответ другого arm;
- пользователь делегировал агенту роль human-in-the-loop; итоговые 47 атомарных
  фактов отдельно adjudicated агентом, не участвовавшим в arms;
- answer и oracle locators затем проверены машинно по пути в manifest, hash
  принятых байтов и диапазону строк.

Это независимая агентная adjudication, но не экспертная приёмка владельцем SDMS.
До runs не был создан отдельный криптографически запечатанный manifest prompts,
tool budgets и isolation policy. Поэтому сохранённый пакет подтверждает содержимое
артефактов, но не позволяет независимо восстановить полную симметрию arm из одного
публичного документа.

## Arms и результаты

| Метрика | Baseline: XML/BSL | Candidate: `cf-index` + `ast-index` + source fallback |
|---|---:|---:|
| Exact oracle coverage | 45 / 47 | 44 / 47 |
| Exact oracle coverage, % | 95,74% | 93,62% |
| Dangerous false claims | 0 | 0 |
| Время | 154 с | 204 с |
| Transcript tool operations | 44 | 53 |
| Проверенные locators | 34 | 36 |

Candidate построил `cf-index` на 752 объекта (`missing=0`) и `ast-index 3.50.0`
на 646 BSL-файлов (15 563 symbols), но каждый вывод подтверждал исходным XML/BSL.
В сохранённой телеметрии этого run candidate занял на 32,47% больше времени и
потребовал на 20,45% больше transcript operations. Это описательное наблюдение,
не оценка причинного overhead: arm не повторялись, а единицы scheduler/tool
telemetry не были заранее нормализованы независимым протоколом.

Потери фактов не были опасными: оба arm выбрали другой корректный ScheduledJob,
чем конкретный preregistered пример, и не полностью перечислили один составной
unknown; candidate дополнительно не упомянул sprint в составном факте Q2.

## Решение

Для MVP выбран **baseline direct-source workflow**:

1. штатный полный snapshot и manifest остаются источником истины;
2. `scripts/harness.py` проверяет frozen inputs, безопасность, claim→locator
  coverage, hash-bound adjudication и seal;
3. стандартное чтение/search XML/BSL оказалось достаточно для данного run;
4. `cf-index` и `ast-index` не входят в обязательную реализацию: на этом
   run они не улучшили exact oracle coverage, а причинное преимущество эффективности
   не доказано;
5. отдельный parser, RAG, MCP, graph или fork не требуются.

Это решение не запрещает повторный candidate-test на другом корпусе. Оно запрещает
объявлять индекс обязательным по одному направляющему Jet-run, когда один
feature-rich SDMS A/B не дал положительного сигнала.

## Финальная dual-agent приёмка понимания

Финальный продуктовый гейт ограничен сценарием **«прийти → открыть → понять»**.
Редактирование конфигурации, прикладные runtime-тесты и использование в живой ИБ
в эту приёмку не входят.

Два прохода были сформированы независимо:

1. основной агент исследовал frozen snapshot стандартным файловым поиском и
   чтением XML/BSL, затем зафиксировал свой отчёт до открытия 47-item package;
   SHA-256 локальной фиксации —
   `77f334f5efdf04c25b047c2283281691ac53ee68bacd7646be9442bb1f478101`;
2. независимый reviewer получил только цель, snapshot root, manifest и ожидаемый
   content ID — без готового вывода и без подсказок о путях. Он отдельно
   зафиксировал взгляд до открытия package; SHA-256 фиксации —
   `aa5f2f89e672dd6c9e6c03fa41429ca1db81a772ecae58c24f666d550b5fa9ef`.

Оба прохода независимо пришли к совместимому пониманию:

- SDMS — корпоративная система управления разработкой и проектами: заявки,
  задачи, проекты и спринты, Kanban/QA, трудозатраты, доступ и уведомления;
  `Catalogs/ВидыДеятельности/Ext/ManagerModule.bsl:1-7`,
  `Catalogs/ИнструментыСистемы/Ext/ManagerModule.bsl:213-267`;
- паспорт совпал по имени, поставщику, версии, managed run mode, Russian script
  variant и extension compatibility mode; `Configuration.xml:34-56`;
- основной проход проследил статическую цепочку HTTP POST → общий модуль API →
  менеджер заявки → проверенная запись новой задачи;
  `HTTPServices/API/Ext/Module.bsl:262-281`,
  `CommonModules/API/Ext/Module.bsl:995-1019`,
  `Documents/ЗаявкаНаРазработку/Ext/ManagerModule.bsl:376-473`;
- reviewer независимо проследил более длинное продолжение: связь задачи с
  заявкой, обновление иерархии/Kanban, Trello и плановых трудозатрат, включение в
  спринт и возможную запись фактических трудозатрат;
  `Documents/Задача/Ext/ObjectModule.bsl:320-365`,
  `Documents/Задача/Forms/ФормаДокумента/Ext/Form/Module.bsl:577-596`,
  `Documents/Задача/Ext/ObjectModule.bsl:650-668`;
- оба отделили static evidence от неизвестных о публикации API, живых данных,
  ролях/токенах, активности заданий, настройках интеграций и production state.

### Разрешённые различия и найденный риск

- Разная длина выбранной бизнес-цепочки — дополнение, а не противоречие: обе
  цепочки сходятся на создании `Документ.Задача`, а продолжение reviewer
  подтверждено тем же XML/BSL.
- Known misses frozen answers — другой корректный ScheduledJob, неполный
  составной unknown и пропуск sprint у candidate — остаются неизменными в
  frozen artifacts. Это объясняет exact oracle coverage 45/47 и 44/47, но не
  создаёт опасного расхождения в итоговом понимании.
- Reviewer дополнительно обнаружил, что при отказе проверки токена полный bearer
  token включается в текст ошибки журнала;
  `InformationRegisters/ТокеныДоступаПользователей/Ext/ManagerModule.bsl:163-171`.
  Это подтверждённый статический security risk исходной конфигурации, не
  исправление текущего read-only этапа и не доказанный runtime exploit.

Все 29 locators основного отчёта и 33 полных locators reviewer проверены по
manifest path/hash и диапазонам. Неразрешённых опасных противоречий между
проходами нет. До и после приёмки manifest содержит 2581 файл с тем же content ID
`sha256:3357ee63204ff863aac116417927240930084dce0eb7613126ad88cff68a424d`.

**Вердикт:** этап 1 принят для ограниченной способности агента самостоятельно
«прийти, открыть и понять» эту feature-rich конфигурацию. Это dual-agent
операционная приёмка, делегированная владельцем, а не экспертная приёмка
владельцем SDMS; коррелированные ошибки моделей, runtime-поведение и
переносимость на другие конфигурации ею не исключены.

## Воспроизведение

После законного получения закреплённого CF и создания `.local` snapshot:

```bash
mkdir -p .local/experiments/<id>/runs/reproduction
python3 scripts/harness.py preflight --experiment .local/experiments/<id>/experiment.json --output .local/experiments/<id>/runs/reproduction/preflight.json
python3 scripts/harness.py verify-answer --experiment .local/experiments/<id>/experiment.json --answer .local/experiments/<id>/runs/baseline/answer.json --output .local/experiments/<id>/runs/baseline/verified.json
python3 scripts/harness.py compare --experiment .local/experiments/<id>/experiment.json --baseline .local/experiments/<id>/runs/baseline/answer.json --candidate .local/experiments/<id>/runs/candidate/answer.json --oracle .local/experiments/<id>/oracle.json --ledger .local/experiments/<id>/adjudication-ledger.json --adjudication .local/experiments/<id>/adjudication.json --output .local/experiments/<id>/runs/reproduction/comparison.json
```

Полный порядок и fail-closed ограничения описаны в
[`experiment-runbook.md`](experiment-runbook.md).

## Границы доказательства

Подтверждено статическое исследование одного открытого feature-rich snapshot на
одной модели и по одному run каждого arm, а также совпадение ответов с локальным
oracle по описанной ledger. Не подтверждены экспертная предметная корректность,
симметрия arm за пределами сохранённых artifacts, runtime-данные живой ИБ,
production web publication, фактические токены/роли/регламентные задания,
переносимость на другие модели, старая платформа и статистическое преимущество по
нескольким повторениям.
