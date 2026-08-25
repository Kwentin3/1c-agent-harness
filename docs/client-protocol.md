# Client-neutral protocol

Harness фиксирует контракт исследования, а не API конкретного агента.

## Общий вход

Каждому клиенту передаются:

1. абсолютный read-only snapshot root;
2. snapshot content ID и manifest;
3. один и тот же frozen question set и его SHA-256;
4. `contracts/answer.schema.json`;
5. одинаковые правила доказательности.

Клиент не должен читать oracle, ответы другого arm или прошлые transcripts. Запись разрешена только в отдельный новый output root; cache — только в объявленный `.local` cache root.

## Общий выход

Ответ содержит:

- `facts`: прямо подтверждённые факты;
- `inferences`: выводы из нескольких фактов;
- `assumptions`: явно обозначенные предположения;
- `unknowns`: то, чего snapshot не доказывает;
- `locators`: относительный путь и строки, связанные с claim IDs;
- фактические client/model/tool versions и метрики.

Имя объекта, текстовый match или результат индекса сами по себе не доказывают назначение, runtime-состояние или call graph.

## Client-specific слой

Различия допускаются только в тонких launch instructions:

- способ запуска и envelope stdout;
- sandbox/read-only permissions;
- выбор реально доступной модели;
- объявленная версия клиента.

Нельзя вводить общий SDK, plugin framework или скрывать различия context budget/model. `scripts/harness.py` намеренно не запускает клиентов.

Готовность клиента фиксируется по уровням: documented, installed,
authenticated, canary-proven и arm-proven. Canary моста не доказывает, что его
runner видит локальный snapshot; гарантией переносимости считается только
завершённый arm с проверенным answer artifact.

## Candidate tools

- `cf-index`: build once на content ID, затем reuse; свойства объекта подтверждаются исходным XML.
- `ast-index`: только optional prefilter. Miss не доказывает отсутствие; `outline`, `symbol` и `usages` перепроверяются anchored search/чтением BSL. Cache направляется через `XDG_CACHE_HOME` в `.local/`.

## Human adjudication

Reviewer получает frozen questions, oracle и оба обезличенных ответа после завершения runs. Он оценивает факты и dangerous false claims. Автоматический locator validator не является human oracle.
