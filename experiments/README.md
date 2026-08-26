# Experiment templates

Скопируйте `experiment.json.example`, `questions.json.example`,
`oracle.json.example`, `adjudication-ledger.json.example` и
`adjudication.json.example` в новый `.local/experiments/<id>/`, замените
значения и вычислите SHA-256. Example-файлы намеренно содержат placeholders и
не являются готовым экспериментом.

`sdms-product-eval-20260825-review/` — готовый публичный review package для
человеческой проверки 47 frozen items. Для повторного `compare` ему нужен
локальный snapshot с указанным content ID.

`issue12-narrow-context-20260826/` — закрытый по manifest review package сравнения
обычного direct-source поиска с bounded context-frontier protocol на SDMS и Jet;
содержит frozen arm packets, независимую adjudication, нативные receipts и
fail-closed decision без добавления нового runtime-компонента.

Исполняемый порядок описан в [`docs/experiment-runbook.md`](../docs/experiment-runbook.md).
