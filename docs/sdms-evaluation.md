# SDMS: доказательный read-only эксперимент

Дата: 2026-08-25. Этот документ — redacted summary. Полный snapshot, вопросы,
oracle, ответы, transcripts, индексы и машинные evidence остаются в `.local/` и
не публикуются.

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
- все locators затем проверены машинно по существованию файла и диапазону строк.

Это независимая агентная adjudication, но не экспертная приёмка владельцем SDMS.
До runs не был создан отдельный криптографически запечатанный manifest prompts,
tool budgets и isolation policy. Поэтому сохранённый пакет подтверждает содержимое
артефактов, но не позволяет независимо восстановить полную симметрию arm из одного
публичного документа.

## Arms и результаты

| Метрика | Baseline: XML/BSL | Candidate: `cf-index` + `ast-index` + source fallback |
|---|---:|---:|
| Факты, совпавшие с oracle | 45 / 47 | 44 / 47 |
| Oracle alignment | 95,74% | 93,62% |
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
2. `scripts/harness.py` проверяет frozen inputs, безопасность, locators,
   adjudication и seal;
3. стандартное чтение/search XML/BSL оказалось достаточно для данного run;
4. `cf-index` и `ast-index` не входят в обязательную реализацию: на этом
   run они не улучшили oracle alignment, а причинное преимущество эффективности
   не доказано;
5. отдельный parser, RAG, MCP, graph или fork не требуются.

Это решение не запрещает повторный candidate-test на другом корпусе. Оно запрещает
объявлять индекс обязательным по одному направляющему Jet-run, когда один
feature-rich SDMS A/B не дал положительного сигнала.

## Воспроизведение

После законного получения закреплённого CF и создания `.local` snapshot:

```bash
mkdir -p .local/experiments/<id>/runs/reproduction
python3 scripts/harness.py preflight --experiment .local/experiments/<id>/experiment.json --output .local/experiments/<id>/runs/reproduction/preflight.json
python3 scripts/harness.py verify-answer --experiment .local/experiments/<id>/experiment.json --answer .local/experiments/<id>/runs/baseline/answer.json --output .local/experiments/<id>/runs/baseline/verified.json
python3 scripts/harness.py compare --experiment .local/experiments/<id>/experiment.json --baseline .local/experiments/<id>/runs/baseline/answer.json --candidate .local/experiments/<id>/runs/candidate/answer.json --adjudication .local/experiments/<id>/adjudication.json --output .local/experiments/<id>/runs/reproduction/comparison.json
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
