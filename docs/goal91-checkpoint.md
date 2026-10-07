# Goal #91 — bounded native/web PASS, owner review

Проверка 2026-10-07. **Согласованный fresh цикл выполнен; demo восстановлена.**
Контракт: [#91](https://github.com/Kwentin3/1c-agent-harness/issues/91).
Следующие направления: [#92](https://github.com/Kwentin3/1c-agent-harness/issues/92).

## Текущий результат

[Финальный Git-tracked отчёт](goal91-final.md): installed source
`eaab4cf3b6c563e11388f02676acb54f0302d004`, artifact
`sha256:415782d4419b82987e51f8539f0030cbcd3b3c5f3ae483541a1481bf25aa0ef9`.
Свежая ordinary Hermes session: cold materialized → warm reused → три registered
narrow searches → один substantive native verify, strict oracle/replay PASS,
13 observations true, 6/6 platform launches, no retry. Snapshot/CF/manifest/runtime
и demo IB после native неизменны. Cleanup/revoke/exact stop/PID0/oldPID absent,
прежние service/route восстановлены; owner login/dashboard/Refresh/confirmed Exit PASS.
Окно закрыто досрочно, purpose key отозван, все timers inactive.

Skills raw parity и local terminal/GitHub PASS. ТЖ registered retained discovery/
selection/expansion PASS, не fresh telemetry. ЖР current fail-closed validation и
expired-ref checks PASS без exporter; positive #80 evidence историческое, current
valid selection/page/record NOT_RUN. Acquisition #90 и nonzero web #92 не добавлены.
PR #86/#88 готовы к owner review в этих явно описанных пределах; merge не разрешён.

## История: первый cold failed и подготовка source repair

[Следующий coding admission и точные оставшиеся gates](goal91-coding-admission.md).
Постоянная web-доставка завершена оператором в #89; Hermes отдельно проверил401
без credentials. Кандидат `7b5ad3b756d07a7331d941b9376d01211532db7f` был установлен
с проверкой plugin/companion/launcher и обычного непривилегированного доступа.
Первый registered cold `one_c_open` 7 октября вернул `materialization_failed`;
warm/narrow/verify не выполнялись. Окно закрыто досрочно, purpose key отозван,
demo восстановлена; вход/Refresh/штатный выход подтверждены на
<https://1c-demo.speechbattle.com/jetcontrol/ru/>.
[Cold failure, cleanup и evidence](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6031464734).

Source repair устраняет воспроизведённый без 1С дефект сбора zombie/отделившихся
потомков через существующий owner `native_cycle`; локально356 tests PASS.
Plugin/companion artifact кандидата:
`sha256:415782d4419b82987e51f8539f0030cbcd3b3c5f3ae483541a1481bf25aa0ef9`.
На этом checkpoint исправление ещё не было установлено; последующая установка
и native acceptance описаны в текущем итоге выше.
При прежнем полном unit-прогоне внутри reference оператор допустил ошибку
изоляции: fixture обнаружил реальный runtime и дошёл до CREATE/load_failed.
[Инцидент, отсутствие survivors и исправление fixture](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6031716774).
Последующий полный regression выполнен вне reference без платформы/runtime.

Nonzero web-сценарий
перенесён владельцем в #92 и больше не блокирует Goal91. Canonical/installed
три skill-пакета сверены побайтно, ценные installed дополнения сохранены в Git.
Старые статусы ниже — история соответствующих проверок, не текущее состояние demo.

## История: ordinary Hermes web PASS, экземпляр остановлен после smoke

В новом [двухчасовом окне](https://github.com/Kwentin3/1c-agent-harness/issues/89#issuecomment-6014916362)
после [operator READY](https://github.com/Kwentin3/1c-agent-harness/issues/89#issuecomment-6014982614)
Hermes выполнил **один** fresh browser smoke своим strict pinned SSH, UID10001,
с существующим `FONTCONFIG_FILE`. Длительность24.808s. Настоящий iframe до/после
штатного `#form0_FormRefresh`: trading date2026-10-05, семь нулей, empty-day message.
Два native report responses200 по разным URL hashes; оба86688 bytes,
SHA256 `9e88a983955449cd00daf8b95ba180552bccd50bb848590dee034dc21a4cac5e`.
Network response ledger:148 HTTP200 +2 HTTP204. Screenshot просмотрен отдельно
и согласуется с iframe; это native UI, не HTML proxy. Горизонтальная прокрутка
табличного документа видна; полноценная UI usability/nonzero приёмка не заявляется.

[Результат Hermes](https://github.com/Kwentin3/1c-agent-harness/issues/89#issuecomment-6015044709)
записан атомарно после закрытия browser/context. Последующий live `ps` не показывает
Chromium/Playwright descendants; прежний executor Apache57/58 сохранён.

Protected root: executor `.local/refine87-reference/access-admission/web-phase-20261006-1107/`.
Прочитаны и сверены следующие anchors (SHA256):

| Artifact | SHA256 |
|---|---|
| admission.json | `258755ea0f071d7634b65f88296fad6b34d6f6e047ad631a11c6664145c16cb0` |
| ready.json | `e83546d5a5eff669880670591adc05de93485417d34673bea7788ec5531d5d5d` |
| hermes/result.json | `46c30c8c4ec0f1348b133e3d755a1cb0b5f4fcfe8a90de5891e0164588f1587a` |
| hermes/trace.zip | `b584ff9f834324b34cae138c09f0f30d821afc5649118ade7cca2b333b9bb0f3` |
| hermes/browser.stderr | `12f5fe04fe29559c5249889458c0cec3059a42a0480e14db0044c93029249d0d` |
| completion.json | `c666689d8ac73d04c0662511bba586124bf5ee3e7f326773e3d49c3815fbb6a3` |

Hermes evidence:40 files/3201571 bytes после browser cleanup. Operator supervisor
обнаружил result и выполнил early rollback. В completion: `finished_utc=2026-10-06T11:15:00.832991+00:00`,
exact прежние target/image, `exited`, PID0, только bridge, ports{},
`config_vrd_aliases_unchanged=true`. Stop/disconnect commands rc0.
Top-level `status` остался устаревшим READY; итог берётся из `final_state`,
`finished_utc` и реально записанных command receipts, не из этой старой строки.
Docker-side факт подтверждён прочитанной операторской квитанцией, не прямым Docker
доступом Hermes. Test IB сохранена: текущий SHA256
`d2c52af3dd6c6bca406bd9ca4493ee710424f4a249bf9362259365c8a7334f64`.
Её изменение допустимо в test web-сессии; оно не относится к исходным CF/snapshot.

**Граница:** ordinary Hermes empty-day/Refresh PASS + operator host denial403 +
rollback receipt. Не nonzero oracle, не постоянный защищённый owner access,
не fresh-agent reproduction, не cold/native CLI на новом runtime.
Нового start/restart в остатке окна нет. Следующий runtime/web этап требует
отдельного конкретного плана/допуска. Goal91 остаётся открытой.

## История: первая разрешённая web-попытка 2026-10-06

После [operator admission](https://github.com/Kwentin3/1c-agent-harness/issues/89#issuecomment-6013416849)
владелец в текущей сессии разрешил только ограниченный web-план; approval зафиксирован
[отдельно](https://github.com/Kwentin3/1c-agent-harness/issues/89#issuecomment-6013568204),
окно до 10:10 UTC, operator rollback не позже 10:09 UTC.
Прежний блокер «нет handoff #89» ниже — состояние на первом checkpoint, теперь снят.
CLI/cold/native и постоянный защищённый owner access этим не разрешены и не доказаны.

[Операторский READY](https://github.com/Kwentin3/1c-agent-harness/issues/89#issuecomment-6013630496):
exact target/image/network admitted, один start/endpoint/Apache start; Syntax OK,
UID33/GID33/groups33, host request получил403. Это операторские свидетельства,
не собственная Docker-проверка Hermes.

Hermes своим strict pinned SSH подтвердил UID10001/GID10001/groups10001,
хеш admission `5b88a63241e24aedd82e4a682c387023bde4aa1655debf8e1230346d78955892`
и размер69781 bytes. Прямой HTTP prerequisite вернул200.
**Одна browser-попытка: FAIL**, 16.763s: `Page.content: Target crashed`.
До crash получены20 HTTP responses200 и три HTML body; report content/Refresh
не проверены. Browser/context закрыты; последующий `ps` не показывает browser
процессов, прежний executor Apache57/58 остался. HTTP200 не является UI PASS.
Причина crash неизвестна: OOM/нехватка памяти не доказаны. Дополнительное чтение
счётчиков памяти было заблокировано terminal safety hook до исполнения; обхода нет.

Protected evidence: executor `.local/refine87-reference/access-admission/web-phase-20261006/hermes/`:
`result.json` SHA256 `eead9f3c7519c93f5dacd49eb0049138f7678043ae60199d2625124cdc5b45a4`,
`trace.zip`391955 bytes, `private-error.txt`, `started.json`, `network.json`
(только hashes URL), `html-ledger.json`, три native HTML body.
Сессионные URLs/trace/raw HTML не публикуются.

[Результат и запрос раннего rollback](https://github.com/Kwentin3/1c-agent-harness/issues/89#issuecomment-6013908077)
опубликованы до deadline. Final target stopped/network removal пока требуют
operator completion; запрос остановки не считается доказательством остановки.
Второй browser/start, расширение памяти или изменения среды не выполнялись.
Повтор требует отдельного решения после анализа сохранённых данных.

## Что проверено на первом checkpoint

Исходная ревизия `98905832388aa4b25fda61b6db8c6df860e9afdd`, tree
`f92122dbd0b7ecc808fe115e568f2f7e16482e4b`; чистая ветка `devops/jet-web-demo`
до документационных изменений этого checkpoint. Local terminal исполняет команды
в `/workspace/1c-harnest`, совпадающем с Git root; authenticated `gh` читает
issues/PR. Это отдельные проверки от remote product tool route.

| Проверка | Фактический результат / предел |
|---|---|
| `python3 -m unittest discover -s tests -v` | 344 tests, OK, 132.266 s; без реального запуска 1С |
| Отсутствующая/невалидная business binding | Source tests `test_hermes_deployment_wrapper` PASS; это не новая installed acceptance |
| Registered `one_c_observation_info` | `ok`, UTC, 3 файла / 47170 bytes, coverage partial=false |
| Observed source window | 2026-09-18 15:25:25.291000–15:26:22.170000 UTC; НЕ свежий журнал 6 октября |
| Registered `one_c_observe` | 98 records, stable retained selection, partial=false; limit=2 → groupsTruncated=true |
| Registered `one_c_expand_observation` | Первая группа содержит 5 records; offset=0, limit=1 вернул одну EXCP record, total=5, truncated=true; процесс 1cv8t, File not found с редактированными paths |
| #89 intake | В live issue нет operator admission/handoff: только ссылка на #91. Статус NOT_STARTED, не PLAN_READY |
| Новый reference / installed identity | Не приняты этим checkpoint; успешный ТЖ-вызов не доказывает identity plugin/companion/runtime |
| Cold CF / warm coding / native verify / web | Здесь NOT_RUN; старые receipts не подменяют новый прогон |
| ЖР select/page/record | Здесь NOT_RUN: select вызывает fixed native `ibcmd` exporter; отдельный бюджет ещё не согласован |
| Skills reconciliation | Source manifest tests PASS; полная installed parity не подтверждена. Исторические расхождения из runbook сохраняются |

Live TechLog opaque anchors (TTL один час; не долговечная квитанция):
`observationRef=snapshot:5983f83323445f243430ae48d467c25e`,
`groupRef=snapshot:5983f83323445f243430ae48d467c25e:group:EXCP:2c3513da771f91f0`,
`recordRef=snapshot:5983f83323445f243430ae48d467c25e:record:6:384634697276c4b5c45ef73a`.
Это сохранённая сводка наблюдавшихся ответов, не raw response archive и не доказательство
сохранности источника вне прочитанного окна. Новое чтение после TTL создаст другую selection.

Read-only пакетная сверка installed skill files была заблокирована terminal safety
hook до исполнения (сообщение о gateway lifecycle, хотя restart не запрашивался).
Никакого обхода запрета, изменения skill install или global configuration не было.
Этот сбой не является ни доказательством parity, ни разрешением на переустановку.

## Воспроизведение доступной части

На exact source revision (или этом documentation-only потомке):

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest tests.test_hermes_deployment_wrapper tests.test_skill_sources -v
git diff --check
```

В обычной сессии с зарегистрированными tools:

1. `one_c_observation_info({})`: использовать возвращённую timezone/coverage.
2. `one_c_observe(start="2026-09-18T15:25:25.291000", end="2026-09-18T15:26:22.170000", events=["EXCP","EXCPCNTX"], limit=2)`.
3. `one_c_expand_observation(groupRef=<ref именно нового ответа>, offset=0, limit=1)`.

Окно выше воспроизводит чтение старого источника; оно не должно автоматически
заменяться текущей датой или называться проверкой свежести текущей ИБ.

## Порядок дальнейшей приёмки

1. **Операторский handoff #89.** Read-only проверить exact retained target
   `1c-issue87-reference-20261003` / ID
   `d2f38aa86d7bc461712df72fc22d5eb924324cbf5f386ca44a458024fd24970c`,
   image/labels/state, ownership/retention, сохранённые IB/runtime/evidence и
   два declared resource aliases. Это identity из опубликованного контракта,
   не новое live Docker observation Hermes. Не запускать target ради discovery.
2. Оператор публикует **один минимальный план** обычного web/native доступа,
   точные non-secret команды, UID/GID/groups, private route, executor-injected
   runtime locator, write boundary, ресурсы/окно и адресный rollback.
   PLAN_READY не равен HERMES_ACCESS_READY. Не менять старый locator/установку.
3. Только после этого — актуальное owner approval точных start/access/deployment
   side effects. Нельзя сейчас добросовестно запросить одобрение неизвестных
   команд/портов/прав вместо ещё отсутствующего плана.
4. До первого native: заморозить identities CF/snapshot/manifest, installed pair
   и runtime, task artifacts, время и **отдельные** лимиты cold materialization,
   substantive verify и ЖР export. CREATE/load/dump/runtime считать явно,
   старые слоты не расходовать. Выбрать принятый сценарий #69, не новый benchmark.
5. Свежий агент получает обычную задачу и несемантический environment contract:
   cold open → warm reuse → narrow → verify на выделенной task-owned копии,
   request/patch/raw/oracle binding и cleanup. Source/CF/manifest immutable.
6. Точный dashboard-кандидат #86: настоящие ненулевые данные, расчёт/Refresh,
   сохраняемая demo, согласованный restart, защищённый owner access и отказ
   неавторизованному клиенту. HTML proxy и прежний empty-day PASS недостаточны.
7. Завершить installed skill reconciliation без потери дополнений, fresh discovery,
   ЖР selection/page/record и immutable installed identities. Полный финальный
   evidence report затем заменит статус checkpoint, не историю неудач.

**Минимальная внешняя предпосылка сейчас:** домашний оператор возвращает read-only
handoff по #89; постоянные sudo/Docker socket, новый transport и новая установка
не нужны. Никакие сервисы, 1С, Xvfb, `ibcmd`, browser/Apache в этом этапе не
запускались; observed ТЖ оставил только штатную retained selection с TTL.

## Карта открытых задач и owner decision

| Работа | Сохраняемая граница и следующий шаг |
|---|---|
| #85 / PR #86 | Exact head `264ad94183509f15cfccfc96c7cdaa65d9957fce`, OPEN, base main; bounded native calculations/form PASS и protected empty-day/Refresh delivery; READY_FOR_OWNER_REVIEW, не nonzero/широкий rollout |
| #87 / PR #88 | OPEN, base `product/owner-yesterday-dashboard`; installed `eaab4cf` cold/warm/narrow/native PASS + protected web restore; [финальные identities/evidence/пределы](goal91-final.md), READY_FOR_OWNER_REVIEW |
| #71 / PR #72 | #71 OPEN; PR #72 MERGED, merge `8a9b31ac805923ba08f31017b9efd7b167fe4669`. R&D/prototype ≠ production root cause; статус issue не закрыт автоматически |
| #73 / PR #74 | #73 OPEN; PR #74 MERGED, merge `05f7876b87201df5cd631ead8fb2881dcce88d9c`. [28 retained receipts, investigate/expand](issue-73-runtime-diagnostics-live.md), не live sessions или свежий источник |
| #36 | OPEN; terminal PRODUCT FAIL сохранён в #92; новый эксперимент не начат |
| #37 | OPEN; [observability facts](issue-37-headless-probe-observability.md) не доказывают полное isolation/root-cause закрытие; остаток не переквалифицирован |
| #41 | OPEN; compile-hardening gate остаётся отдельным, нужен отдельный harmless контракт/бюджет; запуска здесь нет |
| #90 | Следующая продуктовая задача, новая acquisition ЖР вне #91 |

Merge не разрешён. Если владелец отдельно разрешит, зависимость остаётся
**main ← #86 ← #88**; после каждого merge нужны exact tree и post-merge CI.
Текущий итог подготовлен к owner decision; source/runtime/web доказательства и
неповторённая positive ЖР проверка разделены в финальном отчёте. Это не разрешение
на merge, новый native budget или переквалификацию исторических FAIL.
No-paid/no-reviewer граница продолжаемой #87 сохранена; новый внешний review
не запускался, исторические INCONCLUSIVE отзывы не названы одобрением.
