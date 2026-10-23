# Goal90 — current-source checkpoint

## Текущий checkpoint, 2026-10-22

**34a УСТАНОВЛЕН / ТРИ UI-ЦИКЛА И SOURCE-ПАРИТЕТ ПОДТВЕРЖДЕНЫ / SELECT COST ACCEPTED ≤11s / ЭТАП ПРИНЯТ ВЛАДЕЛЬЦЕМ / VISIBILITY≤30s ОТЛОЖЕНА.**
Решение владельца2026-10-22: завершить текущий этап по уже полученным результатам,
дополнительные live-тесты и неподтверждённый замер visibility≤30s перенести на реальные
кейсы в [#92](https://github.com/Kwentin3/1c-agent-harness/issues/92). Это изменение
приёмки этапа, а не PRODUCT PASS отсутствующего замера. Существующие тесты сохранены;
новые21/7, restart, merge/release не разрешены. Код, runtime и ledger20/6 не меняются.

Решение владельца от 2026-10-22: принять текущую select latency при пороге ≤11s:
F10.185808181762695s/D10.566930055618286s/E9.672648191452026s. 5s — необязательное
будущее улучшение. Новых измерений и ускорения cold-route не было; прежние оценки
по 10s сохранены ниже. Visibility≤30s не подтверждена, PRODUCT PASS не заявлен.
Решение не расширяет исчерпанный бюджет exports/UI20/6 и не разрешает новый restart.

Matched runtime `34a4110a0bf04cba68404689e19d523f2279cfed`/c0, handler `fffd0fe2…`,
recipe `a249aae848a1fdd8117a40c801d1c370291eb47f`:35+35 source/6 plugin files,
canonical4b clean, native PM reload без Agent restart. Export19 — отдельный cold transport
profile:7.554746s wall,4.913607s до наблюдаемого SSH Sending-command,0.820590s native;
это не ordinary-chat SLO и не измерение отдельных фаз handler.

F: собственный UI context → File/Exit → native Log in, cleanup context/browser/driver завершён.
H24 JSONDecodeError возник до model/tool/export. Local Windows PTY воспроизвёл2117→512 total (510+CRLF);
remote failed input не сохранён, поэтому точная причинная связь квалифицирована.
Тот же фактический F prompt затем передан один раз штатным file-backed ordinary follow-up:
export20, select10.185808181762695s >10s (native0.5652431533671916s), stream inactive.
F raw/cache/public3/3 совпали без пропусков; native Start13:03:10/Finish13:03:46 UTC
согласованы с наблюдаемым root Exit13:03:45.864138. Visibility F **NOT_MEASURED**:
Exit→submit81.9240517616272s, →result97.20366215705872s — поздно, не30s PASS.
Прежняя D-after-E stability сохранена как history, новой проверки D/E после F не было.

Ledger `814073c4f62be8c1705945d691ab9bfa841aee46f287c9ad1b81f8494a9d35a2`,
contract `9ddb68dba6c8eb365c682e4f51dd71105d4659fde5bae0b7bafe8c0414a401e6`:
29rows,20/20 exports,6/6 UI attempts (3FAILED+3COMPLETED), help2/3,
native74.31000937824138/900s, pending/reserved0. Учёт не сброшен;21/7 не одобрены,
единственный разрешённый demo restart уже использован. Coverage остаётся partial,
valid visibility≤30s не доказана; documented partial coverage сохранён, ТЖ3 pending#92.
Финальный LOCK_SH read сопоставил6 hashed attempt IDs/statuses; native idle cleanup
оставил no master/socket при неизменном SSH config, без control exit/kill/socket removal.
[Единая приёмка](issue90-activation-checkpoint.md),
[session6TransportFreshnessFollowup](../experiments/issue90-current-source/runtime-20261022.json).

### Предшествующий FE checkpoint, 2026-10-22

**ДВА UI-ЦИКЛА И SOURCE-ПАРИТЕТ ПОДТВЕРЖДЕНЫ / COST GAP OPEN / PRODUCT ACCEPTANCE OPEN.**
Установлен matched runtime `fe956b2293346b3fa965d198f461799a92eae668`/c0:
handler `b67fdefd6e21bf732676201b3c0cbe0ef10e0b909e830e7c585a8bee7b1d9fc0`,
recipe `12c598dcceb2a35292977ce476f7ef6776502cb9`, 35+35 source files и6 plugin files;
native PM reload без Hermes restart. Один отдельно одобренный restart существующего
`1c-jet-demo.service` включил exact reference-container stop/start; pins до/после совпали.
Ровно это разрешение на restart израсходовано, повтор не разрешён.

D/E: fresh Jet main → File/Exit → native Log in, собственные context/browser/driver закрыты.
Source подтверждает Start/Finish каждого цикла; raw/cache/public3/3 каждый, пропусков0.
Прежняя D selection/page/record и cache SHA сохранились после E. Select D10.566930s
выше10s, E9.672648s укладывается. D visibility **NOT_MEASURED**: запрос отправлен
через37.366s после Exit, уже за30s. E Exit→first result32.032268s выше30s:
13.974735s до отправки +8.384885s model до tool +9.672648s tool. Это end-to-end gap,
не доказанная задержка публикации самого native ЖР. Coverage partial, completeThrough:null.

Canonical ledger `0a92fe15ec336efadb35d70b67d19a5abd1be7b4e0734293bd88d2c2fcb6bb51`:
exports18/18, attempts5/5 (3FAILED+2COMPLETED), help2/3,
native72.92417605989613/900s, pending/reserved0. Новый бюджет не предложен как одобренный.
[Текущая приёмка и границы](issue90-activation-checkpoint.md),
[квитанция: session5RecoveryFollowup](../experiments/issue90-current-source/runtime-20261022.json).

### Предшествующий CA checkpoint, 2026-10-22

**УСТАНОВЛЕНО / ОБЫЧНОЕ ЧТЕНИЕ ПРОВЕРЕНО / PRODUCT ACCEPTANCE OPEN.**
Matched runtime `ca642e3e2b7ca566840e0c614ab49caae7aed30a`/c0 установлен штатно;
handler SHA256 `389185892a1653afabb994c4c9dcc48fb3d0af7ff82a6c564c2ef23f608a2ce0`.
Один обычный cold select прошёл за9.05949s: raw/cache/public 3/3, пропусков0;
coverage остаётся partial. Прежние19.832/10.2156s сохранены как история, не заменены
этим одним результатом. Visibility30s и два успешных UI входа/выхода не доказаны.
Canonical ledger SHA256 `865f7ae78d97a327dadf0156f38c40009f16ad3f27dcda85f7fe14a7d20c3ec0`:
16/18 exports,3/4 FAILED UI attempts, help2/3, native71.38398242811672/900s, pending0/reserved0.
UI C показала native training/infobase connection cap. Restart не выполнялся:
предложение recovery охватывает существующий service и reference-container stop/start,
просит общий лимит5 попыток с сохранением3FAILED, exports18 без изменения;
это не разрешение на выполнение. [Единый исполненный итог и границы](issue90-activation-checkpoint.md),
[квитанция](../experiments/issue90-current-source/runtime-20261022.json).

### Предшествующий source-only checkpoint того же дня

**SOURCE-ONLY IN PROGRESS / PRODUCT ACCEPTANCE OPEN.** Продолжаются #90 и PR #93,
без нового Goal или review-цикла. Canonical source — `/workspace/1c-agent-harness`,
опорный commit `4b4c3d24ae7f534a03398157878c849fc52f98a8`. Его десять нативных tools
включают `one_c_stage_task`; current-capture branch PR93
`db7f7e894b847cd3fdf29c4da9be60751636c70d` объединяется с этой опорой без отката
staged tasks и публичных owner seams `validate_request` / `project_ibcmd_json`.
Cleanup при ошибке запуска stderr-reader исправлен в трёх существующих путях.
Три регрессии воспроизводят утечку реальных безвредных процессов до исправления
и подтверждают reap, отсутствие группы, закрытые pipes и безопасный отказ после него.
Полный source-прогон: **448 tests PASS** в изолированном Linux/Python3.14.7 без сети,
секретов и 1C mounts. [Квитанция и точные identities](../experiments/issue90-current-source/source-finish-20261022.json).
Exact-head CI3.9/3.12, установка и native PRODUCT PASS этим прогоном не удостоверяются.

Последующий source-срез завершён: учёт каждого capture перенесён к существующему
fixed handler и использует тот же ledger/lock/file owner. Полный прогон — **460 PASS**;
офлайн-репетиция на копии 14 фактических строк сохраняет 11 spent exports.
Большой receipt передаётся учёту как ограниченная техническая сводка с SHA полного
результата. [Квитанция accounting-среза](../experiments/issue90-current-source/accounting-source-20261022.json).
Старый операторский `export_research.py` нельзя оборачивать вокруг нового handler:
его предварительный STARTED приведёт к правильному отказу второго резерва.

Владелец одобрил и применён общий export-limit **16**; 11 использованных вызовов
сохранены. Effective contract SHA256:
`1322f0668a1d48b447333062bdf569946d32ecf0a75b6528b250d55441cb639e`.
Остальные лимиты неизменны. В этой continuation exports/session/native coding — **0**.
Новый source ещё не установлен, измеренная live latency не улучшена этим отчётом.

Readiness текущего профиля проверяется отдельно от принятого #97: предназначенные
demo credentials предоставлены владельцем через защищённый ввод; browser97 key/config
в текущем профиле отсутствуют. Его восстановление требует точного owner-действия.
Текущий dispatcher ТЖ возвращает migration-pending; это исходная граница deployment,
а не десять доказанно рабочих маршрутов. Подключение retained ТЖ оставлено отдельным
остатком [#92](https://github.com/Kwentin3/1c-agent-harness/issues/92), без новой logging policy.

[Финальный handoff #97](https://github.com/Kwentin3/1c-agent-harness/issues/97#issuecomment-6143900400)
принят в границах access/capability; [продолжение #90](https://github.com/Kwentin3/1c-agent-harness/issues/90#issuecomment-6143905887)
отделяет его от продуктовой приёмки. Engineering/browser routes, текущий read-only ЖР
и startup binding предоставлены. Прежние credential/CDP/access blockers ниже —
исторические, не повод пересоздавать доступ. Конфигурации текущего ТЖ в проверенных
effective roots не найдено; retained сентябрьский ТЖ не стал текущим.

Последний опубликованный ledger #97: help **2/3**, exports **11/12**, sessions **0/2**,
native **52.73141303029843/900 s**, STARTED/reserved **0**; SHA256
`d43b7e247158e9c24d5b60b923e284a663068deeb4927833f0d204e936842ab9`.
Это dated handoff, не новое чтение ledger. Один оставшийся single-shot export не
доказывает две fresh acquisitions; бюджет не сбрасывается и не расширяется.
Registered fresh-event witnesses и улучшенная full selection latency пока не приняты.
Исторические 17.05–18.83 s превышают порог ≤10 s; visibility ≤30 s не проверена.

[Checkpoint установки и активации](issue90-activation-checkpoint.md) отделяет исходники,
installed pair и результат обычного чата. Текущую активацию выполняет deployment
lifecycle owner; старый WebUI restart-рецепт ниже к текущему стеку не переносится.
См. также [source-кандидат и историческое продолжение](issue90-capture-candidate.md),
[реальный capture и отдельно маркированный replay](../experiments/issue90-current-source/current-capture-receipt.json).
Ниже сохранён исторический отчёт до #94; его ACCESS_BLOCKED и exports0 не являются текущим состоянием.

## Исторические checkpoints 7 октября, до принятого handoff #97

Ниже сохранены прежние измерения, рецепты и действовавшие тогда ограничения.
Они не являются текущей инструкцией доступа, активации или новым бюджетом.

Статус тогда: **PARTIAL / CURRENT_JOURNAL_ACCESS_BLOCKED**, не PRODUCT PASS.
Issue #90 открыта. Повторный approval на read-only binding/help/bounded export/session
контроли снят [уточнением владельца](https://github.com/Kwentin3/1c-agent-harness/issues/90#issuecomment-6034051631).
Новый live-source, installed positive selection/page/record и пользовательская
приёмка пока не исполнены. Документальные долги выполнены независимо:
[применённый disposition и конкретные owner остатки](issue90-debt-disposition.md).

## Возобновлённое исследование: действующий допуск и фактический результат

Проверен актуальный body #90, source HEAD перед работой `1a596cf04ad96e4d258726dfd6a0468770c7c733`,
Git root выбранного workspace, clean tree. Runtime исследован только через уже
provisioned strict/pinned diagnostic SSH; отозванный coding key #91 не использован.
До запуска сохранён контракт и ledger в task-owned `.local/` домашнего executor:
3 version/help, 12 экспортов, два цикла вход/выход, ≤30 s на вызов, ≤15 min native.
Пороги selection≤10 s / visibility≤30 s / export≤30 s / output≤1 MiB /
journal≤128 files/64 MiB сохранены; для текущего источника **не проверены**.

### Исполненная точная справка, а не предположение

- [Реальный `ibcmd --version`](../experiments/issue90-current-source/ibcmd-version.txt):
  **8.5.1.1150**, rc0, 0.469282983 s.
- [Реальный `ibcmd help eventlog`](../experiments/issue90-current-source/ibcmd-eventlog-help.txt):
  rc0, 0.065071466 s; `export`, JSON/XML, `--skip-root`, inclusive `--from/--to`,
  `--out`, positional journal directory, `--follow=<ms>` подтверждены исполнением.
  Для поддерживающей notifications ОС значение интервала игнорируется. Без follow
  новые события не ожидаются. Справка не обещает snapshot/fence/flush/rotation-consistency.
- Binary SHA256 до/после: `62e72e15bb4550c4ffcf421f962c27fd1e1ddde1ba31e5bc0d7c9e0c2352dde7`.
  [Receipt со stdout hashes и бюджетом](../experiments/issue90-current-source/native-research-receipt.json).
  Это закрывает прежний независимый evidence gap об атрибуции `--follow`, не live приёмку.

### Что действительно мешает экспортировать текущую demo

1. Admitted diagnostic SSH — UID10001 в существующем executor namespace. Его launcher
   всё ещё связывает ЖР с retained September archive #80. Inventory: два файла,
   5454/62581 bytes, September mtime. Это не текущая demo.
2. В этом namespace отсутствуют current reference IB/journal и business root;
   mount inventory не содержит их. Docker socket/sudo/doas отсутствуют. Это
   проверка доступной среды, **не** новая host-side проверка состояния reference.
3. Старая demo-копия существует, её основной файл имеет mtime 2 октября; это не
   основание для current binding. Operator retained postfix copy возвращает
   `PermissionError`. Права не ослаблены. Первый inventory остановился на этом
   исключении; после адресной обработки ошибки закончились остальные read-only
   проверки. Это не native/export попытка и не скрытый успешный доступ.
4. Публичный текущий URL без auth отвечает **401**; это проверка отказа и доступности
   защищённого ingress, не native login/E2E или HTTP interface чтения ЖР.
   Web credentials не заменяют filesystem/ibcmd-доступ; plaintext/секреты не искались.
5. Registered `one_c_observation_info({})` вернул ok: UTC, EXCP/EXCPCNTX,
   3 files/47170 bytes, retained interval 18 сентября. ТЖ route работает,
   но это не свежая October telemetry. Revoked coding route не пробовался.

Прямой export не запускается до current IB→journal binding. Экспорт архива, новый
login без возможности прочесть его ЖР, прямой произвольный host/IP-route, revival
старого key или собственный parser не являются различающим экспериментом.
`--remote` из help относится к standalone server administration gateway; наличие
текущего web-клиента не доказывает такой разрешённый endpoint. Он не угадывается.

**Одна внешняя предпосылка:** владелец deployment/домашний оператор предоставляет
непривилегированному diagnostics route read-only доступ именно к действующему ЖР
сохранённой demo с подтверждённой IB identity/timezone и exact ibcmd invocation.
Конкретный механизм (existing route, ограниченный mount или execution admission)
нужно определить на home host. Новые права/mount/ключи/deployment нельзя внедрить
из текущего read-only допуска. Не требуется ещё раз разрешать уже допущенные
экспорты; требуется отсутствующая техническая capability. Demo не останавливать,
root/Docker socket агенту не выдавать, runtime/ИБ не копировать на Hermes VPS.
Если доступ нельзя дать без новой топологии/stop, вернуть неприменимость этого
полигона, не выдавать несогласованную копию за current source.

### Расход, границы и воспроизведение

- **Help/version 2/3, exports 0/12, session cycles 0/2**, суммарно 0.534354449 s native.
  Лимиты не сброшены; сохранённые remote ledger/contract — основание продолжения.
- Source/tests/installed launcher не изменены; deployment/restart/new rights/merge=0.
  Спекулятивный metadata/capture seam не реализован до фактической feasibility.
- Current demo bytes недоступны: новой полной hash continuity demo/source/runtime
  не заявляем. Архив #80 и runtime locator прочитаны и запечатаны, не изменялись.
- Повторить справку можно на admitted executor командами `ibcmd --version` и
  `ibcmd help eventlog` **только с учётом оставшегося одного help слота**. Не выполнять
  обе повторно под видом reproducing evidence. Опубликованные stdout/receipt можно
  проверять локально без расхода native бюджета.
- Source-only suite первоначальной базы: 356 PASS / 155.194 s — отдельный #90 run,
  не исторический #91 run 57.864 s и не live-source performance. Exact-head CI нового
  supplement проверяется отдельно. В этом продолжении:
  `python3 -m unittest discover -s tests -p 'test_eventlog*.py' -v` —
  **35 PASS / 17.162 s**, existing simulated process/reader
  fixtures, не текущая ИБ и не actual ibcmd export. Stdout hashes/JSON ledger arithmetic
  проверены локально; `git diff --check` PASS. Local terminal/GitHub работают; coding native=0.
- Предыдущий Dual Review относится только к `1a596cf…`: DeepSeek без материальных
  blockers; Gemini INCONCLUSIVE/cli_timeout. Эти отзывы не покрывают новый supplement;
  неисправный arm автоматически не перезапускается и никакого merge approval нет.

Ни одна product acceptance checkbox не повышается до PASS. After-access следующий
шаг — один bounded direct export, затем только по его фактическому результату
минимальный source candidate и два session witnesses через existing reader route.
Не делать second store/parser/service/transport. Current feasibility остаётся UNKNOWN.

## Исторический checkpoint до уточнения автономии и новых help вызовов

Следующие разделы фиксируют прежние чтения и **предложенный тогда**, но уже
разрешённый владельцем бюджет. Фразы «нет нового help»/«нужен новый допуск» ниже
относятся только к этой прошлой точке; актуальный расход и technical blocker — выше.

## Что было установлено чтением, а не native-запуском

Исходная принятая база — [main `646273a44e47223d920911bdaec4bd35ae2b9ed6`](https://github.com/Kwentin3/1c-agent-harness/tree/646273a44e47223d920911bdaec4bd35ae2b9ed6),
tree `4bb37d169b631cb2c71501c862e6f89f24742de4`.

7 октября 2026 существующий strict/pinned SSH diagnostic route доступен, UID10001.
Прочитан установленный diagnostic launcher: он выбирает сохранённый
`live-journal-snapshot` эксперимента #80, не журнал текущей demo. В источнике
два файла, 5454 и 62581 bytes. Эти размеры не доказывают принадлежность текущей
базе или полноту до настоящего времени. Source release сообщает artifact
`sha256:415782d4419b82987e51f8539f0030cbcd3b3c5f3ae483541a1481bf25aa0ef9`;
это чтение release, **не новая closed installed-byte parity**.

Официальный ibcmd присутствует в уже подготовленном runtime executor; чтение
бинарных bytes дало SHA256
`62e72e15bb4550c4ffcf421f962c27fd1e1ddde1ba31e5bc0d7c9e0c2352dde7`,
совпадающий с [историческим точным #80 binary](issue-80-registration-log.md#supported-official-ibcmd-exporter-final-candidate).
Прочитана сохранённая stdout справки `ibcmd help eventlog` из эксперимента #80:
`export`, inclusive `--from/--to`, JSON/XML, `--skip-root`, `--out`, positional
journal path и `--follow=<ms>` (notifications на поддерживаемой ОС, иначе ожидание
с заданным периодом). Нового version/help invocation здесь **нет**.

Справка подтверждает наличие команды, но не snapshot consistency, fence/flush,
rotation behavior или полноту live-экспорта. Наличие `--follow` само по себе не
делает конечный bounded запрос согласованным срезом.

## Почему нельзя назвать текущий путь свежей диагностикой

- [Exporter](../one_c_harness/eventlog_file_exporter.py) принимает stable journal
  и сравнивает полный digest до/после. Это guard стабильности данного источника,
  не способ получить текущий согласованный журнал и не IB binding.
- [Reader](../one_c_harness/eventlog_observation.py) принимает XML, сохраняет
  selection/ref/TTL, различает empty/unavailable и count-based partial. Его
  `coverage.complete` относится к полученной выборке, не автоматически к текущему
  времени или к полноте live history. Максимальная дата записи не является fence.
- [Исторический wrapper](../deployment/goal91/one-c-harness) разделяет diagnostic и coding
  routes. Целевая demo находится в другом retained reference; purpose coding key
  #91 отозван по [completion](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6032686960).
  Его закрытое окно нельзя активировать или использовать для ЖР автоматически.

Не реализуется спекулятивный capture и не ослабляется stable-source guard до
проверки exact native возможности и фактической топологии. Нет fallback на архив,
копирования дописываемых файлов «как получится», temporary IB/BSL/EPF reader,
нового parser/service/watcher/index/framework или Hermes core patch.

## Минимальный следующий допуск (PROPOSED, не APPROVED)

В Hermes запрошен новый bounded допуск; явного ответа ещё не получено:

1. Оператор делает read-only admission **одного** журнала текущей учебной demo:
   фактическая IB identity, её journal binding, timezone, UID/read permissions,
   exact ibcmd availability и воспроизводимый способ вызова без остановки demo.
   Никаких новых прав, ключей, mount/ingress/services или runtime installation
   под видом чтения. Если существующая топология не позволяет это — вернуть
   минимальный отдельный план доступа, не исполняя его.
2. До 3 новых version/help invocations; до 12 экспортов, каждый ≤30 seconds,
   суммарное native время ≤15 minutes. Все вызовы получают последовательный
   ledger; failed/timeout тоже расходуют бюджет. Старые allowance не используются.
3. Два отдельно разрешённых штатных login/logout в учебной demo создают различимые
   session events. Reader получает только фактический bounded период, не ожидаемый
   текст. Никаких записей бизнес-объектов, config/log-policy changes и coding verify.
4. После фактического исследования публикуются exact source-кандидат и, если
   нужна смена установленной пары/launcher, **отдельный revision-bound deployment
   запрос**. Текущий запрос не разрешает deployment/restart/merge.

Предлагаемые измеримые пороги, фиксируемые **до** native acceptance: ordinary-chat
selection ≤10 s, появление контрольного события ≤30 s, один export ≤30 s,
XML ≤1 MiB, retained records ≤100, source inventory ≤128 files/64 MiB (текущие
bounds, не обещание пригодности больших production журналов). Превышение SLA
сохраняется как COST FAIL, отсутствие evidence — не «ошибок нет».

Матрица последующей приёмки: binding positive/wrong; fresh event A; exact retained
page/record/comment continuation; event B в новой selection при неизменности A;
empty/partial/unavailable/changing; append и, если осуществимо в допуске, segment
change (иначе explicit NOT_RUN); duration/bytes/latency; registered ТЖ и coding
refusal/warm read-only regression, local terminal/GitHub. Новый coding native
run не включён. Freshness fence/coverage и source identity должны сохраняться
с конкретной selection и быть доступны пользователю, а не только локальным metrics.
Точный metadata seam определяется по результатам native research, не создаётся
второй selection store или новый model-facing path/argv инструмент.

## Выполненные проверки и границы

`python3 -m unittest discover -s tests -v` в local workspace: **356 tests PASS**,
155.194 s. Это source regression принятых fake/native-seam fixtures, не вызов 1С,
не проверка установленного ЖР. Предшествующий Python-wrapped test command был
отклонён runtime guard до выполнения; обычный canonical command выполнился.
Новых 1С/ibcmd вызовов, export, контрольных событий, deployment/restart/merge нет.
Конфигурация, snapshot/manifest, demo/runtime и исторические evidence не изменялись.

Воспроизведение source-only проверки — приведённая unittest команда из Git root;
на runtime executor её нельзя запускать с реальной injected платформой вместо
test-owned unavailable runtime. Live continuation требует нового явного допуска
и operator identity/read-only handoff. При текущем блокере продуктовая цель #90
**не достигнута**; её нельзя закрывать docs/CI результатом.
