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

В Git разрешено помещать только redacted summary без исходной конфигурации и raw
transcripts. Для открытой конфигурации допустим небольшой review package из
авторских вопросов, oracle items, ответов, per-item ledger и hashes, если он не
копирует исходный XML/BSL и не содержит секретов.

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
symlink/hard-link и размещение output/cache вне snapshot. Чтение выполняется
через descriptor-bound `O_NOFOLLOW` с проверкой стабильности `fstat`, а не через
схему «проверить путь, затем заново открыть его по имени».

## 4. Запустить arms

Каждый клиент получает одинаковые:

- snapshot content ID;
- `questions.json`;
- `contracts/answer.schema.json`;
- запрет записи в snapshot;
- запрет чтения oracle и чужих ответов.

Индекс или иной candidate-tool обязан хранить cache в объявленном `.local` cache root. Отрицательный результат индекса перепроверяется чтением XML/BSL.

## 5. Проверить ответы

```bash
python3 scripts/harness.py verify-answer \
  --experiment .local/experiments/<id>/experiment.json \
  --answer .local/experiments/<id>/answers/baseline.json \
  --output .local/experiments/<id>/evidence/baseline.verified.json
```

Проверка locators включает confinement, отсутствие symlink, существование файла,
совпадение прочитанных байтов с hash из принятого manifest, диапазон строк и
обратное покрытие каждого `fact`/`inference`. `assumptions` и
`unknowns` могут быть без locator. Семантическая истинность и отсутствие новых
существенных утверждений только в поле `answer` остаются задачей reviewer.

## 6. Adjudication и сравнение

Reviewer заполняет per-item ledger и hash-bound adjudication после выполнения обоих arms:

```bash
python3 scripts/harness.py compare \
  --experiment .local/experiments/<id>/experiment.json \
  --baseline .local/experiments/<id>/answers/baseline.json \
  --candidate .local/experiments/<id>/answers/candidate.json \
  --oracle .local/experiments/<id>/oracle.json \
  --ledger .local/experiments/<id>/adjudication-ledger.json \
  --adjudication .local/experiments/<id>/adjudication.json \
  --output .local/experiments/<id>/evidence/comparison.json
```

До вычисления `accepted` harness требует совпадения snapshot content ID,
question-set SHA-256, oracle SHA-256, ledger SHA-256 и SHA-256 обоих answers.
Oracle items и ledger должны совпасть по порядку и тексту; denominator, correct
totals и dangerous counts пересчитываются из ledger. `status=ok` означает
целостный frozen contract, но не человеческое подтверждение семантики.

Публичный 47-item пример и checklist находятся в
[`experiments/sdms-product-eval-20260825-review/`](../experiments/sdms-product-eval-20260825-review/).

## 7. Seal

```bash
python3 scripts/harness.py seal \
  --experiment .local/experiments/<id>/experiment.json \
  --artifact .local/experiments/<id>/evidence/preflight.json \
  --artifact .local/experiments/<id>/evidence/comparison.json \
  --output .local/experiments/<id>/evidence/artifact-manifest.json
```

`seal` повторно проверяет snapshot и создаёт новый manifest артефактов, не перезаписывая существующие файлы.
