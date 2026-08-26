# SDMS frozen review package

Небольшой публичный пакет для человеческой проверки результата этапа #1. Он
связывает exact oracle coverage 45/47 и 44/47 с точными байтами вопросов, oracle, обоих
ответов и 47-item adjudication ledger. Исходный код SDMS и snapshot в пакет не
включены.

## Что внутри

- `questions.json` — семь frozen вопросов;
- `oracle.json` — 47 заранее подготовленных expected items и исходные locators;
- `answers/*.json` — точные проверенные ответы двух arms;
- `adjudication-ledger.json` — решение reviewer по каждому из 47 items,
  rationale и locators из соответствующего answer;
- `adjudication.json` — totals и SHA-256 всех входов оценки;
- `comparison.json` — receipt, полученный `harness.py compare`;
- `package-manifest.json` — SHA-256 публичных review-артефактов;
- `experiment.json.example` — воспроизводимая локальная раскладка prerequisite.

Пакет содержит авторские вопросы, оценки, фактические утверждения и locators, но
не копирует XML/BSL конфигурации. Исследуемый upstream —
[DNS Technologies / SDMS](https://github.com/dns-technologies/SDMS) commit
`eb372065e273ceade9939542ce56565c4d422e91`, GPL-3.0. Публикация этого пакета не
выбирает лицензию самого `1c-agent-harness`.

## Локальный prerequisite

Для перехода от locator к исходному XML/BSL нужен тот же snapshot:

- официальный учебный клиент 1С `8.5.1.1150`;
- исходный CF SHA-256
  `426d2049ff87af8e987b4d542ce3f75f3c4f73713d5a69cc5085aecb489722f8`;
- штатный `LoadCfg → DumpConfigToFiles -Format Hierarchical`;
- snapshot content ID
  `sha256:3357ee63204ff863aac116417927240930084dce0eb7613126ad88cff68a424d`;
- локальные пути `.local/runs/sdms-native-02/snapshot/` и
  `.local/runs/sdms-native-02/snapshot.manifest`.

Получение платформы и snapshot описано в `docs/lab.md` и
`docs/experiment-runbook.md`. Если content ID отличается, этот adjudication
нельзя применять.

## Машинная проверка

Создайте новые локальные каталоги, не перезаписывая старые receipts:

```bash
mkdir -p .local/experiments/sdms-product-eval-20260825/review-runs/manual
mkdir -p .local/experiments/sdms-product-eval-20260825/review-cache

python3 scripts/harness.py preflight \
  --experiment experiments/sdms-product-eval-20260825-review/experiment.json.example \
  --output .local/experiments/sdms-product-eval-20260825/review-runs/manual/preflight.json

python3 scripts/harness.py verify-answer \
  --experiment experiments/sdms-product-eval-20260825-review/experiment.json.example \
  --answer experiments/sdms-product-eval-20260825-review/answers/baseline.json \
  --output .local/experiments/sdms-product-eval-20260825/review-runs/manual/baseline.json

python3 scripts/harness.py verify-answer \
  --experiment experiments/sdms-product-eval-20260825-review/experiment.json.example \
  --answer experiments/sdms-product-eval-20260825-review/answers/candidate.json \
  --output .local/experiments/sdms-product-eval-20260825/review-runs/manual/candidate.json

python3 scripts/harness.py compare \
  --experiment experiments/sdms-product-eval-20260825-review/experiment.json.example \
  --baseline experiments/sdms-product-eval-20260825-review/answers/baseline.json \
  --candidate experiments/sdms-product-eval-20260825-review/answers/candidate.json \
  --oracle experiments/sdms-product-eval-20260825-review/oracle.json \
  --ledger experiments/sdms-product-eval-20260825-review/adjudication-ledger.json \
  --adjudication experiments/sdms-product-eval-20260825-review/adjudication.json \
  --output .local/experiments/sdms-product-eval-20260825/review-runs/manual/comparison.json
```

Unit-тест `tests/test_review_package.py` независимо пересчитывает manifest,
47-item denominator, totals и claim/locator closure публичного пакета.

## Как выполнить человеческую проверку

Для каждого `questions[].items[]` в ledger:

1. найти тот же item в `oracle.json`;
2. прочитать полный ответ соответствующего arm, включая `facts`, `inferences`,
   `assumptions` и `unknowns`;
3. открыть перечисленные `citedLocators` в локальном frozen snapshot;
4. решить, действительно ли строки доказывают item целиком, а не только существуют;
5. отдельно проверить `dangerousClaims`;
6. зафиксировать принятие либо конкретные исправления в issue #1.

Автоматика подтверждает точные байты, структуру, наличие claim→locator покрытия,
manifest path/hash и диапазон строк answer/oracle locators, а также совпадение
totals с ledger. Она **не подтверждает
семантическую достаточность** строк и не проверяет, что свободное поле `answer`
не содержит нового существенного утверждения. Эти два решения остаются за
человеческим reviewer. Issue #1 автоматически не закрывается.

## Зафиксированные нарушения human-review процесса

Frozen ответы, oracle, ledger и adjudication не переписывались после runs. Для
этого пакета зафиксированы следующие открытые нарушения процесса:

- поле `reviewer` указывает на агентного adjudicator, а не на независимого
  человека или владельца SDMS;
- формального GitHub review PR с предметным verdict пока нет;
- семантическая достаточность `citedLocators` для всех 47 items человеком не
  подтверждена;
- свободный текст `answer` не прошёл полный human audit на существенные
  утверждения, отсутствующие среди classified claims.

Поэтому 45/47 и 44/47 — только **exact oracle coverage** frozen агентной
adjudication, не точность бизнес-ответов и не принятие human benchmark.
Технический PR может быть смержен отдельно; issue #1 и benchmark acceptance
остаются открытыми до решения владельца.
