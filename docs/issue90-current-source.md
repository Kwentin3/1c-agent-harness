# Goal90 — current-source admission checkpoint

Статус: **PARTIAL / LIVE_SOURCE_BLOCKED**, не PRODUCT PASS. Issue #90 открыта.
Новый live-source, installed positive selection/page/record и пользовательская
приёмка пока не исполнены. Документальные долги выполнены независимо:
[применённый disposition и конкретные owner остатки](issue90-debt-disposition.md).

## Что установлено чтением, а не native-запуском

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
