# Результат Antigravity arm

## Контракт и воспроизводимость

Antigravity был проверен на том же frozen эксперименте, что и Hermes arms:

- experiment: `sdms-product-eval-20260825`;
- snapshot content ID: `sha256:3357ee63204ff863aac116417927240930084dce0eb7613126ad88cff68a424d`;
- question set SHA-256: `3eba62e70085d74f954968832f5c5d9ab06db0c0da44e83af6bf22651fcbcd90`;
- AgentBridge Antigravity CLI: `1.1.15`;
- итоговый answer SHA-256: `94e7f3b1c5497156dbb4801c3d61c7ad5f2e93cbd0ef8576242201039d220fbc`.

Runner получил отдельный read-only bundle снимка. Oracle, ответы других arms и их
transcripts клиенту не передавались. Один frozen question выполнялся одной
ограниченной research task. Семь принятых units потребовали восемь attempts: Q4
один раз завершился `result_schema_invalid` и был повторён по заранее
зафиксированной retry policy.

Каждый native task record был преобразован строгим representation adapter без
семантического repair. Harness отдельно проверил каждый unit, собрал полный ответ
в frozen question order и повторно проверил итог. Результат: 7/7 вопросов,
27 существующих locators, правильные content/question IDs. Повторная сборка из
units, client descriptor и metrics дала побайтово тот же answer SHA-256. Post-run
preflight подтвердил прежние 2581 файла snapshot и тот же content ID.

Локальные task records, raw answers, oracle и snapshot остаются в `.local/` и не
публикуются в Git.

## Общая оценка

Независимый adjudicator применил тот же frozen 47-item oracle, что использовался
для baseline и indexed candidate.

| Arm | Oracle alignment | Dangerous false claims | Наблюдаемое время |
|---|---:|---:|---:|
| Hermes direct source | 45/47 (95,74%) | 0 | 154 с |
| Hermes indexes + source fallback | 44/47 (93,62%) | 0 | 204 с |
| AgentBridge Antigravity | 31/47 (65,96%) | 0 | 1364 с |

Разбивка Antigravity:

| Вопрос | Зачтено |
|---|---:|
| Q1 — паспорт | 6/6 |
| Q2 — назначение и масштаб | 8/9 |
| Q3 — цепочка создания задачи | 5/9 |
| Q4 — движения трудозатрат | 4/6 |
| Q5 — регламентный механизм и мессенджеры | 3/5 |
| Q6 — Bearer/JWT | 4/6 |
| Q7 — существенные unknowns | 1/6 |

Antigravity сохранил безопасную границу: опасная ложная декларация о доказанной
криптографической проверке JWT не появилась, а runtime-состояние в основном не
выдавалось за факт. Основная потеря качества — неполные составные ответы: были
опущены части статической цепочки Q3, детали движений Q4, срок и обновление даты
использования в Q6 и большинство заранее зарегистрированных категорий Q7.

Есть и ограничение oracle: Q5 требует конкретный пример
`ПересчитатьОчередьЗадач`, тогда как Antigravity выбрал другой реально
существующий механизм `ОбновитьIDПользователейМессенджера`. По строгому frozen
scoring этот item не засчитан; менять oracle после run нельзя.

## Вывод

Архитектурная граница подтверждена частично и проверяемо:

- второй клиент прочитал тот же snapshot и вопросы;
- snapshot contract и правила locators не стали client-specific;
- различия ограничены read-only transport, инструкцией клиента и тонким adapter;
- общий harness принял и проверил итоговый артефакт;
- универсальный SDK или абстракция третьего клиента не созданы.

При этом Antigravity arm не прошёл общий порог
`minimumFactAccuracy = 0.9`: для 47 items нужно не менее 43, получено 31. Поэтому
`arm-proven` здесь означает доказанный полный технический прогон, а не
эквивалентное качество модели. Issue #4 нельзя закрывать только на основании
этого run.

Для воспроизведения требуется внешняя предпосылка: авторизованный AgentBridge
Antigravity runner с read-only монтированием того же bundle. Следующий минимальный
эксперимент — повторить заранее неизменный unit protocol с более явными
per-question completeness requirements либо другим реально доступным клиентом,
не меняя oracle после запуска.
