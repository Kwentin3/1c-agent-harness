# #85 — admission перед первым native-запуском

## Выбранное решение

Использован существующий `Report.Dashboard` (его metadata, регистрация, роли и путь открытия сохраняются). Три production path: новый object module и замена существующих form XML/module. Вчера — календарный день относительно `CurrentSessionDate()` ИБ; Refresh пересчитывает дату, сохранённые периоды не используются. Данные read-only, `SELECT ALLOWED`, явная проверка Read, без privileged mode. RLS сохраняется: владелец должен иметь нужные права; ограниченный пользователь может видеть только разрешённые данные.

Native output — штатный `SpreadsheetDocument`, не внешний веб-сервис. Русский HTML preview — structural proxy; native подписи en/tr соответствуют языкам данной конфигурации. Никакие upstream библиотеки/полная конфигурация не копируются в продукт harness; task patch сохраняет атрибуцию входа.

## Фактическая fixture / независимые ожидания

В disposable ИБ создаются 6 товаров с unit cost40,60,30,20,10,5; остатки задаются прямыми record sets (технический seed, не proof штатного поступления). Затем вызывается реальный `SalesInvoice.Write(DocumentWriteMode.Posting)`:

- вчера00:00: A100 + A100 + B300, VAT100; cost200;
- вчера12:00: B150 + C80 + D70 + E60 + F50, VAT82; cost125;
- вчера23:59:59: A100, VAT20; cost40;
- позавчера23:59:59 и сегодня00:00 — контрольные продажи, должны быть исключены;
- draft с вручную seeded sales777 — негативный контроль Posted (не штатное приложение);
- writeoff cost999 в другом складе — контроль исключения не-продажных расходов.

Ожидания вычислены отдельно Decimal: net1010, VAT202, gross1212, cost365, grossProfit645, count3, avg336.67. Все6 продуктов суммируются, top5 B450,A300,C80,D70,E60; F50 не должен отображаться. Дополнительно пустой день, отрицательная прибыль20−40=−20, високосный/новогодний переход дат, undefined date default и повторное чтение. До/после production API/render fingerprint реальных документов и4 регистров совпадает. Client `GetForm` создаёт production form через OnCreateAtServer; проверяет OwnerDashboard row5 net1010 и TableHeight22. Это не ручное GUI/E2E.

## Whole-probe callable audit

Runtime8.5.1.1150, первичный `shcntx_root.hbk` SHA256 `91b8233b4052e8b63aad618333d4c84afa4e9f810b5092075bb243c2e1504e9f`. CRC/size/member SHA проверены retained reader; locators в `.local/owner-dashboard/help{,-additional}.json`.

- `CurrentSessionDate4022`, `BegOfDay950`, `Round930`, `Format971`, `ValueToStringInternal46`, `AccessRight693`, `GetForm3526`: aliases/args/слои проверены. CurrentSessionDate учитывает timezone session/ИБ/server; GetForm только клиент, выполняет server call.
- `ReportManager.Create831`, `Query.ExecuteBatch3663`, `SpreadsheetDocument.Area86/Write72`, `SpreadsheetDocumentRange.Text411/ColumnWidth425`, HTML286, TableHeight376/TableWidth375, Structure.Insert728, Array ctor: проверены на том же runtime.
- Catalog/CreateItem/Write, Document/CreateDocument/Write/GetObject, recordsets/CreateRecordSet/Filter.Recorder.Set/Add/Write, Query/SetParameter/Execute/Unload/Select/Next, TextWriter2args/Write/Close, UUID/String/Date/Array.Add и ErrorDescription964: предыдущий exact-runtime help audit и успешный #69 на этой же версии; поля текущих metadata прочитаны, не выдуманы. ErrorDescription только отдельный diagnostic file, не receipt grammar.
- `FormAttributeToValue` — существующий путь Dashboard form `Module.bsl:67`; native entry проверит новый тот же form/server seam. NStr и Chars.LF — уже существующая конфигурация/успешная проба.
- Только один rendered OnStart, ранний вызов before preserved normal startup, balanced Procedure/Function, single terminal complete row, полный changed path closure3+3. Dynamic Execute/Eval не добавлены.

Перед запуском существующий `managed_probe_prepare` должен применить оба exact patches к полной disposable canonical копии, подтвердить6 changed paths/XML и discarded cleanup. Source-only шаг не расходует native budget. Создан readable preview до запуска; автоматический screenshot QA недоступен (automation Chrome не запущен); это ограничение не скрывается.

## Неизвестное

Полный runtime запрос/обработка формы пока не выполнены. Не доказаны интерактивное GUI, restricted-role/RLS case, ties/нулевая накладная и переход Refresh через реальную полночь (поддержаны исходным кодом, не выданы за runtime proof). Ориентир native2: первый содержательный проход, второй только адресное исправление. Live DB/source immutable; нет deployment/restart/merge.

READY FOR NATIVE
