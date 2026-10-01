# Native result — bounded PASS, original autonomy/cost not passed

2026-10-01, installed registered `one_c_native_verify`, JetTr1.0.3.1 snapshot, separate ordinary business root `/workspace/1c-agent-harness/.local/goal69-business` (no harness source copied there). **Native invocations1/2; no retry.** Production patch is unchanged from the static candidate. No companion/core/runner changes. Deployment import fix is separately tracked in PR83.

## Results and primary evidence

| Observation | Native observation |
|---|---|
| Empty draft save/read | true |
| Empty post/read | true |
| Stock / cost recorder rows | 2 / 2 |
| Stock / cost values | Quantity4; Amount40; fixture product and source/target |
| Long Unicode basis + independent Comment, draft save/read | both preserved |
| Same basis + independent Comment, posted/repost/read | both preserved; Posted=true |
| Stock / cost movements before/after basis change | all columns/rows equal |
| Shortage transfer post attempt | rejected, object remains unposted with saved basis |
| Rejected recorder stock / cost rows | 0 / 0 |

These are real runtime assertions, not synthetic oracle fixtures. `server-receipt.txt` contains13 named true observations; `client-receipt.txt` proves the server call returned with matching fresh token. Request runId/nonce match on both sides; server-generated token is different from nonce. `oracle.py` reproduces PASS from these bytes. Seed is deliberately direct record-set setup in a disposable database, not proof of a normal receipt-document workflow.

Primary receipt `receipt1.json` SHA256 **f0e00ea86ce16b3dff292f1852774e69f1bb1054aec5b1156e99a9533950eac6**. Production patch SHA256 f1ddfef9d220d723d1279b82313b65328339f70ea05cb6651ee9498b041ce42f. Instrumentation SHA256 9639f0f21fbe3a97f90b7ecefe37f41e78212c18ba6d95cfe403ed3447eb285d. Raw client SHA25678499080934888b75e2862e7c30712250c3a8a01579ce434bd19ed9364974b1b; raw server hash is bound inside the canonical receipt and checked by replay tests.

Canonical before/after identity5099 files/a7c4275cb37bef5bbad3d8e668328ad104389b6897b20f5c5d419a05958000db is checked by unchanged shared-task route, which produces PASS only after this equality. Reopen retained the same admitted SnapshotRef/contentId70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691. Prepared input7e70fe01c09dfff747f3939188876f680f163bec5c59ef4f143c38bdc5b4650c equals copied/frozen input and inputAfter. These different identity algorithms must not be equated. Loaded work-copy hash changed79de18…: platform loading may modify only the disposable work tree, not the immutable input.

## Duration, lifecycle and safety

`native-result.json`: cycle69.216s; total81.334s; create/load process0 and DumpResult0. Runtime ends with expected runner SIGTERM (`processReturn=-15`) after complete marker and two stable receipt reads, not with a claimed process0 exit. Domain result comes from the strict oracle, not process success. Runtime run.result was absent at controlled termination; complete receipt is the canonical mechanism.

Standard `compact-current-invocation-v1` cleanup completed in3.115s, removed224552387 logical bytes; frozen-input, work-copy, disposable ib/home/tmp removed. No manual cleanup. Retained spec/evidence/logs/result remain at `.local/runs/native-cycle/run-qtk9h2n9`. `post-run-check.json` confirms no 1cv8t/1cv8ct/Xvfb processes and no children under business `.local/prepared`. Task-owned preparation/evidence in `.local/inventory-transfer-basis` is retained intentionally. No original target or live database was the command target.

## Reproduction

1. Admit same JetTr snapshot and8.5.1.1150 runtime in an ordinary separate project via standard deployment binding. Fixed deployment source PR83 requires Python3.11+ to preserve safe-path child import. Keep credentials in the existing deployment secret source, not in this experiment.
2. Production patch then instrumentation patch must actually apply to a physically separate work tree and reconstruct the rendered candidate. Check canonical source read-only. Render a fresh runId/nonce into both patched BSL and request; do not rerun historical bytes to claim freshness. Retained request is for replay only.
3. Copy request, patches and oracle under admitted project `.local/` and call registered `one_c_native_verify(snapshotRef, request, productionPatch, instrumentationPatch, oracle, receipt, timeoutSeconds=300)`. Do not execute1С through a custom runner. Fresh runs require separate explicit budget; the second slot in this completed experiment remains unused and is not a standing authorization.
4. From a clean repository checkout, replay without1С:

```sh
python3 experiments/issue69-transfer-basis/oracle.py \
  --request experiments/issue69-transfer-basis/request.json \
  --client-receipt experiments/issue69-transfer-basis/client-receipt.txt \
  --server-receipt experiments/issue69-transfer-basis/server-receipt.txt
python3 -m unittest tests.test_issue69_evidence -v
```

## What is not achieved

- Fresh executor first-pass autonomy: original600s timeout persists; original1057.98s checkpoint was already beyond budget. This continuation does not reset cost. Native81.334s is a separate measured cycle duration, not the total agent effort.
- Automatic WebUI workspace selection/admission: explicitly deferred; one deployment-bound remote project was used.
- Interactive native form rendering and full ordinary application startup: only XML binding/position plus successful configuration load is proved; OnStart has task-local early Return. The visible HTML was a labeled structural proxy.
- General write support or production rollout: no such inference is made.

## Завершение этапа на имеющемся полигоне

Владелец изменил финиш текущего этапа: завершить и принять #83/#84 на единственной
доступной тестовой конфигурации, затем остановиться. Другая конфигурация, fresh autonomy
и автоматический выбор WebUI workspace не являются блокерами этого ограниченного финиша.
Исходные результаты не переквалифицированы: **PRODUCT PASS в проверенной границе,
ROUTE COST FAIL; fresh end-to-end autonomy не доказана**.

- #83 принят в `main`: merge `68918fe73c3bea80684857322c3d36ac722075ad`;
  tree совпал с проверенным head, post-merge CI Python 3.9/3.12 PASS.
- Production-патч и исходные client/server квитанции сохранены побайтно, без повторного native.
  Final static reconstruction на retained original files подтверждает: ровно два XML-файла,
  необязательная строка с пустым default, существующие en/tr-представления,
  `Object.TransferBasis` после `WarehouseReceiver`, уникальные ID элементов управления,
  неизменность всех прежних элементов XML и ноль production BSL-изменений.
  Это проверка сохранённых исходных байтов, не новая live-проверка или GUI-отрисовка.
- Слияние #83 в ветку #84 не меняет конфигурацию, native request, instrumentation или oracle.
  Replay доступен из чистого checkout командами выше; полный suite и exact-head CI
  проверяются на финальной объединённой ревизии, затем отдельно на merge-коммите `main`.
- Текущий домашний executor недоступен: registered `one_c_open` вернул `terminal_failed`,
  прямой запуск того же установленного wrapper — SSH `No route to host`.
  Установленный wrapper совпадает с принятой source-реализацией с двумя ранее разрешёнными
  deployment-подстановками (business cwd и pinned known_hosts). Новая запись, restart,
  fallback или попытка 1С не выполнялись. Исторический runtime PASS не означает текущую
  доступность подключения.

Пользователь получил сопровождаемый точный патч функции и установленный маршрут одного
допущенного бизнес-проекта. Исходная конфигурация и живая ИБ не изменены; это не rollout.
После принятия #84 ограниченный этап #69 закрывается с этой явно изменённой границей,
а не как успешный первоначальный тест свежей автономности. Новое испытание не запускается.
