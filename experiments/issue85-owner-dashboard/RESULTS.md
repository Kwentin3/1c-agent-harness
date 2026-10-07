# Dashboard владельца за вчера — результат #85

## Итог

**Продуктовый срез прошёл полную заявленную native-приёмку: strict oracle PASS в попытке 3.** JetTr 1.0.3.1, учебная платформа 8.5.1.1150; отдельная одноразовая ИБ. Владелец удвоил бюджет до 4 запусков суммарно, использовано 3/4. Повтор успешного запуска не нужен.

Минимальный dashboard использует существующий `Report.Dashboard`. Ровно три production path: новый report ObjectModule, существующая XML-форма и её модуль. При OnCreateAtServer и Refresh вычисляет предыдущий календарный день по времени сеанса. Production не менялся после исправления nested ALLOWED во второй попытке. Нет нового сервиса/BI/общей функции harness, metadata объектов или изменений проведения.

[Русский HTML-предпросмотр](preview.html) теперь содержит **фактические тестовые цифры** третьей попытки. Это отдельный HTML-proxy, не скриншот/экспорт из 1С. Native подписи en/tr; русская локализация в конфигурацию не добавлена. Автоматический browser screenshot предпросмотра получить не удалось: CDP браузер недоступен. Структура HTML, семь показателей и пять строк сверены тестом; интерактивную визуальную отрисовку не заявляем.

## Фактические показатели

В disposable ИБ реально проведены пять SalesInvoice на трёх днях, из них три за вчера. Fixture и независимые ожидаемые суммы — [ADMISSION.md](ADMISSION.md).

| Показатель | Native значение |
|---|---:|
| День торговли | 2026-10-01 |
| Продажи без НДС | 1010.00 |
| НДС | 202.00 |
| Продажи с НДС | 1212.00 |
| Себестоимость | 365.00 |
| Валовая прибыль | 645.00 |
| Проведённые накладные | 3 |
| Средняя накладная без НДС | 336.67 |
| Товары в полных итогах | 6 |

Полный результат: B450, A300, C80, D70, E60, F50. Итоги включают шестой товар, UI ограничивает показ пятью.

[Серверная квитанция](evidence/attempt3/run--evidence--receipt.txt.server) содержит десять `true` observations:
- `fixturePosted`: документы действительно проведены, draft не проведён;
- `calendarBounds`: вчера `[00:00:00, сегодня 00:00:00)`; соседние дни исключены;
- `rendered`: создан штатный SpreadsheetDocument;
- `topFive`: TableHeight 22, первая/пятая строки соответствуют ожидаемым B/E; полный массив данных проверен отдельно oracle;
- `negativeProfit`: предыдущий контрольный день даёт продажи20, себестоимость40, прибыль−20;
- `repeatSame`: повторный summary идентичен;
- `emptyDay`: нулевые показатели, нет товаров, табличный документ создаётся;
- `dateRollover`: явные даты 2024-03-01 и 2026-01-01 дают 29 февраля и 31 декабря;
- `defaultYesterday`: вызов без даты даёт то же календарное вчера;
- `sourceStateUnchanged`: до/после отчётных чтений одинаковое сериализованное состояние Sales, InventoryCost, InventoryInWarehouses, CustomerBalance и полей Ref/Date/Posted/Total SalesInvoice.

Последнее — сравнение наблюдаемого состояния, не физический аудит каждого возможного write. Production source дополнительно не содержит `.Write(`/привилегированного режима; scope ограничен этими report API, не всеми путями конфигурации.

[Клиентская квитанция](evidence/attempt3/run--evidence--receipt.txt) подтверждает независимый server token, завершение и `formCreated`. `GetForm("Report.Dashboard.Form.ReportForm",,,True)` выполняет production OnCreateAtServer, проверяет TableHeight22 и revenue1010 в ячейке (5,2). Это создание managed-формы, не GUI/E2E или вызов Refresh человеком.

[receipt3.json](receipt3.json) — итог существующего shared route: точные request/patch hashes, client/server bytes и SHA, business payload, oracle PASS и cleanup. [OBSERVED.json](OBSERVED.json) — производная проверенная сводка, не замена сырой квитанции.

## История без переоценки

1. Попытка1: проведены fixture документы; query engine отверг nested `SELECT ALLOWED`. Диагностика → RED regression → удалены два вложенных keyword, верхние ALLOWED и AccessRight сохранены. FAIL сохранён.
2. Попытка2: расчёт/создание формы подтверждены, но test-only `SpreadsheetDocument.Write(..., HTML)` отклонён учебной лицензией. Последующие assertions не выполнены; strict oracle FAIL. Её request/oracle/exact patches/OBSERVED теперь сохранены рядом с [историческими receipts](evidence/attempt2/). FAIL не стал PASS задним числом.
3. Владелец разрешил продолжение и удвоил лимиты. [CONTINUATION.md](CONTINUATION.md) опубликован до нового запуска. Только лишний export удалён из test instrumentation, run/nonce обновлены. **Production и oracle байтово прежние**. Попытка3 — полный PASS, без обхода лицензии. Коммерческая лицензия не нужна для этого учебного read-only dashboard.

Measured attempt3 runtime64.936s, runner total79.885s. Это измерения runner, не полное время авторства/задачи. Fresh autonomy/COST для dashboard не оценивались; этот PASS не исправляет предыдущие результаты других задач.

## Dual review: польза и границы

Первый review (`eb817f82…`) не нашёл blocking defects арифметики/query scope. DeepSeek действительно выявил stale preview: строки замены в генераторе не совпали с фактическим HTML. Замечание исправлено новым генератором и тестом отображаемых значений. Cosmetic README spacing исправлен.

Gemini переоценил доказательства: attempt2 server receipt **не** подтверждала topFive/form-generation observation после лицензионного отказа. Lead ограничил вывод в [adjudication](https://github.com/Kwentin3/1c-agent-harness/pull/86#issuecomment-5946967079). Теперь topFive действительно подтверждён попыткой3, но это новое runtime evidence, не заслуга reviewer opinion. RLS/GUI остаются unknown. Повтор predicates не повод добавлять framework. Review полезен как независимая проверка/поиск расхождений, но не как разрешение запуска, merge или замена теста.

## Ограничения и безопасность

Отчёт отражает активные движения **проведённых SalesInvoice**, в учётной валюте. Не включает все возможные отдельные возвраты/корректировки, оплаты/кассу; валовая прибыль не равна чистой прибыли бизнеса. Все цифры — искусственная fixture.

Не проверены restricted-role/RLS, equal-revenue ties, нулевая накладная, интерактивный GUI/Refresh через полночь, другие конфигурации/платформы. Production сохраняет штатный ALLOWED и явные AccessRight, не скрывает отказ прав нулями. Это не доказательство поведения RLS ограниченного пользователя.

Canonical snapshot/manifest/source не менялись: до/после одинаковые 5099 файлов и tree hash в preflight-v3/post-v3. Runner sourceBefore/sourceAfter одинаковы, cleanup completed; shared route prepared discarded. Временные IB/work copies удалены, evidence retained. Exact production delta — 3 paths; с test-only instrumentation closure — 6.

**Нет merge, rollout, restart или изменения живой базы.** PR остаётся открытым для владельца; бюджет continuation не является merge-разрешением. Это завершённый bounded product proof на одном полигоне, не универсальная BI/write-платформа.

## Воспроизведение без 1С

```sh
python3 -m unittest tests.test_owner_dashboard -v
python3 experiments/issue85-owner-dashboard/oracle.py \
  --request experiments/issue85-owner-dashboard/request.json \
  --client-receipt experiments/issue85-owner-dashboard/evidence/attempt3/run--evidence--receipt.txt \
  --server-receipt experiments/issue85-owner-dashboard/evidence/attempt3/run--evidence--receipt.txt.server
python3 -m unittest discover -s tests
```

Replay даёт PASS текущим receipts, отдельно отвергает неполный attempt2; проверяет request/token/patch/SHA/cleanup, unchanged production/oracle и preview. Mutation fixtures в unit tests — модели тестов, не fabricated external evidence.

Если отдельно нужен новый native run: admitted `one_c_open` → точный SnapshotRef → `one_c_native_verify` с task-relative текущими request/production/instrumentation/oracle и новым receipt, timeout300. Fresh request identities и новый stage обязательны; успешную квитанцию не перезаписывать. Новый run не требуется для текущей приёмки и не запускается автоматически.

[CONTRACT](CONTRACT.md) — первоначальные source locators; [ADMISSION](ADMISSION.md) — исходный pre-run audit; [CONTINUATION](CONTINUATION.md) — renewed gate; [ATTRIBUTION](ATTRIBUTION.md) — upstream notices. Readable `product/` UTF8/LF; exact patches сохраняют BOM/CRLF. Никаких heavy assets или копии harness в бизнес-проект.
