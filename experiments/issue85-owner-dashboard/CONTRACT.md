# Owner-yesterday dashboard: source-only semantic preflight

> Это исторический pre-run contract. Актуальный итог: третья native-попытка прошла полный strict oracle PASS при неизменном production/oracle, после удаления лишнего test-only HTML export. Бюджет продлён владельцем до 4 суммарно, использовано 3. Результат, hashes и limits — [RESULTS.md](RESULTS.md), [OBSERVED.json](OBSERVED.json), [CONTINUATION.md](CONTINUATION.md). Исходные попытки 1/2 остаются FAIL; merge/rollout не выполнялись.

## Change and API
Replace the existing saved-period/two-chart form of `Report.Dashboard` with a read-only native spreadsheet, computed at server creation and each Refresh. No new metadata objects, shared dependencies or writes.

`GetYesterdaySummary(AsOfDate = Undefined) Export` returns Structure:
`StartDate, EndDateExclusive, Revenue, VAT, GrossSales, Cost, GrossProfit, InvoiceCount, AverageTicket, Products`.
`Products` is a ValueTable of ALL products with `Product, Revenue, VAT, Cost, GrossProfit`, ordered Revenue DESC, then Product.Code/ref. Only rendering truncates to five. `RenderYesterdayDashboard(Summary) Export` returns SpreadsheetDocument. Form attribute: `OwnerDashboard`.

Undefined date → `CurrentSessionDate()` → `BegOfDay` → exclusive end; start=end−86400. Explicit date takes the same normalization. No saved period, work-date setting or machine clock is consulted. Invoice count is distinct active Sales recorders whose recorder is posted SalesInvoice; zero-value sales still count. Average net ticket = Round(Revenue/InvoiceCount,2), or zero when count=0.

## Source context (canonical snapshot-relative locators)
- `Reports/Dashboard.xml:15-30,41-44`: report and default form already registered; retain metadata/schema unchanged.
- `Reports/Dashboard/Forms/ReportForm/Ext/Form.xml:22-35,138-143,557-583`: existing Refresh command, event and Report main attribute. Preserve Report identity and Refresh; replace chart/period content.
- `Reports/Dashboard/Forms/ReportForm/Ext/Form/Module.bsl:64-84,96-129`: current composition/chart route gets Report through FormAttributeToValue and uses saved ItmPeriod. New form server path must call the report object API instead, not duplicate query logic.
- `Reports/ProfitOnSales/Templates/MainDataCompositionSchema/Ext/Template.xml:175-217`: cost Expense for SalesInvoice unioned with sales Amount, not joined; gross profit revenue minus cost.
- `Documents/SalesInvoice/Ext/ManagerModule.bsl:41-55,137-152,218-240`: document amount and VAT are separately converted by exchange rate/multiplier; Sales is aggregated by product/document; InventoryCost uses Expense records. Sum stored register resources, not document Total or currencies.
- `Documents/SalesInvoice/Ext/ObjectModule.bsl:14-54,58-71`: actual posting reflects/writes Sales and InventoryCost; undo-posting also prepares/writes recordsets. These adjacent writers are not modified.
- `AccumulationRegisters/Sales.xml:49-75,103-156,210-260`: raw Active/Recorder/Period and two-decimal Amount resource. VATAmount is the separate register resource.
- Read-only SSH source precedents: `CommonModules/Common/Ext/Module.bsl:169-175,937-939,2521-2527` uses AccessRight("Read",metadata), CurrentSessionDate and BegOfDay; `CommonForms/EditSpreadsheetDocument/Ext/Form.xml:2123-2152,2636-2638` uses native `SpreadSheetDocumentField`, Edit, spreadsheet namespace/type; `Catalogs/Products.xml:47-54` has unique string code. These were read remotely, not copied into immutable local source.

## Scope, preserved behavior and wrong implementations
Read only raw Sales and InventoryCost, explicit Period >= start AND Period < end, Active, recorder type SalesInvoice and Recorder.Posted; InventoryCost additionally RecordType=Expense. SELECT ALLOWED, ordinary object-level read-right checks, no privileged mode. Permission/query failures propagate; do not substitute zero. Row-level access restrictions remain enforced and can make an allowed view partial; do not promise a privileged full-business total.

Preserve posting, stock validation, register writes, rates/tax conversion, existing report/default-form identity, English/Turkish localization. Direct report-object API also applies the same predicates; bypassing the UI cannot change period semantics. It does not modify or validate posting/integration writers.

Plausible wrong versions: (1) rolling 24 hours or saved month; (2) raw Sales×Cost join multiplying lines; (3) all inventory expenses including write-off/transfer or receipts; (4) invoice/header Total counted instead of active movements/net Amount; (5) top-five total instead of all-product total; (6) permission denial swallowed as an empty day.

## Distinguishing cases (pre-state → action → expected business state)
- Session date D at 15:00, records D−2 23:59:59, D−1 00:00, D−1 23:59:59 and D 00:00 → open/default API → only the two D−1 records included, exactly calendar yesterday. Refresh after midnight advances day even if a prior month was saved.
- Multiple same-product invoice lines plus multiple cost records; net amounts 100+50, VAT 20+10, costs 40+20 → API → Revenue150 VAT30 GrossSales180 Cost60 GrossProfit90, one invoice, average150; no join multiplication.
- Posted purchase receipt, write-off and transfer in interval alongside invoice expenses → API → only invoice Expense cost included; unrelated stock movements untouched.
- Draft without movements, inactive movement and non-posted recorder with retained raw records → API → neither totals nor invoice count includes them.
- Two active invoices, net100 and net0 → API → InvoiceCount2, AverageTicket50; counting nonzero net revenue is wrong.
- Six or more products incl equal revenues → API/render → all products in ordered ValueTable and totals, exactly first five displayed; ties by Code/ref; profit rows = Revenue−Cost.
- No active posted Sales or invoice cost records → API/render → all numeric zeros, empty Products, explicit localized no-sales message, no division by zero.
- Denied Read on Sales/InventoryCost/SalesInvoice/Products → API → explicit error, never a successful zero/empty dashboard; no privilege elevation.
- Identical unchanged register/document state → repeated default API/render → same numbers and no persistence. Static no-write constraint: production code contains only read query execution, in-memory structures/tables and spreadsheet/form attribute assignment; no Write/Post/transaction/background/file/privilege calls. Later native lane must independently fingerprint documents and movements.

## Unknowns and admission
Native attempts=0. Static sources support this implementation candidate, not successful compile/import, data execution or UI display. Exact target runtime admission still required for ExecuteBatch with nested union/group/order, raw Recorder.Posted polymorphic dereference, spreadsheet Area(row,col).Text/ColumnWidth, Format/zero display and Round alias, report object method availability, OnCreateAtServer and spreadsheet attribute binding. Read-only source precedents are not an exact-version API receipt. Interactive UI/permissions/RLS behavior remains untested. Lead owns API admission and any separately authorized native work.

## Static patch proof (after implementation; not native acceptance)
`git diff --no-index --no-ext-diff base tree` produced the exact binary-preserved patch; only known base/tree prefixes were normalized. Both `git apply --no-index --check` and actual `git apply --no-index` returned 0 in a separate copy with `GIT_CEILING_DIRECTORIES` set to its parent. Applied bytes equal candidate bytes, with exactly these changes:
- `Reports/Dashboard/Ext/ObjectModule.bsl` (new)
- `Reports/Dashboard/Forms/ReportForm/Ext/Form.xml`
- `Reports/Dashboard/Forms/ReportForm/Ext/Form/Module.bsl`

Patch SHA-256: `5f7f3774b66fd4b61d3081d646202ef133f89afae72c3c9737081fe3cf1182d8`.
Raw static receipt: `.local/owner-dashboard/candidate/static-apply-proof.json`. It retains commands, exits, encoding flags, changed paths and post-apply hashes. Original source hashes were unchanged across build/application. BOM/CRLF retained for patch inputs; readable product sources are plain UTF-8/LF. Git's apply emits CRLF trailing-whitespace warnings but no application failure; no whitespace-fixing transformation was used.

Исторический source-only admission не является текущим verdict. Lead принял API audit, исправил nested ALLOWED по native diagnostic; третья попытка прошла strict oracle (RESULTS.md). Статический hash выше относится к первоначальному кандидату, не текущему production patch.
