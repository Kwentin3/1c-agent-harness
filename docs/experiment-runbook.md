# Воспроизводимый read-only эксперимент

`harness.py` проверяет неизменность снимка и машинные контракты. Он не запускает 1С или модель, не оценивает предметную семантику и не заменяет human adjudication.

## Раскладка

Закрытые или крупные данные остаются в `.local/`:

```text
.local/experiments/<id>/
├── experiment.json
├── questions.json
├── oracle.json
├── answers/
└── evidence/
```

В Git разрешено помещать только redacted summary без исходной конфигурации, raw transcripts и закрытого oracle.

## 1. Подготовить snapshot

Снимок создаётся штатным `/DumpConfigToFiles -Format Hierarchical`. Manifest содержит все файлы, отсортированные по относительному POSIX path:

```text
<sha256><два пробела><relative/path><LF>
```

`contentId` — `sha256:` плюс SHA-256 байтов manifest.

Все значения `--output` должны находиться внутри объявленного в experiment
`outputRoot`; родительский каталог создаётся заранее. Harness отклоняет output
внутри snapshot, output вне `outputRoot` и пересечение snapshot с
`outputRoot`/`cacheRoot` в любом направлении.

Перед выгрузкой задайте доступную UTF-8 locale (в лаборатории подтверждена
`en_US.utf8`). `LC_ALL=C` на конфигурации с кириллическими объектами может дать
имена с `?` и необратимо испортить locators. Preflight поэтому fail-closed
отклоняет любой manifest path с `?`; это осознанное ограничение формата harness.

## 2. Заморозить вопросы

`questions.json` содержит непустой массив `questions` с уникальными `id`. Зафиксируйте SHA-256 файла до запуска любого arm. Вопросы, порог и допустимые доказательства нельзя менять после просмотра ответов.

## 3. Preflight

```bash
mkdir -p .local/experiments/<id>/evidence
python3 scripts/harness.py preflight \
  --experiment .local/experiments/<id>/experiment.json \
  --output .local/experiments/<id>/evidence/preflight.json
```

Проверяются manifest/content ID, обязательные корневые `Configuration.xml` и
`ConfigDumpInfo.xml`, полный набор файлов, question hash, lossy `?` paths,
symlink/hard-link и размещение output/cache вне snapshot.

## 4. Запустить arms

Каждый клиент получает одинаковые:

- snapshot content ID;
- `questions.json`;
- `contracts/answer.schema.json`;
- запрет записи в snapshot;
- запрет чтения oracle и чужих ответов.

Индекс или иной candidate-tool обязан хранить cache в объявленном `.local` cache root. Отрицательный результат индекса перепроверяется чтением XML/BSL.

Для внешнего клиента с ограниченным output envelope предпочтителен unit-run:

1. один frozen question → один новый task;
2. native task record сохраняется неизменным;
3. client adapter извлекает ровно один `answer-unit.schema.json` payload;
4. `verify-unit` сразу проверяет форму, claim references и locators;
5. итог публикуется только когда присутствуют все frozen question IDs.

Пример строгого Antigravity extraction без repair:

```bash
python3 scripts/antigravity_adapter.py extract-unit \
  --task-record .local/experiments/<id>/runs/<arm>/Q1.task.json \
  --output .local/experiments/<id>/runs/<arm>/Q1.json
```

Retry policy фиксируется до запуска. Невалидный unit не разрешается вручную
редактировать, дополнять данными другого arm или превращать эвристикой в новый
семантический ответ.

## 5. Проверить ответы

```bash
python3 scripts/harness.py verify-answer \
  --experiment .local/experiments/<id>/experiment.json \
  --answer .local/experiments/<id>/answers/baseline.json \
  --output .local/experiments/<id>/evidence/baseline.verified.json
```

Проверка locators включает confinement, отсутствие symlink, существование файла и диапазона строк. Семантическая истинность факта остаётся задачей независимого reviewer.

## 6. Adjudication и сравнение

Reviewer заполняет `contracts/adjudication.schema.json` после выполнения обоих arms:

```bash
python3 scripts/harness.py compare \
  --experiment .local/experiments/<id>/experiment.json \
  --baseline .local/experiments/<id>/answers/baseline.json \
  --candidate .local/experiments/<id>/answers/candidate.json \
  --adjudication .local/experiments/<id>/adjudication.json \
  --output .local/experiments/<id>/evidence/comparison.json
```

`status=ok` означает сопоставимый frozen contract. Решение о принятии инструмента делается по `scores.*.accepted`, dangerous false claims, метрикам и заранее объявленному порогу.

## 7. Seal

```bash
python3 scripts/harness.py seal \
  --experiment .local/experiments/<id>/experiment.json \
  --artifact .local/experiments/<id>/evidence/preflight.json \
  --artifact .local/experiments/<id>/evidence/comparison.json \
  --output .local/experiments/<id>/evidence/artifact-manifest.json
```

`seal` повторно проверяет snapshot и создаёт новый manifest артефактов, не перезаписывая существующие файлы.
