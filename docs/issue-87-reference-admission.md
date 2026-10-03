# #87 refine: допуск отдельного штатного эталона

**Исторический preflight до операторского допуска.** Первоначальное предложение
ниже не являлось разрешением. Последующий owner-admitted operator reference
и его ограниченная приёмка описаны в [native web runbook](issue-87-native-web-runbook.md).
**GOAL INCOMPLETE**: native empty-day web принят; сквозной refine/public delivery нет.

Контракт: [owner refine](https://github.com/Kwentin3/1c-agent-harness/pull/88#issuecomment-5966401848).
Baseline: `7fc13929c14e83fdc751d5bf2ff16f648a4bf936`.
[Новый preflight](../experiments/issue87-web-publication/refine-preflight.json),
[исторический publisher PASS / browser FAIL](../experiments/issue87-web-publication/GENERATED-BROWSER.md).

## Выбор и доказательства

Сохранить Ubuntu **24.04 amd64**, учебную **8.5.1.1150**, файловый режим,
кандидат dashboard #85/#86 и данные отдельной копии demo. Изменить только
подготовку окружения: штатное размещение платформы и пакетный Apache 2.4
в **отдельном контейнере**, без переноса установленного дерева и локального
смешивания библиотек из разных ОС.

- Текущий executor действительно Ubuntu 24.04.4; это проверено по `/etc/os-release`,
  а не выведено из исторического Debian bootstrap. Remote checkout старый/dirty;
  его сохраняем, не делаем checkout/reset/clean на месте.
- Installer сохранён, 1 726 133 319 bytes, SHA-256
  `396b7065b9efb6272093f1bda5eab647081a13d9ccbb4c5cfb0e711346d5af28`.
- `ldd` на проверенном `1cv8t` с одним vendor library directory показывает
  зависимость `libwebkit2gtk-4.1.so.0` через `libwx_gtk3u-3.0.so.0`, а также
  отсутствующие системные GUI/CUPS библиотеки. Хеши `1cv8t` и этой библиотеки
  совпадают у original и sealed copy. Значение `ldd rc=0` **не** означает, что
  все зависимости найдены; не переносим старое blanket требование WebKit 4.0.
  У `wsap24t.so` в этой проверке нет `not found`, но это не проверка всех
  динамически загружаемых компонентов и не доказательство работы web.
- Один **non-root installer `--help`**, installation=0, завершился rc1 с
  `Unable to initialize installer`. Root filesystem read-only, `/tmp` и `/run`
  noexec. Эти факты не доказывают единственную причину отказа. Не снимаем
  ограничения текущего контейнера и не повторяем неизменённую команду.
- Exact training readme указывает один сеанс, только файловый режим, отсутствие
  паролей/OS-authentication пользователей ИБ и запрет реальной автоматизации.
  Это демонстрационный сценарий; внешний ingress остаётся отдельным допуском.

Общие официальные ориентиры:
[установка, раздел 2.3.2.2](https://1c-dn.com/library/tutorials/1c_enterprise_administrator_guide_file_mode_8_3_27/),
[публикация, bitness, права и worker MPM](https://1c-dn.com/anticrisis/tools-and-technologies/embedded-web-client/setting-up/).
Это **не exact 8.5 training recipe**: component IDs и параметры сверяются с
действительно заработавшей справкой installer. Exact readme не даёт матрицу
поддерживаемых ОС. Ubuntu 24.04 — обоснованный контрольный кандидат, а не
сертифицированный этой проверкой набор.

Registry identity официального Ubuntu base, проверенная без скачивания слоёв:
`docker.io/library/ubuntu@sha256:f610ab94648195aa356059f5b41d6085c9d4d903c072430cdd1af7bdb646106b`
(linux/amd64). Digest фиксирует base, не доказывает совместимость 1С.

## Одно ограниченное решение владельца

Разрешить домашнему оператору **один отдельный контрольный контейнер**, с
установкой пакетов и платформы **только внутри него**, без изменения текущего
executor, общей ОС и соседних контейнеров. Кандидат admission:

- Максимум 20 GiB дополнительных task-owned данных, до 2 CPU и 4 GiB RAM.
  Это предложенный потолок, не измеренный расход и не резервирование ресурсов.
  До pull/build оператор проверяет фактическую ёмкость Docker storage и память;
  прежняя проверка filesystem executor не заменяет host admission.
- Ресурсы помечены задачей #87; новые директории данных/evidence находятся под
  отдельной `.local/refine87-reference/` на домашнем executor storage. Каталог
  не существовал до текущего запуска; имена контейнера/image/volume и owners
  записаны до действий. Никаких broad prune и удаления неизвестных объектов.
- Платформа остаётся в предусмотренном installer `/opt/1cv8t/...` **внутри нового
  контейнера**, root-owned. Это явное ограниченное исключение из лабораторного
  размещения ПО в `.local/`, не перемещение существующей установки.
- Нет privileged/host network, Docker socket, постоянного sudo, новых host
  пакетов, DNS/firewall/proxy/IdP, public ingress и host port publishing.
  Package installation имеет только исходящий доступ в период подготовки;
  web listener только loopback нового контейнера. Браузерные проверки выполняются
  внутри него непривилегированно; вывод/evidence оператор сохраняет для Hermes
  через уже существующий маршрут. Новый SSH-транспорт не разрабатывается.
- Root только для подготовки, штатной публикации и управления Apache **этого
  экземпляра**; worker обслуживает отдельную ИБ от непривилегированного service
  user. Agent не получает административные credentials или Docker socket.
  Обычные обратимые исправления установки внутри этого объёма не требуют
  отдельного approval на каждую команду. Новая лицензия/правовая договорённость,
  превышение потолка или расширение границ — остановка.

Этот документ и «начать refine» не равны этому административному допуску.
До owner approval исполнение стадии ниже — **HOLD**.

## Передача домашнему оператору после approval

1. Проверить host capacity, существующие ресурсы, точный source baseline из Git,
   read-only hashes CF/snapshot/manifest/demo/backup и отсутствие сеансов demo.
   При текущем сеансе не делать живую файловую копию: дождаться безопасного
   quiescent состояния. Не останавливать чужие процессы.
2. Создать только task-owned экземпляр. В protected root-owned staging скопировать
   installer как данные и повторно проверить digest **до привилегированного
   исполнения**. Не исполнять root-код из user-writable workspace.
3. Сначала получить exact installer help в пригодной для штатного installer
   среде нового контейнера и сохранить её. Уточнить component IDs, необходимые
   пакеты и установка без GUI по этой справке. Не переносить `ws`,
   `v8_install_deps` или имена других опций из 8.3 как уже подтверждённые.
   Не скачивать/принимать новые закрытые дистрибутивы или font EULA автоматически.
4. Установить Apache из доверенного пакетного репозитория этой ОС и платформу
   штатным installer; сохранить base digest, полный `dpkg` inventory/версии,
   package sources, install argv/exit/logs и root-owned runtime manifest.
   Не использовать извлечённый runtime текущего стенда, preload, fake UID/version,
   binary patches или смешанные чужие GUI libs. При неподдерживаемом компоненте
   или ABI-конфликте сохранить конкретный blocker, не строить новый обход.
5. Подготовить **физически отдельную копию** demo; runtime user имеет нужные права
   только на неё. Старые demo/backup/CF/snapshot/manifest не монтируются writable
   в экземпляр. Копия предназначена для контрольного web-сеанса, не удаления
   сохраняемой demo. Считать HTTP через расширение 1С native-операциями тоже.
6. Один штатный publisher baseline этой же сборки, реальный пакетный Apache,
   worker MPM с одним обслуживающим worker process. Сохранить generated Apache
   config/VRD **до** любых поправок. Получить Apache syntax/module admission.
   Все поправки, включая loopback, paths, ownership и hardening, перечислить
   отдельным diff. Не заявлять byte-identical тест, если он производный.
7. Один fresh browser baseline без rewrite языкового URL и подмены HTML/JS:
   настоящий UI/dashboard, расчёт и Refresh. Ненужные WS/HTTP/OData/analytics
   ограничить явно и сохранить diff; изолированная физическая копия не разрешает
   автоматически включать сервисы в сохраняемой demo.
8. Только после UI PASS — один согласованный stop/start нового Apache и повтор
   dashboard/Refresh. При том же `/en` 404 сохранить минимальные request/response,
   версии, config/VRD, browser trace; остановить web-контроль. Не повторять старые
   slash/locale controls и не приписывать исход отдельной переменной без проверки.
9. Передать durable `DONE / PARTIAL / BLOCKED` handoff с точными ресурсами,
   состоянием процессов, расходом, invocations, retained evidence и cleanup.
   Hermes независимо сверяет файлы/хеши/наблюдения; summary не заменяет результат.

## Владельцы и дальнейшие этапы

| Смысл | Единственный владелец / seam | Проверка |
|---|---|---|
| Установка и publisher | vendor installer / webinstt; оператор исполняет штатные команды | exact help, install receipts, generated output |
| Runtime coordinates | executor-owned locator, `ONE_C_HARNESS_RUNTIME_CONFIG` | существующий `require_runtime`, без project paths/discovery framework |
| Native lifecycle и admission | companion/harness | regression `open/narrow/verify`, затронутые observation routes |
| Transport | существующая terminal/SSH boundary | не добавлять другой harness, SSH wrapper или install orchestrator |
| Способ работы агента | канонические skills + один Git recipe/runbook | manifest, installed identity, независимая fresh-agent приёмка |
| Dashboard semantics | неизменённый прикладной кандидат #85/#86 | реальный UI, расчёт, Refresh, сохранность |

До доказанного эталона не переписываем общий runtime контракт, весь skill и
bootstrap. Единственное текущее skill-уточнение — убрать неверное обобщение
WebKit 4.0; это инспекция ABI, не новый проверенный путь установки. Остальные
противоречия записаны как будущая минимальная коррекция: README locator,
installed/canonical skill drift, слишком общий совет переносить платформу.

После локального успеха — короткий проверенный recipe/runbook, только доказанно
необходимые адаптеры, регрессии и свежий агент без истории чата. Свежая приёмка
получает опубликованные инструкции и доступ, не coordinator notes/готовые
исправления. Ingress, merge, deploy существующих services и закрытие #87 отдельно.

## Retention и rollback

Старый executor/runtime/demo/backup и исторические evidence не удалять.
Контрольный экземпляр после успешной проверки остановить или оставить только
по owner-решению; сохранённые результаты и контрольную ИБ не удалять до intake.
Rollback — stop/remove **только помеченного task-owned контейнера**, сохранение
копии ИБ и evidence под task root; installer staging/package cache удаляются
адресно после фиксации receipts. Image/volume удалять только если создан текущей
задачей и больше ничем не используется. Никаких изменений общей сети/Compose
текущего executor для отката не должно требоваться.

Текущая стадия: SSH/preflight и dependency inspection выполнены; один installer
help failed; **installation/root publisher/Apache/native client/browser=0**.

Source checks перед публикацией: `python3 -m unittest discover -s tests -v` —
**344 tests, OK**; JSON/manifest/локальные ссылки и private-host scan прошли.
Это static/unit проверки текущего source-кандидата, не remote regression
`open/narrow/verify` на новом runtime и не web-приёмка. Полные установленные
skills ещё не сверены с каноническими: в них есть прежние дополнения вне
текущего narrow ABI-уточнения; совпадение version не означает byte parity.

Ни эталон, ни рефакторинг в целом ещё не приняты. Paid reviewers не запускались:
предыдущие технические failures не перезапускаются, no-paid граница #87 сохранена.
