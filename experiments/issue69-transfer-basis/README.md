# InventoryTransfer: основание перемещения — bounded continuation

Необязательный unlimited String `TransferBasis`, `DontCheck`, `en=Transfer basis`, `tr=Transfer gerekçesi`; `Object.TransferBasis` после WarehouseReceiver в GroupHeader/GroupLeft. Два production XML-файла; BSL проведения неизменен. Новый язык не добавлен.

## Контекст и наблюдения

- Snapshot JetTr1.0.3.1: contentId70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691,5099 файлов. Document metadata `InventoryTransfer.xml`:210 основная форма,222–223 InventoryInWarehouses/InventoryCost,337–383 прецедент Comment unlimited/DontCheck.
- `InventoryTransfer/Ext/ObjectModule.bsl`:11–34 реальный Posting: InitializeDocumentData → PrepareRecordSets → ReflectInventoryInWarehouses/InventoryCost → WriteRecordSets → NegativeBalanceControl. Production этих модулей не изменяет.
- `InventoryTransfer/Ext/ManagerModule.bsl`:12–22 lock InventoryCost;72–135 calculation Amount based on actual balances. `InventoryInWarehouses/Ext/ManagerModule.bsl`:12–61 отрицательный остаток вызывает Common.MessageToUser с Cancel.
- Фикстура в disposable ИБ: новые два склада, продукт, draft-регистратор; record sets дают source100 единиц/1000 стоимости. Это технический seed реальных регистров, не proof штатного поступления.
- Пустой новый документ4 единицы → Write/read → emptyDraft; Posting/read → emptyPosted. Два реальных recorder-scoped ряда в каждом регистре, Quantity4/Amount40, product и source/target проверяются.
- Новый draft с длинным Unicode текстом и независимым Comment → Write/read → точное сохранение обоих; ранее проведённый документ → записать этот текст + Posting/read → точное сохранение, Posted=true. Сравниваются все поля всех recorder rows до/после в обоих регистрах.
- Новый draft1000 единиц с текстом → сохранить, затем Posting → должен быть отклонён; повторное чтение unposted/text preserved, recorder rows0 в обоих регистрах. Это runtime rollback observation, не вывод только по позднему Cancel.

Неверные варианты: только поле формы (нет persisted attribute), обязательность/placeholder (пустой save/post провалится), использование Comment (проверка независимости), вмешательство в проведение (row equality/expected values), удаление shortage prohibition (negative case).

## Допуск

Production patch retained SHA256 f1ddfef9d220d723d1279b82313b65328339f70ea05cb6651ee9498b041ce42f без изменения. Оба патча реально применены в отдельной partial work copy и реконструировали кандидат побайтно. Instrumentation: только ManagedApplicationModule, PostingManagement metadata(ServerCall=true) и module. Один OnStart, balanced procedures/functions, ранний Return до штатного startup. Whole added-callable list сохранён в stage-read; API checked against installed8.5.1.1150 shcntx_root91b8233b4052e8b63aad618333d4c84afa4e9f810b5092075bb243c2e1504e9f и ru b8bc0d3a1ee8d00e2f113a800339731304428cc35ae395e5094a8b022773f8ed. TextWriter2args/Write/Close, UUID/String/Date, Array.Add, Catalog.CreateItem/Write, Document.CreateDocument/Write/Ref.GetObject, register.CreateRecordSet/Filter.Recorder.Set/Add/Write, Query/SetParameter/Execute/Unload, ValueTable.Count/columns подтвердили сигнатуры. Непроверенные ErrorDescription/StrSplit/IsBlankString не используются. Append не используется. Query.Execute — разрешённый запрос, не dynamic Execute.

Oracle принимает только точный свежий run/nonce, совпадающий server-generated token, отличающийся от nonce, полный набор13 true boolean observations и complete markers. 57 синтетических отрицательных мутаций отвергаются; они не native evidence.

Штатный installed one_c_native_verify → unchanged shared_task_route → native_cycle; путь SnapshotRef, request/patch/oracle/receipt внутри business .local. Runtime child import проверен без1С; actual Python3.12.3. Бюджет Goal всего2 native, сейчас0; второй только адресная коррекция. CF не нужен для prepared snapshot load, immutable canonical assets не правятся. Никакого самостоятельного runner или новой receipt grammar.

Неизвестно до запуска: платформа примет весь rendered BSL, сохранение и движения. Интерактивная отрисовка формы/полный штатный startup/production deployment не заявляются. Static preview — proxy. READY FOR NATIVE относится только к согласованному bounded эксперименту, не runtime PASS.

READY FOR NATIVE

## Стоимость и автономность

Это NON-FRESH continuation. Первоначальный600s executor timeout и1057.98s checkpoint сохранены; clock не сброшен. Время текущего ожидания пользователя не выдаётся за active compute. Fresh end-to-end autonomy и исходный600s ориентир не достигнуты. Один фиксированный remote business project; automatic WebUI workspace selection отложен владельцем. Issue69 не закрывается как полная исходная цель на основании этого узкого доказательства.
