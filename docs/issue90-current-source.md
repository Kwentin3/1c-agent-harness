# Goal90 — current-source admission checkpoint

Статус после возобновления: **PARTIAL / CURRENT_JOURNAL_ACCESS_BLOCKED**, не PRODUCT PASS.
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
- [Wrapper](../hermes-plugin/deployment/one-c-harness) разделяет diagnostic и coding
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
