# Goal91: coding admission после проверки транспорта

Статус на 7 октября 2026: **COLD_FAILED / WINDOW_CLOSED / WEB_RESTORED**.

## Текущее исправление CF materializer

Первый registered cold `one_c_open` установленного кандидата
`7b5ad3b756d07a7331d941b9376d01211532db7f` вернул `materialization_failed`.
Warm/narrow/verify не выполнялись. Окно закрыто досрочно, purpose key отозван;
demo восстановлена с проверкой входа, Refresh и штатного выхода на
<https://1c-demo.speechbattle.com/jetcontrol/ru/>.
[Completion и сохранённая диагностика](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6031464734).

В сохранённой диагностике `create.result` содержит BOM + `0`, native create.log
сообщает успешный CREATEINFOBASE; load/dump diagnostics отсутствуют. Перед cleanup
наблюдался Xvfb PID61, но его running/zombie state не снимался. Эти факты сами по
себе не доказывают причину отказа и не являются успешным cold open.

На установленном companion под UID10001 ошибка воспроизведена **без 1С**:
настоящий процесс-обёртка записывает result0 и завершается, оставшийся дочерний
процесс становится zombie; прежний materializer отклоняет шаг с
`native materialization left a running process`. Все процессы репетиции собраны.
Это доказанный дефект очистки, согласующийся с cold failure; исходное состояние
PID61 не восстанавливается предположением. Linux
[kill(2)](https://man7.org/linux/man-pages/man2/kill.2.html) допускает наличие zombie
при проверке существования процесса; одного killpg недостаточно для его сбора.

Исправление использует уже существующие `_prepare_process_ownership` и
`_stop_process_group` из `native_cycle`, включая child subreaper, сбор отделившихся
потомков и сохранение прежних дочерних процессов. Отдельный владелец lifecycle не
добавляется. Ленивый package import исключает цикл с `require_runtime`.
Отсутствие механизма ownership блокирует запуск до Popen. Result0, exit status,
600s на batch, immutable CF и cleanup staging сохраняются.

Кандидат plugin/companion:
`sha256:415782d4419b82987e51f8539f0030cbcd3b3c5f3ae483541a1481bf25aa0ef9`.
Это **source candidate**, не установленная identity и не native PASS. Установленный
artifact первого cold остаётся
`sha256:3d1bb0ac848bb49f15e0325d8f62eaa2ed05e2516db63ee96ceb6d051d616acc`.

Воспроизводимая локальная проверка на Linux:

```sh
python -m unittest discover -s tests -p test_cf_materializer_processes.py -v
python -m unittest discover -s tests -v
```

Четыре regression checks используют реальные процессы, без платформы 1С:
успешный result0 с orphan, потомок с setsid, timeout, nonzero result.
Процессы после каждого случая отсутствуют; timeout/nonzero остаются FAIL.
Отдельная проверка из изолированной копии 24 файлов production package layout
под UID10001 импортирует только предоставленный companion через штатный cwd;
checkout/scripts и дополнительные зависимости не требуются.

При полном unit-прогоне внутри reference оператор допустил ошибку изоляции:
старый deployment-wrapper test рассчитывал на отсутствие runtime contract,
обнаружил реальный runtime и получил `load_failed` вместо `precheck_failed`.
Он достиг CREATE и неудачной загрузки своей синтетической конфигурации; полный
фактический счёт platform launches не инструментирован. Это не fresh Hermes
replay, не native acceptance и не zero-native подготовка. Процессов 1С/Xvfb после
прогона нет, временный fixture удалён; demo web unit не перезапускался, три
immutable input SHA256 прежние.
[Публичная коррекция и проверка последствий](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6031716774).
Fixture исправлен: тест явно подставляет отсутствующий task-owned runtime.
Полный regression вне reference, без установленной платформы/runtime: Python3.12,
356 tests PASS (57.864s), compile PASS, 19 committed JSON examples PASS.
Исходные неуспешные результаты сохраняются отдельно и не объявляются PASS.

Для переноса кандидата с Windows нужен Git archive с
`git -c core.autocrlf=false -c tar.umask=0022 archive <exact-tree-or-commit>`;
byte-bound patches/receipts нельзя нормализовать вручную. При подготовке архив
проверяется по Git blob hash каждого файла и executable bit.

Следующая live-приёмка — **новое** ограниченное окно для точного исправленного
кандидата после source/CI и отдельного решения владельца. Закрытое окно с
NO_RETRY не переиспользуется. План: согласованное обслуживание до120мин,
backup/rollback пары, versioned companion + согласованные plugin/release/launcher,
проверка registration и безопасных negative routes; затем свежий Hermes agent
через registered tools выполняет cold≤3 → warm/narrow0 → verify≤3, всего≤6
platform launches, без retry/продления. До каждого cold/verify — прежний независимый
watchdog2100s и survivor check. После результата — revoke/exact stop, сохранить
evidence, убрать только task-owned disposable ИБ, restore и вход/Refresh/Exit.
CF/project-target/runtime/demo и retained diagnostics остаются прежними.

## История подготовки до первого cold

Разделы ниже сохраняют прежние evidence и допуски для трассировки. Их installed
paths/status относятся к соответствующим старым проверкам и не являются новым
разрешением на запуск или текущей deployed identity.

### Ожидания согласованы в source

Эта секция заменяет прежний блокер foreground600 и прежние значения adapter/shared
ниже; исторические проверки сохранены для трассировки.

- Реальный public terminal этой WebUI исполнил мгновенную команду с timeout2160;
  timeout2161 отказал до исполнения. Operator delivery6023131117 независимо принято.
- CI cold-diagnostics candidate c62bd59: Python3.9/3.12 PASS (run37512555200).
- Новый source-кандидат: plugin open/verify ждёт2160; narrow90 и diagnostics прежние.
  `timeoutSeconds` по-прежнему ENTERPRISE1..480, не общий бюджет.
  Shared route ждёт runner1320+T: два batch600 и120 резерва завершения.
  Inner platform limits не изменены. Реальные RED→GREEN тесты подтверждают dispatch
  и сохранение T; full352 PASS (148.618s), focused25 PASS, diff-check PASS.
- Release identity пересчитана. Installed plugin/companion/launcher не менялись.
  Длительность ожидания не гарантирует cleanup: watchdog остаётся операторской
  предпосылкой. При timeout никакого retry или success по частичным данным.

### Исторический план первого допуска (окно уже закрыто)

Владелец должен разрешить до120мин обслуживания, включая кратковременную
недоступность demo и необходимый перезапуск Hermes для обновлённого Python plugin.
T0 назначается только после готовности обоих операторов и отсутствия активных задач.

1. Установить git с зафиксированной версией в exact reference; сохранить контейнер,
   исходную CF, snapshot/manifest, demo, runtime и evidence. Не rm/recreate reference.
2. Установить exact reviewed Git candidate companion в новый root-owned versioned
   каталог; синхронно plugin/release/launcher, preserving diagnostic route и pinned
   known_hosts. Source launcher содержит старый fixed product path: оператор делает
   только documented substitution на новый exact candidate path, фиксирует diff/hash.
   Требуются backup/rollback пары и живой plugin registration после перезапуска.
3. После stop штатной web-службы: non-native timeout/disconnect rehearsal с setsid
   child, частичным evidence и exact-container cleanup; negative binding/config,
   forwarding/PTY и invalid envelope. Никакого 1C до успешной репетиции.
4. До каждого open/verify вооружить независимый host watchdog2100s, shell2040s
   (+kill-after5), terminal2160. Если весь watchdog не помещается до T0+105мин,
   новую операцию не начинать. Deadline окна абсолютный, без продления.
5. Только после этих gates один fresh-agent replay принятого #69: cold3 platform
   launches, warm/narrow0, verify3; всего максимум6, без retry. Это reproduction,
   не blind benchmark. Fresh run/nonce, frozen patches/oracle, реальные receipts.
6. Success/failure: revoke key/channels, exact-container stop/Pid0, сохранить evidence,
   адресно убрать disposable ИБ, восстановить прежнюю web-службу и login/Refresh/Exit.
   При неподтверждённой остановке — HOLD, web не поднимать поверх survivors.

Задания операторам и ответы: кратко — результат, доказательство, блокер,
следующий исполнитель. Полные hashes/PID/logs/rollback отдельно по ссылке.

Этот документ не является новым разрешением на запуск или обслуживание.

## Принятые результаты и границы

- [Owner web delivery, #89](https://github.com/Kwentin3/1c-agent-harness/issues/89#issuecomment-6019437901): постоянный HTTPS/BasicAuth, systemd lifecycle, owner dashboard/Refresh и восстановление подтверждены оператором. Hermes отдельно получил HTTPS401 без credentials; новый authenticated owner web test им не повторялся. Host reboot и encrypted credential backup не проверены. Пароль не переносится в Git.
- [Independent transport](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6021769489): обычный Hermes OpenSSH/ProxyJump, UID/GID/groups10001, exact cwd, CF/contract/runtime permissions, package import и invalid-envelope refusal проверены. Это не installed launcher или cold/native PASS.
- [Cleanup](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6021973588): оператор отозвал purpose key и проверил отсутствие всех трёх task sessions; owner service остался со стартом15:13:40UTC. Доступ сейчас не активен; автоматического продления нет.
- Ненулевой web-сценарий исключён владельцем из обязательной Goal91 и перенесён в #92. Основная цель — полный цикл на имеющейся учебной конфигурации.

## Исторические источники и установленная identity

Companion в reference:
`/opt/one-c-harness/60fa41bc6dcb6a6a4de38b22d2830501b9abfeba`.
Все23 Python package files сверены с source до изменения launcher.
SHA256 JSON(path→SHA256), sorted keys/compact separators, с префиксом
`one_c_harness/`: `bbc10c4e36c528e69604b22341243a22a3a6e44c6f2ec297e859ec74b824461d`.
Это фактические bytes, не доверие одному release label.

Business root `/srv/goal91-jet`, runtime config `/etc/one-c-harness/goal91-runtime.json`:

| Input | SHA256 |
|---|---|
| project-target.json | c95b082bcb4a1bd43aa05f71b434bf6d4effd04109e5c5e99c6b8efb698bba7a |
| .local/dist/Jet-1.0.3.1-tr.cf | 5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a |
| runtime config | 9ecb2c0c1be4413cacfd744d899c01e5b84984b994049a7ced9e53affe152185 |

Все три файла root-owned0444, не writable для10001. Web IB недоступна10001.
Product/runtime не копируются в business root; записи только в объявленные `.local` subpaths.

Проверены6 installed plugin files под `/data/hermes-home/plugins/one-c-harness`:
`adapter.py`, `schemas.py`, `__init__.py`, `plugin.yaml`, `release.json`,
`skills/one-c-harness/SKILL.md`. Каждый отличается от Git **только CRLF вместо LF**.
Declared artifactId `sha256:b8378fce1b796806ca05c9595391e1abfbe6efd0ec3accb56c09848a4a150ca1`.
Не называть эту установку raw-byte-identical source. On-disk проверка также не доказывает
identity уже загруженного в процесс модуля; зарегистрированные маршруты проверяются отдельно.
Installed adapter SHA256: `b4d2656091128e258256e24760095b27c1c8f1177a19479f4df0949c6f983702`.

Skills reconciliation: в canonical сохранены отсутствовавшие exact-help/publisher
и training print/export caveats из installed skill. Нет удаления дополнений или
изменения установленных skills. После обновления manifest:1c-enterprise-linux37,
headless-1c-probing6, semantic-contract-testing2 ресурсов; missing/extra/hash mismatches0.
Это byte parity, не fresh-agent discovery или native воспроизведение.

## Диагностическая регрессия этого продолжения

Зарегистрированный `one_c_observation_info({})` после executor recreate вернул `ok`:
UTC,3 файла/47170bytes, partial=false, EXCP/EXCPCNTX, интервал
2026-09-18T15:25:25.291000+00:00 — 2026-09-18T15:26:22.170000+00:00.
Это сохранённый старый ТЖ, не свежий журнал октября. Source discovery работает;
ЖР selection/export в этом продолжении не запускался.

## Минимальное изменение launcher — до live deployment

Меняется только ветка `open|narrow|verify` существующего
`hermes-plugin/deployment/one-c-harness`:

- trusted `ONE_C_HARNESS_PROJECT_CWD` допускает только `/srv/goal91-jet`;
  missing/wrong binding отклоняется **до SSH**, без fallback на старый проект;
- trusted абсолютный `ONE_C_HARNESS_CODING_SSH_CONFIG` указывает на отдельный
  pinned config, alias `goal91-reference`; credentials в существующей защищённой
  deployment-области Hermes, не в проекте;
- fixed command передаётся через stdin, а не через игнорируемый SSH_ORIGINAL_COMMAND;
- Python `-I -B`, root-owned package, child import environment сохраняются;
- диагностические операции продолжают использовать прежние source/runtime/SSH.

Не менять global terminal backend, schema инструментов, domain API, старые журналы,
web credentials или owner demo. Source-тесты подменяют **только SSH** и не доказывают
живую установку. До активации нужен exact candidate SHA/hash, backup installed launcher,
точный diff deployment substitutions и локальные required env. Нельзя просто заменить
installed launcher исходным файлом: существующий pinned known_hosts обязан сохраниться.

## Проверки source-кандидата

- `python3 -m unittest discover -s tests`: **346 PASS** после изменения launcher
  и reconciliation skills (150.951s). Это локальная source-регрессия, не native.
- `python3 -m unittest tests.test_hermes_deployment_wrapper -v`:8 PASS.
  Проверены stdin transport, exact binding, обязательный абсолютный config,
  отсутствие fallback при SSH failure, старый diagnostic argv и реальный локальный
  companion на подменённом только SSH. Отдельно пройден RED→GREEN для сохранения
  child import contract: PYTHONPATH=product, PYTHONSAFEPATH=1, PYTHONNOUSERSITE=1,
  несмотря на hostile inherited Python environment.
- `sh -n hermes-plugin/deployment/one-c-harness`, `git diff --check`:PASS.
- Содержательный child source audit и адресные тесты — не внешний Dual Review;
  no-paid/no-reviewer граница PR88/#87 сохранена.

## Уточнение после операторского ответа 6022490812

Оператор подтвердил отсутствие `git` в reference. Установка требует отдельного
допуска; собственной замены `git apply` не вводим. Предложенная аварийная граница —
остановка exact reference контейнера без удаления/recreate, затем восстановление
через существующую web-службу. Watchdog и non-native репетиция ещё не выполнены.

Лимит реального Hermes terminal проверен без native: вызов с timeout=601 отклонён
до исполнения (`Foreground timeout 601s exceeds the maximum of 600s`). Поэтому
предложенные2160s пока недопустимы. В установленном `/opt/hermes/tools/terminal_tool.py`
есть `TERMINAL_MAX_FOREGROUND_TIMEOUT` (default600), но изменение общей среды и
перезапуск Hermes требуют отдельного решения владельца. Не применять молча и
не обходить фоновой командой. До такого решения таблица новых timeout не RUN_READY.

CI-коррекция `b5b8150`: тест transport остаётся активным на Python3.9 и проверяет
ожидаемый отказ deployment bootstrap (Python3.11+), а на3.12 — успешный запуск.
[CI обеих версий PASS](https://github.com/Kwentin3/1c-agent-harness/actions/runs/37509890127).
Производственное требование Python3.11+ не ослаблено.

## Cold failure diagnostics: source-коррекция

Перед удалением staging сохраняются только существующие `create/load/dump.log`
и `.result` в приватный `.local/runs/project-target-failed-<uuid>`; IB/snapshot
не копируются. Проверяются symlink/nonregular/multiple-link entries. Это не защита
от враждебной конкурентной подмены путей. Исходная ошибка сохраняется; ошибки
retention/cleanup отражаются в notes и в structured TargetBlocked.message.
Fallback notes совместимы с Python3.9, но его traceback их автоматически не печатает.
Логи, уже удалённые до обработки ошибки, и незаписанные данные hard kill не восстанавливаются.

Ведущий независимо выполнил focused36 PASS и full351 PASS (157.706s).
Оба release.json пересчитаны и artifact closure проверена тестами. Установленный
комплект НЕ обновлён: новая source identity требует согласованной установки
companion/plugin, иначе существующий fail-closed version check должен отказать.
Python3.9 missing-API regression симулирована; реальный CI проверяется отдельно.
Native/SSH/deployment в этой коррекции не выполнялись.

## Оставшиеся предзапусковые проверки

1. Старый forced command завершал shell через30s. Его нельзя использовать для native:
   отдельное ограниченное окно и новый timeout требуют операторского допуска.
2. `hermes-plugin/adapter.py:279–284` даёт `open` только60s; materializer допускает
   до600s **на каждый из трёх шагов** (`cf_materializer.py`). Нельзя обещать, что они
   укладываются в60s или что внешний обрыв завершит все native descendants.
   До native зафиксировать согласованные outer/inner limits и cleanup при разрыве;
   при необходимости исправить и проверить этот узкий source-дефект без платформы.
3. `native_verify` передаёт runtime timeout+90 во внешний terminal, а shared route
   отдельно ограничивает subprocess; CREATE/load имеют свои batch limits.
   Название timeoutSeconds не является общим native budget.
4. Перепроверить writable directories, отсутствие native процессов/активного owner
   сеанса, exact source/plugin/companion/runtime identities перед live deployment.
   Не делать валидный cold `open` как «проверку binding» до допуска.
5. Отдельно завершить registered ТЖ/ЖР regression. ЖР selection может запускать
   native exporter на старом executor; не включать его незаметно в coding-попытку.

## Предлагаемый сценарий и счётчики — не разрешение

Предпочтителен один полный проход **свежего агента**, а не native репетиция ведущего
плюс ещё один такой же запуск. Повторить принятый небольшой прикладной сценарий
основания перемещения из #69 допустимо по контракту Goal91; это воспроизводимость,
не новый blind autonomy benchmark. Исторический COST FAIL не переписывается.

| Этап | Верхняя граница запусков 1С на один проход |
|---|---:|
| cold open: CREATEINFOBASE | 1 |
| cold open: DESIGNER /LoadCfg | 1 |
| cold open: DESIGNER /DumpConfigToFiles | 1 |
| warm open + narrow/search | 0 |
| verify: CREATEINFOBASE | 1 |
| verify: DESIGNER /LoadConfigFromFiles /UpdateDBCfg | 1 |
| verify: ENTERPRISE, client→server witness | 1 |

Итого **до6 platform launches**, без скрытого retry. При failure не тратить
следующие слоты вслепую; сохранить receipts и остановить текущую последовательность.
Xvfb — сопровождающие процессы, учитываются и очищаются отдельно. Owner web
restore/login/Refresh — отдельный web lifecycle, не «седьмой CLI».
Fresh runId/nonce, точные production/instrumentation patches и oracle должны быть
заморожены до verify. Historical request/receipts не переиспользуются как свежие.
Содержательный результат: сохранение основания в черновике и проведённом документе,
независимость от комментария, сохранение движений, отказ при нехватке остатка.
Source locators, patch closure и подготовленные bytes проверяются до native verify.

## Обслуживание и финиш

Absolute T0/deadline пока **не назначены**: часы запускаются только после source
readiness, одобрения владельца и подтверждения оператора. Предложение — до120мин,
последние15мин только cleanup/revoke/восстановление web. При нехватке времени не
начинать новую native операцию. Без автоматического продления/merge/release.

Оператор закрывает admission новых web-сеансов, подтверждает выход владельца,
останавливает только task service и поднимает exact reference без Apache.
Hermes активирует только согласованный launcher и проверяет запреты binding/transport
без платформы. Свежий агент выполняет один принятый цикл, сохраняет raw receipts;
ведущий независимо сверяет oracle, hashes и cleanup. Private key не покидает Hermes.
После успеха **или ошибки** оператор отзывает task key, завершает только task-owned
каналы/процессы, восстанавливает service и owner route, проверяет реальный web login/
Refresh/Exit. Disposable ИБ удаляется адресно; CF/snapshot/manifest/demo/runtime/evidence
сохраняются. Если native survivors не подтверждены как устранённые, web не запускать
поверх них: сообщить failure и выполнить согласованный адресный rollback.

До устранения перечисленных предзапусковых разрывов этот документ — подготовка,
а не RUN_READY. Следующий owner request должен ссылаться на exact tested candidate,
включать timeout/cleanup контракт и конкретные T0/deadline, без нового общего согласия
на неизвестные действия.
