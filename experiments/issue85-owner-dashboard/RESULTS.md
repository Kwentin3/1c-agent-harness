# Dashboard владельца за вчера — результат #85

## Коротко

Реализован минимальный native dashboard на **JetTr1.0.3.1 / учебной платформе8.5.1.1150**. Использован существующий `Report.Dashboard`; не добавлены web service/BI/framework/общие функции harness. При создании формы и Refresh считает предыдущий календарный день с часовым поясом session/ИБ.

**Расчёт и создание формы фактически подтверждены. Полная приёмка не пройдена: strict oracle FAIL; issue остаётся открытой.** Не смешивать `runtime_contract_completed` с business PASS.

Патч только3 production path: новый report ObjectModule, существующая form XML, существующий form module. Два старых chart/saved-period интерфейса заменены простой read-only сводкой. Metadata report/его регистрация/права/типовая торговая логика не изменены. Native подписи en/tr; русский [preview](preview.html) — отдельно обозначенный HTML-proxy, не новая локализация конфигурации.

## Проверенный результат

В disposable ИБ **реально проведены SalesInvoice**; источники и expected fixture описаны в [ADMISSION](ADMISSION.md). Production query получил:

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

Шесть строк в порядке B450,A300,C80,D70,E60,F50. Тестовое значение общей выручки учитывает F, которого нет в UI top5. Production формирует штатный SpreadsheetDocument; client `GetForm("Report.Dashboard.Form.ReportForm",,,True)` выполнил OnCreateAtServer, получил OwnerDashboard с TableHeight22 и строкой продаж1010. Это **создание managed form**, не ручная работа/скриншот GUI.

Все цифры — искусственные продажи тестовой базы, не реальные результаты предприятия. `fixturePosted###true`, `calendarBounds###true` и actual metrics сохранены в [server receipt](evidence/attempt2/run--evidence--receipt.txt.server); binding/token и `formCreated###true` — в [client receipt](evidence/attempt2/run--evidence--receipt.txt). [OBSERVED.json](OBSERVED.json) автоматически сверяет цифры и классифицирует неполный результат; полный oracle остаётся строгим и отвергает эти receipts.

## Два запуска и ограничение

1. Run1: IB создана/конфигурация загружена, SalesInvoice проведены; nested `SELECT ALLOWED` отклонён query engine. Native diagnostic → regression RED → удалены2 nested keyword → GREEN. ALLOWED на верхнем query/отдельном invoice-count query и явный AccessRight сохранены. Старый patch SHA `5f7f3774b66fd4b61d3081d646202ef133f89afae72c3c9737081fe3cf1182d8`; canonical locators/hashes в evidence/preflight.json. Старый полный patch retained локально, не выдан за текущий.
2. Run2 с текущим production patch: расчёт совпал с независимым Decimal ожиданием, production renderer и форма созданы. Вспомогательный `SpreadsheetDocument.Write(...,HTML)` **в test instrumentation**, не production, выбросил лицензионный запрет учебной версии. После этой строки серверный probe не выполнил оставшиеся assertions. Diagnostic буквально: `Current license limitation. Print and save spreadsheet functions are not available in the training version.`

Production ничего не экспортирует/печатает/сохраняет. Коммерческая лицензия **не требуется для выбранного dashboard**; препятствие — лишний export в test probe. Export можно убрать для следующего адресного proof; никаких попыток обойти лицензионный запрет не сделано. Native2/2 использованы. Владелец не ответил на запрос разрешить третий; timeout clarification не считается одобрением. Run3 не выполнялся.

## Что пока неизвестно

Не завершены native assertions empty day, negative profit, explicit leap/year rollover, repeated reads, top-five assertion и сравнение документов/регистров **после чтения отчёта**. Поддержка видна в production исходнике, но это не runtime доказательство. Не проверены restricted role/RLS, tied revenues, нулевая накладная, Refresh через реальную полночь и интерактивная отрисовка. Нет proof переносимости на другие конфигурации/версии.

Строгое ограничение данных: отражённые активные движения **проведённых SalesInvoice**, суммы ресурсов в учётной валюте. Это не отчёт по оплатам/кассе, не чистая прибыль, не общий net sales включая возможные отдельные механизмы возвратов/корректировок. Валовая прибыль = продажи без НДС − себестоимость этих продаж, без аренды/зарплат/прочих расходов. RLS сохраняется; разрешённый пользователь может видеть лишь доступные ему данные. Не заявляется privileged бизнес-итог для ограниченного пользователя.

## Безопасность и статус поставки

Оба native result сохраняют одинаковый `preparedInvocation.sourceBefore/sourceAfter`; в обоих `storageCompaction.status=completed`. Исходный snapshot/manifest/live IB не менялись. Полный preflight применил exact production/instrumentation к канонической копии, подтвердил только6 changed paths, XML и discarded cleanup. Временные IB/work copies удалены существующим lifecycle; evidence retained. Нет deployment/restart/merge, dashboard **не установлен в живую/исходную базу**.

Код/patch/доказательства в обычной task branch/PR; issue85 остаётся открытой. Все341 tests прошли после добавления retained replay и regression/mutation checks. Это рабочий вычислительный/формовый кандидат, **не финально принятый rollout**.

## Воспроизведение

Без 1С/записи:

```sh
python3 -m unittest tests.test_owner_dashboard -v
python3 -m unittest discover -s tests
```

`tests/test_owner_dashboard.py` сверяет retained actual values/request/token/patch SHA/cleanup и отдельно доказывает, что full oracle отвергает неполную native receipt. Positive/mutation oracle fixtures в unittest — тестовые модели, не synthesized external evidence.

Native replay требует отдельно разрешённого бюджета. На admitted route `one_c_open` → exact returned SnapshotRef → `one_c_native_verify(snapshotRef, request, productionPatch, instrumentationPatch, oracle, receipt, timeoutSeconds=300)`. Использовать отдельные task-relative файлы/новый receipt. **Перед replay убрать вспомогательный HTML Write из test instrumentation, сохранить numeric/renderer/form assertions, nonce и все строгие checks; повторно preflight полный patch closure.** Не менять production для обхода учебных ограничений. Текущий exact-instrumentation.patch честно соответствует run2 и воспроизводит лицензионный отказ, а не PASS.

[CONTRACT.md](CONTRACT.md) — первоначальная семантика/source evidence; [ADMISSION.md](ADMISSION.md) — pre-run audit; [evidence/help-locators.json](evidence/help-locators.json) — exact runtime help members/hashes. [ATTRIBUTION.md](ATTRIBUTION.md) — условия upstream входа, не выбор лицензии harness.
