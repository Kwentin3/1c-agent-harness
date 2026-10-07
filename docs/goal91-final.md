# Goal91 — итог ограниченного native/web цикла

7 октября 2026: **COLD → WARM → NARROW → VERIFY PASS; WEB_RESTORED**.
Свежая обычная сессия Hermes прошла установленный registered route; независимый
replay подтвердил 13 прикладных наблюдений. Demo восстановлена, вход/Refresh/выход
проверены. PR #86 и #88 подготовлены к решению владельца; merge/release не выполнены.

Это воспроизведение принятого сценария #69 на имеющемся полигоне, не новый blind
benchmark или универсальная write-поддержка. Исторический COST FAIL #69 сохранён.
Новая acquisition ЖР — #90; ненулевой web/workflow — #92.

## Точные source и installed identities

Исполнен [source `eaab4cf3b6c563e11388f02676acb54f0302d004`](https://github.com/Kwentin3/1c-agent-harness/tree/eaab4cf3b6c563e11388f02676acb54f0302d004),
tree `9ffa23e2fdf537bde30eeb6369bf3a9500f4da37`.
[CI Python 3.9/3.12 PASS](https://github.com/Kwentin3/1c-agent-harness/actions/runs/37577439810);
локальный Linux regression вне runtime: 356 PASS, 57.864s; compile и 19 JSON examples PASS.
Четыре real-process regression checks и UID10001 package-layout check обходятся без 1С.

| Identity | Значение |
|---|---|
| Plugin/companion artifact | `sha256:415782d4419b82987e51f8539f0030cbcd3b3c5f3ae483541a1481bf25aa0ef9` |
| Installed raw closure | 24 companion files на обоих executor routes; 7 plugin files; byte-exact с Git |
| Launcher SHA256 | `e67bea4eb6f998097811639ff0701687b3b2ab0f7f3c44a631dc559b1a468326` |
| Reference ID | `d2f38aa86d7bc461712df72fc22d5eb924324cbf5f386ca44a458024fd24970c` |
| Reference image | `sha256:69f919497cada9a8611f3de61df902d9f94bf20f84552ef5bd93125c38608ef9` |
| Platform binary SHA256 | `0d11379cfd37c029a472fa500cbd8a64050cc5e53f7904036f8f6ce6a7fe0574` |
| Runtime contract SHA256 | `9ecb2c0c1be4413cacfd744d899c01e5b84984b994049a7ced9e53affe152185` |
| Business project-target SHA256 | `c95b082bcb4a1bd43aa05f71b434bf6d4effd04109e5c5e99c6b8efb698bba7a` |
| Original CF SHA256 | `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a` |
| Snapshot manifest/contentId | `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`, 5099 files |

Business cwd `/srv/goal91-jet`, UID/GID/groups `10001`, root-owned immutable inputs;
продукт отдельно в `/opt/one-c-harness/eaab4cf3b6c563e11388f02676acb54f0302d004`.
Launcher имеет ровно две documented deployment substitutions: pinned known_hosts
и versioned companion path. Runtime/credentials не входят в предметный SnapshotRef.
Missing/wrong binding, missing/unreadable config и invalid envelope отказали до native;
forwarding/PTY и owner IB/evidence access запрещены. Runtime не переустанавливался.

Перезапуск Hermes выполнен текущим owner `run_dashboard_sidecar.sh production`;
WebUI/Dashboard/admitter healthy. Native loader выбрал установленный plugin и девять tools.
Canonical/installed skills: `1c-enterprise-linux` 37 files,
`headless-1c-probing` 6, `semantic-contract-testing` 2 — closed byte parity PASS.

## Окно, свежесть и помощь

[Новое разрешение и окно](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6031867458):
T0 05:50UTC, cutoff 07:35UTC, restore deadline 07:50UTC. Владелец подтвердил отсутствие
сеанса. Прежнее окно с NO_RETRY не переиспользовано. Обе non-native репетиции timeout
и disconnect доказали revoke/exact stop/PID0/отсутствие прежнего host PID.

Создана пустая ordinary Hermes WebUI session `16af09c959d8` в отдельном Git workspace
на точном source; обычные terminal/GitHub и зарегистрированные tools. Агент получил
Git-инструкции, установленный skill, опубликованный сценарий #69 и контракт среды.
Codex управлял watchdog/доступом/восстановлением и подавал отдельные phase dispatches.

Readiness началась 05:59:57UTC; final native turn завершился 06:32:14UTC — примерно
32m17s с ожиданием оператора и подготовкой. Это не 63 секунды «полной автономности».
Одна операторская коррекция пути staging: защищённая `.local` заменена существующей
writable `.local/runs`. Агент отдельно исправил readonly permissions своей копии и
порядок списка в static assertion. Все non-native неудачи сохранены; исходные файлы,
production patch, request/nonce и oracle не исправлялись вручную ради PASS.
Чтение квитанцы сначала отказало в terminal hook; простой read-only base64 read прошёл.
Нового review/subagent, native retry, альтернативного runner или admin fallback нет.

| Registered этап | Результат | Platform launches |
|---|---|---:|
| Один cold `one_c_open({})` | `materialized`, ready SnapshotRef | 3: CREATE, LoadCfg, DumpConfigToFiles |
| Один warm `one_c_open({})` | `reused`, тот же contentId/sourceIdentity | 0 |
| Три bounded `one_c_narrow_context` | Реальные InventoryTransfer locators; исходный TransferBasis отсутствует | 0 |
| Один `one_c_native_verify` | strict oracle PASS, canonical receipt | 3: CREATE, load/update, ENTERPRISE |
| Итого нового цикла | 2 open calls, 1 verify call, без retry | **6/6** |

Это счёт стадий закрытого исполненного алгоритма, не отдельная kernel-level трасса
всех exec. Cold watchdog 06:10:25–06:45:25UTC оставался активным при warm reuse;
после survivor/idle check отменён. Новый verify watchdog 06:27:00–07:02:00UTC.
[Verify dispatch и freeze](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6032326698).

## Предметный результат и provenance

Сценарий [#69](../experiments/issue69-transfer-basis/RESULTS.md): optional persisted
InventoryTransfer basis, независимый Comment, неизменные движения, shortage refusal.
До verify оба окончательных патча физически применены к отдельной копии actual snapshot.
Ровно два production XML и три instrumentation files; posting ObjectModule неизменён.
Независимая проверка подтвердила exact production/oracle и только замену fresh токенов
в instrumentation. Рабочая копия запечатана readonly.

| Frozen artifact / receipt | SHA256 |
|---|---|
| Fresh request (`runId=70a1c8cd-5828-4336-81b5-397060f2010d`) | `f1221a50822e576aa30f018231bf3ad2f363cac92ef4da030b1c61bc681ac8ca` |
| Production patch | `f1ddfef9d220d723d1279b82313b65328339f70ea05cb6651ee9498b041ce42f` |
| Instrumentation patch | `92a780f45f3e76e44ef512807f76d40917afe856fb6f72e5cdda5e1aec132ea4` |
| Oracle | `3cc861964dd4a31a82279a346801490a65c40d765630178f5800cb1e396da30c` |
| Exact verify argument JSON | `81f6d8fcf4ff9bda1d3ce808a945340b87f0b84483367c9f7873882174b0f6f3` |
| Prepared/runner/frozen/inputAfter identity | `cc960ce7845b239706583e5b41193d5f1e735a1688a49acbdf96be18f14526e7` |
| Canonical shared-route identity | `a7c4275cb37bef5bbad3d8e668328ad104389b6897b20f5c5d419a05958000db` |
| Canonical native receipt | `89da9f8a1f8d607daf660e9c31d16ed20031d204b6ecb5cb567a2d7de9be9151` |
| Raw client | `9efce57fc9fe54ecd9871f0dfa8c9c65ec7d47085d584a1b5924ecb4aeee6a57` |
| Raw server | `fb5bb8ef5a56929916bf707447115bd3f4d32735d0e716d0a6ade2471dac01ef` |

Identity algorithms различаются: manifest/contentId, content-only canonical и
mode-bound native tree не приравниваются друг к другу. Новый native runner:
`.local/runs/native-cycle/run-o58jdlxp`; cycle50.719s, total63.065s.
CREATE/load process0 и DumpResult0; runtime завершён штатным SIGTERM (`-15`) после
complete marker и двух стабильных чтений, runtime DumpResult отсутствует.
Это receipt-based business PASS, не утверждение runtime process0.

Независимый replay raw bytes: все 13 observations true — empty draft/post,
stock/cost counts and values, filled draft/post с независимым Comment,
stock/cost unchanged, shortage rejected и нулевые движения отказанного документа.
Seed прямой в disposable registers. Interactive InventoryTransfer form/full startup
не проверены; owner dashboard ниже — отдельная реальная UI-проверка.

## Cleanup, сохранность и защищённая demo

Штатный `compact-current-invocation-v1`: 3.118s, manualCleanupActions0,
removed224591832 logical bytes; frozen/work copy, IB/home/tmp и shared prepared tree
удалены. Дополнительная static copy удалена адресно после сверки её identity;
request/patches/oracle/spec/logs/raw receipts сохранены приватно.
Все 5099 исходных file hashes и manifest до/после совпали; runtime binary/resources/
aliases и demo IB до/после native совпали. Original CF/contract/runtime не изменены.

Purpose key отозван; exact reference exited/PID0, прежний host PID2714716 исчез;
оставшихся task SSH roots нет. Затем тот же reference/image восстановлен:
новый host PID2763670, start06:33:35UTC; прежний `1c-jet-demo.service` active/running
с06:33:36UTC, enabled/Restart=always. Service bytes и route bytes/uid/gid/mode совпали
с backup. Purpose SSH после revoke: rc255/stdout0. Все пять window timers inactive.

Правильный адрес: <https://1c-demo.speechbattle.com/jetcontrol/ru/>.
Обычный authenticated native browser: login06:35:39UTC, настоящий iframe dashboard
за2026-10-06, семь нулей/empty-day; Refresh06:36:38UTC; File→Exit→confirmation
06:37:09UTC вернул exit page с кнопкой «Войти». Tab закрыт. Public unauthenticated
HTTPS401; direct backend from home host403; published Docker ports{}. Защита и
credentials не менялись. Host reboot/полный credential recovery здесь не проверялись;
их инструкция и сохранённая web-доставка — [операторский контракт #89](https://github.com/Kwentin3/1c-agent-harness/issues/89#issuecomment-6019437901).

## Диагностика и граница ЖР

ТЖ: fresh registered discovery/selection/expansion PASS; UTC, retained September
interval2026-09-18T15:25:25.291000–15:26:22.170000, 3 files/47170 bytes,
partial=false, EXCP selection80 records. Это старая копия, не свежая October telemetry.

ЖР: три registered tools прошли current fail-closed checks: 48-hour selection
`invalid_request` до exporter; существующие expired selection/record refs —
`evidence_not_found`. TTL/cache не изменялись, exporter calls0. Положительные source/
selection/page/comment-continuation evidence остаются исторической приёмкой
[#80](issue-80-registration-log.md), а текущий valid export/positive page/record —
**NOT_RUN**. Их нельзя выдавать за свежую проверку; новая acquisition не добавлена.
Local terminal/GitHub после restart и закрытия окна работают. Это точная граница
текущей regression, а не обещание доступности свежего production ЖР.

## Воспроизведение и owner decision

Source/immutable inputs/пара устанавливаются по [coding admission](goal91-coding-admission.md)
и [reference runbook](issue-87-native-web-runbook.md). Для нового native требуется
новый bounded допуск: текущий ключ отозван, бюджет6/6 исчерпан.
После registered cold/warm/narrow stage inputs в task-owned `.local/runs/<task>/`,
не в protected `.local` root. Render fresh runId/nonce в request/instrumentation;
production и oracle из #69 сохраняются exact. Применить оба патча к отдельной
копии, проверить closure и запечатать; зарегистрированный verify получает exact
SnapshotRef и remote project-relative пути. Затем независимый oracle/hash replay,
cleanup/revoke/exact stop/restore и реальный login/Refresh/confirmed Exit.

Raw evidence не помещено в public Git: source/installed gates, transcript/ledger,
request/patches/oracle, canonical/raw receipts, runner logs, cleanup и browser
snapshots сохранены в private operator archive на обоих узлах. Значения secrets
не являются частью отчёта. Owner может проверить приведённые hashes по архиву.

`completion-evidence.tar.gz`: 132 evidence files, 1906589 bytes, SHA256
`b22b81f4fa8a70144c1209cbca385abf7a1367a54e5bc6a70e39530157d8db52`.
File manifest SHA256
`fed33361eda7a69a6a1cdd88d7d63edf27fa021fedb07d57f9553d93df12368b`.
Оба архива прочитаны обратно: root:root0600 в root0700 directories:
home `/var/lib/one-c-harness/goal91-maintenance-20261007T0550Z`, Hermes
`/opt/hermes-devops-agent/backups/goal91-maintenance-20261007T0550Z`.
Операторская read-only сверка в этом каталоге:
`sha256sum completion-evidence.tar.gz completion-evidence-manifest.json`;
`tar -tzf completion-evidence.tar.gz`. Архив включает manifest для каждого файла.

Итоговый PR commit дополняет исполненный `eaab4cf` только документацией;
код, packaging, tests и installed identity не меняются и не переустанавливаются.

Для #86 (`264ad94183509f15cfccfc96c7cdaa65d9957fce`) и #88 итог подготовлен к
owner review с указанными пределами. Merge только отдельным решением в порядке
**main ← #86 ← #88**, exact tree и post-merge CI после каждого шага. #71/#73 остаются
с ограниченной historical acceptance; #36/#37/#41 не возобновлены и не закрыты
автоматически как PASS. [Карта задач](goal91-checkpoint.md#карта-открытых-задач-и-owner-decision).

Старый cold FAIL и [операторский isolation incident](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6031716774)
сохранены. Число platform launches того случайного unit-прогона не измерено;
его нельзя прибавлять к этому новому циклу как известное число или называть zero-native.
