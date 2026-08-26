# Experiment templates

Скопируйте `experiment.json.example`, `questions.json.example`,
`oracle.json.example`, `adjudication-ledger.json.example` и
`adjudication.json.example` в новый `.local/experiments/<id>/`, замените
значения и вычислите SHA-256. Example-файлы намеренно содержат placeholders и
не являются готовым экспериментом.

`sdms-product-eval-20260825-review/` — готовый публичный review package для
человеческой проверки 47 frozen items. Для повторного `compare` ему нужен
локальный snapshot с указанным content ID.

Исполняемый порядок описан в [`docs/experiment-runbook.md`](../docs/experiment-runbook.md).
