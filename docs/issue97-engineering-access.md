# Домашний engineering access (#97)

Дата: 2026-10-13. Кандидат доступа, без merge/release. Продуктовая приёмка #90
остаётся отдельной. Источник engineering/native кода: `bd40827a7e95bba9d08ed03d430559aca089c953`;
это потомок PR #95 (`0dbfa1c0cd9f61e547e95d4aef3b2d28531ad39c`).

Актуальный итог: ordinary engineering/runtime/browser/ЖР и post-cleanup приняты
Hermes; current startup source binding закрыт после согласованного обслуживания.
Условия двух bounded циклов #90 предоставлены, сами циклы **NOT_RUN**.
Один оставшийся export не гарантирует полную продуктовую приёмку #90.
Исторические PARTIAL ниже сохранены по этапам; последняя source admission — v3.

## Владельцы и границы

| Смысл | Владелец / контракт | Потребитель |
|---|---|---|
| Команды, процессы, disposable ИБ | обычный Hermes, SSH shell UID/GID10001 в выделенном namespace | разрешённая продуктовая issue |
| Изоляция и lifecycle доступа | оператор; pinned forced command → точный container ID | engineering SSH |
| ЖР текущей demo | существующий #94, фиксированный probe/export JSON | reader #90 |
| Native budget и admission | существующий canonical ledger #90 | native caller |
| HTTP credentials | native Hermes Secrets активного профиля | проверка HTTP и разрешённый будущий клиент |
| HOME browser | существующий Playwright/Chromium, тот же fixed-container SSH transport | browser97; session admission остаётся у #90 |

`engineering-shell.py` — только транспорт команд в фиксированную изоляцию;
не владелец reader, бюджета или бизнес-смысла. Старый executor содержит чужие
процессы и workspace; поэтому одного UID10001 там недостаточно. Использован
имеющийся образ и установленные runtime, без второго harness или backend.

## Обычный вызов

Backend Hermes остаётся local. Выполнять из обычного terminal tool:

```sh
ssh -F /data/hermes-home/credentials/ssh/engineering97/config -T engineering97 'id; pwd'
```

stdin доступен собственным программам; команда исполняется `/bin/bash -c`
в `/workspace/1c-agent-harness`. Source read-only; работа — только `.local/`.
Для Git в root-owned read-only checkout использовать только per-command
`git -c safe.directory=/workspace/1c-agent-harness ...`, без global config.
Native config: `ONE_C_HARNESS_RUNTIME_CONFIG=/workspace/1c-agent-harness/.local/one-c-runtime.json`.
HOME=`.local/home`, TMPDIR=`.local/tmp`, TZ=`UTC`.
Платформа: `.local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t`, учебная 8.5.1.1150.
Xvfb/libraries/fontconfig указаны в runtime config. Hermes подтвердил native
работоспособность одним учтённым CREATEINFOBASE: process0, DumpResult0,
штатный success log и созданная пустая1CD3203072 bytes. CF load/business
runtime этим smoke не проверялись.

После утраты tmpfs Hermes может восстановить только свои каталоги/config без
оператора и native вызова:

```sh
ssh -F /data/hermes-home/credentials/ssh/engineering97/config -T engineering97 'python3 -I -B -' <<'PY'
import json, pathlib
p = pathlib.Path('.local')
for name in ['home', 'tmp', 'cache/fontconfig', 'runs']:
    (p / name).mkdir(parents=True, exist_ok=True)
runtime = p.resolve() / 'platform'
(p / 'one-c-runtime.json').write_text(json.dumps({
    'schemaVersion': 1,
    'platform': str(runtime / '1cv8t/x86_64/8.5.1.1150/1cv8t'),
    'xvfb': str(runtime / 'libs/usr/bin/xvfb-run'),
    'fontconfig': str(runtime / 'fonts.conf'),
    'libs': str(runtime / 'libs/usr/lib/x86_64-linux-gnu'),
}))
PY
```

Физические ограничения: read-only root и bind mounts, network none, private PID/IPC,
capabilities ALL dropped, no-new-privileges, CPU1, RAM1GiB, PIDs128.
`.local/` — tmpfs512MiB/65536 inodes; `/tmp` — tmpfs128MiB/16384 inodes.
Ключи и host pins только в native credential source; Docker socket, host PID,
живой demo IB и host shell агенту не предоставлены.

CF `.local/dist/Jet-1.0.3.1-tr.cf` и manifest `.local/immutable/snapshot.manifest`
read-only. Manifest не означает наличие самого snapshot: canonical snapshot
в этой среде ещё не материализован. Изменять configuration в work copy разрешает
конкретная продуктовая issue; shell не расширяет этот допуск.

## HOME browser без изменения backend

Для браузера предоставлен отдельный fixed worker: engineering97 сохраняет
network none, browser97 использует обычный Docker bridge без published ports.
Это тот же `engineering-shell.py`, не новый harness/API или global backend.
Новая проверка label/network не допускает bridge для engineering или host/foreign
network для browser. Source нового handler:
`c6a8c951a930117ec9f10a21b9a7df7e95ee77fc`, installed SHA256
`9e76e384ae3080a69668df31a1e61be25acab09e76e9bd9ac1cf45561015e38b`.
Прежний engineering handler и journal-only handler не заменялись.

```sh
ssh -F /data/hermes-home/credentials/ssh/browser97/config -T browser97 'id; pwd'
```

CID `b547e8ac370892449a89b16148ff7f2c3a0169b25dcf0198dad6ea7077bb39f8`,
тот же image pin, source checkout bd40827. UID/GID10001, private PID/IPC,
capabilities0/no-new-privileges, CPU1/RAM1GiB/PIDs128, read-only root/binds,
собственные `.local/`512MiB и `/tmp`128MiB. Живая ИБ/socket/host PID не доступны.
Browser/libs borrowed read-only, новых browser file bytes0:1003 files,
466079922 logical bytes; heavy данные остаются на HOME. Приложение может
использовать сеть, поэтому доступ к URL не является правом менять demo.

Установленные Playwright1.58/Chromium145.0.7632.6 доступны через
`PYTHONPATH=/opt/issue97-browser/python`,
`PLAYWRIGHT_BROWSERS_PATH=/opt/issue97-browser/cache`; loader/fontconfig env
задан оператором в worker. Выполнять `python3 -B`, поскольку `-I` исключает
PYTHONPATH. После потери tmpfs обычный Hermes самостоятельно выполняет
`mkdir -p .local/home .local/tmp .local/cache/fontconfig .local/runs`.
Вести не более одного browser/client процесса одновременно; закрывать свой
context/browser штатно и убирать только свои task files/process groups.

Секреты читать native getter на Hermes в `/app/venv/bin/python` и передавать
SSH stdin в память HOME процесса; не сохранять в task files/argv/logs.
Для исключительно HEAD admission использовать `APIRequestContext` с
`http_credentials={username: ..., password: ..., send: 'always',
origin: 'https://1c-demo.speechbattle.com'}`, timeout15000 и max_redirects0.
Ошибки сохранять только как type/первую строку: полный Playwright call log
может содержать Authorization. Для реального browser context эти параметры
APIRequestContext не подставлять автоматически; он получает отдельные
http_credentials и допускается только после session admission #90.

Operator ordinary-UID probe: own about:blank DOM rendered, HEAD200HTML,
native/session/export/help0. Initial8s challenge retry timed out; заранее
переданная Basic authorization дала200 за1.73s, без изменения сервера.
Отдельный network-none browser rehearsal PASS, контейнер удалён. Первый
rehearsal отказал на inherited executor entrypoint; использован явный python3
entrypoint. Неудачный диагностический lifetime test сохранён; исправлена
граница context manager. Ни один browser probe не открывал demo JS/session.
Личная Hermes browser/post-cleanup проверка PASS после operator cutoff08:40:14UTC:
SSH08:44:10UTC, hostnameb547e8ac3708, own loopback DOM/JavaScript rendered,
HEAD200HTML, UID/GID10001, protected inputs unchanged, все refusals PASS.
Baseline zombies0, new/owned processes0 и own root absent после cleanup.
Receipt `receipts/post-init-browser.stdout` SHA256
`047365cc71cc2334db3692022192578a6bb5cb155f83cf556b3d0637eabc7ebe`,
protected root `/workspace/1c-harnest/.local/browser97-hermes-20261013T082233Z/`.
Первый личный witness PASS выявил baseline6 zombies; перед native `--init`
миграцией проверено отсутствие active client,8 собственных файлов сохранены
и restored manifest совпал. Native/session/demoGET0. Полный #97 PARTIAL:
безопасность старта именно current demo ещё не подтверждена.

Protected HOME provisioning receipt:
`/home/roman/.local/issue97-browser/operator/provisioning.json`;
Init migration/cleanup receipt: `operator/init-migration.json`, SHA256
`4fdf0bc777bc16b9bac221e90cdb27127bdec558ecb9a12c68d42b407d2a3e9a`.
Protected recovery: `operator/pre-init-tmpfs.tar`, SHA256
`d1fa10e23792165f7a71c829e7b29a1ac4aebff53fee31d15d4bfc8b54c03f8f`.
Protected browser evidence: `operator/browser-evidence.json`, SHA256
`f5fd21c8923f1a6adefd6e39373d7d7c8b7d22a55e0823908910dc7eefc5da5a`.
Native credential config `/data/hermes-home/credentials/ssh/browser97/config`,
SHA256 `84fce698740ba1f34aeeb5b2b3e8706c1bab93e9b8f724c4ea915144e38f5504`.
Rotation/revoke как engineering97, только tagged `issue97-browser` entry;
не восстанавливать весь authorized_keys из before backup. Retain source,
readonly borrowed assets и protected evidence; route/key без TTL.

## ЖР и ТЖ

Маршрут #94 прежний:

```sh
ssh -F /data/hermes-home/credentials/ssh/current-journal/config -T current-journal \
  'current-journal-v1 eyJzY2hlbWFWZXJzaW9uIjoxLCJvcGVyYXRpb24iOiJwcm9iZSJ9'
```

Причина regression: новый `20261011000000.lgp` принадлежит UID/GID33 и имеет0600;
worker UID10001/GID33 получал `PermissionError`. Worker теперь UID/GID33,
с теми же read-only mounts/network none/capability restrictions.
Исходный журнал и его права не менялись. Readable runtime directory создан
hardlinks существующих файлов, без изменения исходных файлов/каталогов.

Текущая связь: fixed reference container → `/var/www/jetcontrol/default.vrd`
→ `File=/var/lib/1c/ib` → `1Cv8Log`; timezone UTC. Native exports не запускались.
ТЖ: `conf/conf.cfg` содержит `ConfLocation=/opt/1cv8t/conf`, Apache envvars
задаёт HOME=`/var/lib/1c/home`. В фактических `/opt/1cv8t/conf`,
`/var/lib/1c/home`, platform conf, `/etc/1c` и стандартных home roots
`logcfg.xml` не найден; current ТЖ source/coverage не установлен.
Это подтверждённое отсутствие настройки в проверенных roots, а не утверждение
об отсутствии любых событий. Retained18сентября не является current demo source.
Logging не включать.

## Demo admission и учёт

URL: `https://1c-demo.speechbattle.com/jetcontrol/ru/`.
Native Secrets: `ONE_C_DEMO_HTTP_USERNAME`, `ONE_C_DEMO_HTTP_PASSWORD`;
чтение через `hermes_cli.config.get_env_value_prefer_dotenv`, active source
`/data/hermes-home/.env`. Значения не печатать, не помещать в Git/workspace/chat.
Authenticated HEAD дал200, без запуска сессии 1С. Это не login/logout witness.

Engineering namespace не имеет сети; browser97 предоставляет HTTPS client,
source binding после согласованного обслуживания приведён ниже.
Retained canonical snapshot находится в reference
`/srv/goal91-jet/.local/targets/jettr-1.0.3.1/snapshot`; его manifest совпал с
immutable pin выше. SessionModule вызывает `StandardSubsystemsServer.SessionParametersSetting`,
тот — `BeforeStartApplication` (line3727). Этот путь включает условные
`CorrectSharedUserHomePage` (line3906, `CommonSettingsStorage.Save`) и
`HandleCopiedSettingsQueue` (line4039, `SystemSettingsStorage.Save`).
ManagedApplicationModule вызывает BeforeStart/OnStart библиотеки;
`DisableSystemStartupLogic` в клиенте не отменяет server session handler
и требует прав Administration/DataAdministration (ServerCall line200).
Эти записи — служебные настройки; их наличие само по себе не доказывает
business writes. Retained Dashboard.OnOpen строит отчёт, app overrides
BeforeStart/OnStart пустые; CTL/OSL/UsersSaaS модули отсутствуют. Однако
SSLSubsystemsIntegrationClient.BeforeStart включает условные InfobaseUpdateClient
и другие hooks. После обслуживания startup closure сопоставлен с текущим dump;
фактические права пользователя ИБ остаются execution-проверкой #90.
Штатный параметр БСП DisableSystemStartupLogic — кандидат только при уже
имеющихся требуемых правах, а не доказанный безопасный вход. Не обходить
проверку прав и не считать HTTP credentials данными пользователя ИБ.
Штатный web-кандидат: `?C=DisableSystemStartupLogic&DisableHomePageForms`.
[Primary 1C syntax](https://kb.1ci.com/1C_Enterprise_Platform/Guides/Administrator_Guides/1C_Enterprise_8.3.22_Administrator_Guide/Appendix_7._The_parameters_of_the_command_line_to_launch_1C_Enterprise/7.8._Webclient_command_line/?language=en)
описывает передачу application parameter через C и отключение home forms.
Он не исполнялся; CLIENT hooks подавляются, SERVER SessionModule остаётся.
Не использовать обычный startup fallback, UC или privileged mode.
UsersInternal.SetInitialSettings и пустой UsersOverridable.OnSetInitialSettings
меняют только client/interface settings; IBVersion!=0.0.0.0 не является
обязательным no-business-write gate. Current compiled-config/extensions binding
проверен отдельной цепочкой ниже; HEAD/VRD сами по себе его не подтверждают.
Владелец подтвердил: после HTTPauth сразу открывается demo, отдельной формы
1С нет. Дополнительный IB password не требуется; это не доказательство
административных прав или отключения startup updates.
Фактический safe login/logout пока NOT_RUN; source admission не заменяет
продуктовые cycles. При занятом/заблокированном slot не повторять
вход, не подтверждать обновление/отключение пользователей; failed attempts
тоже учитываются существующим ledger. Завершать только собственный сеанс
штатным Exit с подтверждением, не объявлять закрытие tab нормальным logout.
Не запускать demo клиент ради проверки доступа, не вытеснять sessions,
не менять logging/business/configuration или lifecycle demo.

Canonical checkpoint #90: help2/3, exports4/12, session0/2,
native8.480200893012807/900s, STARTED0. До любого связанного native вызова
владелец #90 делает реальную reservation; failed/timeout учитываются.
Допустимый следующий smoke: только пустая disposable ИБ в engineering `.local/`,
не более30s с предварительным учётом в существующем ledger, без help/export/demo.
Оператор продуктовые циклы не расходует.

Hermes выполнил ровно один такой smoke лично: attempt
`f700b97233d847dc8fd03e1f47b2c3bb`, настоящая STARTED/reservation30s под
существующим LOCK_EX; terminal COMPLETED,5.590007265098393s включая cleanup.
Ledger после этого smoke: help2, exports4, session0, native14.0702081581112/900s,
STARTED0, SHA256 `39de965f749fea23beb99611d4a1a7f7f04cb929b0b42d837ca553ae0c767669`.
Original contract SHA256 `325fbdc242d96de33774474408ce1482cb83806ab543ad398a1a7e751461fd8f`
не изменён. Runtime smoke записан отдельным kind `engineering-runtime-smoke`;
не export/session/help. Owned IB/process group/children удалены, защищённые
source/CF/manifest/sentinel hashes неизменны. Runtime receipt stdout SHA256
`27b96d6c42de717bb66f53edd3a240a37898fec2a08943f048620329640ddc83`.

## Durability, retention и отзыв

Container `1c-engineering-issue97` имеет restart policy unless-stopped;
SSH route/key без TTL. Cleanup task-файлов/процессов не удаляет контейнер,
binding, source или credentials. Tmpfs данные исчезнут при рестарте контейнера;
компактные receipts сохранять в защищённой `.local/` Hermes до уборки.
Runtime/CF/heavy copies остаются дома. Постоянная новая allocation — source,
XKB dependencies и directory metadata; runtime borrowed read-only/hardlinked.
Подробные bytes/inodes и raw receipts — защищённые locators ниже.
На HOME новая physical allocation: source8146944 bytes, operator/XKB4501504,
bundle2052096; runtime directory с540 hardlinked файлами —0 новых file bytes
(logical1297523968), плюс metadata новых каталогов. Свободно268515135488 bytes,
18811490 inodes перед smoke. Никакие runtime/ИБ на Hermes не копировались.
Bundle удалён после SHA-verified retention в operator worktree, освобождено
2052096 allocated bytes. Environment work завершена2026-10-13T07:14:11.207217Z;
`operator/cleanup.json` подтверждает retained route и отсутствие helper workers,
engineering namespace содержит только PID1 sleep. Receipts/source/XKB/rollback
retained без TTL; компактные raw evidence имеют0600 в защищённом operator root.

Оператор rotation: создать новый ключ в том же защищённом credential source,
заменить только tagged `issue97-engineering` authorized_keys entry с прежними
from/restrict/forced-command и pinned hosts, проверить обычный маршрут, затем
отозвать старый ключ. Revoke: убрать только этот tagged entry; сохранить evidence.
Удаление контейнера — отдельный операторский teardown после retention task-data.
Rollback #94: CAS вернуть сохранённые handler и только marked authorized entry
из `/home/roman/.local/issue94-current-journal/.operator-backup`; старый worker
не читает новый0600 segment, поэтому такой rollback возвращает известный отказ.
Не заменять весь authorized_keys историческим backup и не восстанавливать key #91.

## Exact identities и evidence

- Engineering container: `1f3565421de9c18af24408e6a04db29297ba7c3dd61810ec8f6806fa77ffd5ba`;
  image `sha256:036a932ca78ec1f161b83fc3d26d663d950a8e845002c160771950ec72ce6488`.
- Engineering handler SHA256: `141d35b42acca75de0553328fde3d859a4f792577a3abef75a380fcefd9cec68`.
- #94 handler SHA256: `8e2063e572ad88adf1e84acdbd4091127f09ffe1e906a65cdc7b448d500cbe81`.
- Current reference: `d2f38aa86d7bc461712df72fc22d5eb924324cbf5f386ca44a458024fd24970c`;
  image `sha256:69f919497cada9a8611f3de61df902d9f94bf20f84552ef5bd93125c38608ef9`.
- VRD SHA256: `e5406c8e7352b43c6499e2ff4fe189c9b239fe045eb0ac46de2960555850ac7d`.
- CF SHA256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`.
- Manifest SHA256: `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`.
- Protected HOME deployment receipt: `/home/roman/.local/issue97-engineering/operator/provisioning.json`.
- Protected operator receipts: worktree `1c-agent-harness-issue97/.local/`,
  `engineering-provisioned.json`, `engineering_refusals.receipt.json`,
  `journal-installed.json`, `route_probe.receipt.json`, `check_demo_secret.receipt.json`.

Operator boundary check: own code/process/cleanup PASS; source/CF/manifest/runtime/
foreign sentinel writes denied with hashes unchanged; setuid0/mount denied;
foreign process absent from namespace; no demo/socket visible. #94 probe PASS,
four journal files, native0. Unit current-journal7 и engineering6 PASS.
Hermes лично повторил own-code/process/cleanup, namespace/refusals, current ЖР
и прежний diagnostics/registered retained ТЖ: PASS. Защищённый receipt:
`/workspace/1c-harnest/.local/issue97-hermes-intake-20261013T064825Z/acceptance.json`,
SHA256 `83bf5b4eecda9784abea3ad94dfda1f97d964c5b00fc0daf20bb7c6d45752db7`.
[Sanitised operator evidence](issue97-engineering-evidence.json) связывает
raw locators/hashes с реальными checks. Native smoke PASS. После operator cleanup
Hermes лично повторил fresh own code/process/cleanup, refusals, ЖР и старые
diagnostics/registered retained ТЖ через те же config/aliases: PASS, native0.
Повторные SSH witnesses начаты2026-10-13T07:17:58Z, после cleanup07:14:11Z.
Post-cleanup protected receipt:
`/workspace/1c-harnest/.local/issue97-hermes-intake-20261013T064825Z/post-cleanup-acceptance.json`,
SHA256 `679bb2004fe46cda1640dfaa63f0e9eb761be233e02abd241ae7f53e277f1014`.
Исторический статус **PARTIAL / ORDINARY_ENGINEERING_RUNTIME_AND_POST_CLEANUP_ACCEPTED**:
остаётся current-demo safe-session capability gap. Два продуктовых login/logout
и fresh-event acceptance #90 не запускались; source candidate не merged/released.

Личная [final browser/post-init приёмка Hermes](https://github.com/Kwentin3/1c-agent-harness/issues/97#issuecomment-6142147442):
PASS, включая native init orphan adoption/reaping и повтор engineering/ЖР/diagnostics/
registered retained ТЖ после cutoff. Protected `final-acceptance-v2.json` SHA256
`6f4b59f76213cba9fd8ed1c4d3f70215f1f3979e160377dbbfb44faaad2d0597`;
`manifest-v2.json` SHA256 `d12c627aea7f53b638bdab099df5b565f6813ace3fd1f131ea320126acdfb897`,
102 files/390409 logical bytes. V2 исправляет ошибочный UI initialization gate;
source-admission-v2.md SHA256 `53fcab69e032ad468ed3a8345900b4254e7ca41f7983ed741e8d32bfee79b9a8`.
На этапе browser-v2 полный #97 PARTIAL: current compiled configuration/active extensions binding
к проверенному retained source ещё NOT_PROVEN. Дополнительный IB password
не требуется; два предусмотренных #90 cycles остаются0/2.

## Проверка чтения конфигурации, 13 октября

После browser acceptance оператор согласовал с consumer #90 bounded native
репетицию на disposable копиях **retained**, не текущей ИБ. Проверенный оригинал:
`refine87-reference/operator/reference-ib/1Cv8.1CD`, 118210560 bytes, SHA256
`b060127640773fda03a8c2bef5e9847d35f0b159bb116e043ce1e2ba84b9ac42`.
Использован существующий ibcmd8.5.1.1150, SHA256
`62e72e15bb4550c4ffcf421f962c27fd1e1ddde1ba31e5bc0d7c9e0c2352dde7`.
Каждая попытка отдельно зарезервирована как export в canonical ledger;
лимит30s, учтено время контейнера и cleanup, включая ошибки.

| Проверка | Результат | Учтено, s | Protected receipt SHA256 |
| --- | --- | ---: | --- |
| extension list без отдельного `/tmp` | exit255: невозможен IPC в read-only root | 1.6048002920579165 | `971861ffc0edbbd8ebbd57a2f03f9e522dce6e8c03a1c083391154594a5c58c8` |
| config save --db, writable disposable ИБ и tmpfs `/tmp` | exit0, CF18500297 bytes; хеш ИБ неизменён | 8.382368819089606 | `5c6ddacdb7f2abe4e87d099f825fe17764172366b28ce8671ea531c2e47fcc4a` |
| та же config save --db, файл ИБ mounted RO, locks/state/IPC в tmpfs | exit255: `Database file access error` | 1.8925854018889368 | `92f07a972d88084aac98c708efc24c7114d7d0115a7f756271766835b1875364` |

Receipts на HOME: `/home/roman/.local/issue97-config-rehearsal/<attemptId>/receipt.json`.
Attempt IDs соответственно `4ec4c4c4a0c54822b785ccefe8823f02`,
`c29d70208c464225a473fce935b1de53`, `efe759574735496a87487575981c5ce4`.
Команда успешной репетиции внутри отдельного worker:
`/opt/ibcmd/ibcmd infobase config save /work/current.cf --db --db-path=/work/ib --data=/work/state`.
Это **не команда для запуска против demo**. Успех writable disposable не доказывает
безопасность конкурентного открытия живой ИБ. RO-пробе предшествовала non-native
проверка mount flag `ro`, отказа открытия на запись и доступности своих lock-файлов.
Первый preflight ошибочно ожидал только EROFS вместо допустимого EACCES; исправлен
до native reservation, исходный отказ сохранён. После общего RO-отказа второй
native вызов не выполнялся. На этом этапе список расширений остался непроверенным.

Все три попытки сохранили исходный и disposable 1CD SHA256. Temporary workers,
копии и CF удалены; компактные receipts сохранены в защищённых каталогах.
CF SHA256 `c30267b4b9737a8165eb84b56c65cfb494d7b67dda8912ef670304af78968255`
не совпадает с исходным CF; это само по себе не доказывает изменение кода:
на этом этапе семантическое сравнение выгрузок не выполнено.

**Исторический ledger после retained rehearsal:** help2/3, exports7/12, session0/2,
native25.94996267114766/900s, STARTED0/reserved0; SHA256
`095d195ca4d5ebb8161a47f023902c334500502279ffa57625139774a87a7342`.
Предыдущие значения выше относятся к завершённой browser/engineering приёмке.
Operator native3 — только retained rehearsal; current-demo native/session0.

Результат retained rehearsal **PARTIAL**: чтение текущей конфигурации ещё не обеспечено.
Рассмотренный следующий вариант — согласованное окно обслуживания через существующий
`1c-jet-demo.service`, штатное завершение без принудительного вытеснения sessions,
консистентная копия на HOME и немедленное восстановление публикации; исследование
проводится на копии. Этот вариант требует отдельного решения владельца, поскольку
#97 прямо запрещает stop/restart demo. Последующее решение владельца и исполнение
этого окна зафиксированы ниже; общий запрет этим не снимается.

## Согласованная консистентная копия текущей ИБ

13 октября владелец разрешил окно обслуживания **сейчас** через существующий
`1c-jet-demo.service` и отдельно подтвердил отсутствие открытых пользовательских
сеансов. Это разовый допуск для получения копии, не постоянное право рестартов.
Обнаруженные открытые дескрипторы Apache сами по себе не были объявлены пользовательскими
сеансами; после подтверждения владельца использован штатный service lifecycle.

Полный unit (SHA256 `287c4033486292719be93603330c708f8a8fddc914fa6b121803dc779a56cccd`)
содержит не только Apache `graceful-stop`, но и `ExecStopPost=docker stop --timeout 10`;
`ExecStartPre` запускает тот же retained контейнер. Первая попытка ошибочно ожидала
running container после stop, отменила копирование и восстановила сервис за19.4206s.
Во второй попытке файл извлечён штатным `docker cp` из остановленного exact container;
до и после копирования Running=false/PID0. Затем service start в `finally`;
transient systemd job имел дополнительный start guard в ExecStopPost.
Окно с копированием заняло18.6035s. Systemd подтвердил оба штатных завершения сервиса.
Exit137 контейнера относится к завершаемому `sleep` PID1 в штатном StopPost;
это не результат запуска/принудительного завершения продуктового цикла #90.

Protected HOME copy:
`/home/roman/.local/issue97-current-copy/issue97-copy-9329e50f20f2/1Cv8.1CD`,
121946112 bytes, file0400/parent0700, SHA256
`a9ccb83b209f8e6e5f886c746d3f02aa7073a4f30b0034d81a1b5810f573cb50`.
Рядом `receipt.json`, SHA256 `bb6c4fe27fafd759d755c23b77baad5a95783d31a0c2a7a2f6a29fe9402ef90a`,
и `closure.json` с service events и хешем действующей ИБ после восстановления:
он совпал с копией. Хранить copy/CF/XML на HOME до завершения #90 и отдельного
согласованного cleanup с сохранением receipts/hashes; никакого
live writable IB mount для Hermes не создано. Старые originals/CF/snapshot сохранены.

Reference CID/image прежние; **новый** PID3591944, start
`2026-10-13T10:05:57.302519757Z`. VRD SHA256 прежний e5406c8e… .
Идентичность процесса не считается неизменной после разрешённого service lifecycle.
Maintenance native invocations0/product cycles0. Следующий раздел фиксирует
анализ копии; одно совпадение хеша файла ИБ не заменяет source admission.

## Связь текущей конфигурации с кодом запуска

На отдельных disposable дочерних копиях выполнены четыре согласованных с consumer
вызова ibcmd. Live ИБ не передавалась native worker. Каждый вызов имел отдельную
reservation30s в прежнем ledger; failed и cleanup включены в расход.

| Операция | Результат | Учтено, s |
| --- | --- | ---: |
| `infobase config save /output/current.cf --db --db-path=/work/ib --data=/work/state` | exit0; CF18500297 bytes | 7.43528599711135 |
| `infobase config extension list --db-path=/work/ib --data=/work/state` | exit0; stdout/stderr пусты, расширения не перечислены | 3.491612889105454 |
| `infobase config export /output/xml --file=/source/current.cf --threads=1` | exit255: отсутствует default DB context; XML0 | 1.1495287329889834 |
| та же export с `--db-path=/work/ib --data=/work/state` на disposable копии | exit0; 5100 файлов / 61772537 bytes | 14.70502273994498 |

CF SHA256 `c30267b4b9737a8165eb84b56c65cfb494d7b67dda8912ef670304af78968255`
совпадает с CF из retained rehearsal. Это не единственное доказательство:
полностью сравнены все пути и SHA256 XML/BSL текущей выгрузки с immutable snapshot.
**5096 совпадений, отсутствующих файлов0, изменённых3, добавленный1.**
Изменены `ConfigDumpInfo.xml` и Dashboard `Form.xml`/`Module.bsl`; добавлен
`Reports/Dashboard/Ext/ObjectModule.bsl`. В ConfigDumpInfo кроме configVersion
добавлена только запись ObjectModule Dashboard; других изменений metadata IDs нет.
Остальные файлы, включая Configuration.xml, ManagedApplication/SessionModule,
общие startup-модули, их metadata и overrides, совпадают побайтно.

Текущий Dashboard полностью прочитан: OnCreateAtServer вызывает получение
вчерашней сводки через SELECT ALLOWED и построение SpreadsheetDocument; запись
бизнес-объектов/config/log policy в этих изменениях не обнаружена. Candidate
по-прежнему выключает home forms. Проверка — source admission, а не исполнение
demo URL. Параметры, права и фактический штатный выход проверяет Hermes в #90,
без fallback к обычному startup, выдачи прав или обхода авторизации.

Protected HOME proof:
`/home/roman/.local/issue97-current-config/05b6b7cd54224065a15a098d39bf33d2/binding.json`,
SHA256 `55b07d1657c65df517f7f50c2fbc3895428bfe3b2d79c678c85e56c3d2312ed0`.
Содержит copy→native CF→XML chain, receipt hashes, полные Dashboard sources,
исчерпывающий список отличий и21 одинаковый startup source/metadata hash.
Компактная копия для обычного Hermes:
`/workspace/1c-harnest/.local/issue97-current-binding/operator-binding.json`.
Тяжёлые 1CD/CF/XML остаются HOME; временные workers/дочерние ИБ удалены.
Дополнительное retention: current-copy6 files/121958011 logical bytes,
current-config5116/80401890, rehearsal13/6601; вместе214740992 allocated bytes.
Это защищённые evidence, не новый постоянный доступ Hermes к живой ИБ.
После выгрузки service active, живой1CD SHA256 всё ещё равен quiesced copy,
VRD/CID/image прежние, новый PID/start подтверждены.

Текущий ledger: **help2/3, exports11/12, session0/2,
native52.73141303029843/900s, STARTED0/reserved0**; SHA256
`d43b7e247158e9c24d5b60b923e284a663068deeb4927833f0d204e936842ab9`.
Operator native7 (3 retained +4 current-copy); product cycles0.
Последняя попытка отдельно согласована consumer с явной оговоркой: оставшийся
один single-shot export не гарантирует полную проверку #90 «первое событие →
выборка → последующее событие → новая выборка; старая не меняется».
Два login/logout ещё не израсходованы; бюджет не расширен, #90 не закрывается.

После обслуживания Hermes лично подтвердил новые PID/start и прежние
engineering/browser/ЖР routes, authenticated HEAD200 и cleanup без новых
процессов; demo GET/e1cib/session0. Receipt
`/workspace/1c-harnest/.local/issue97-post-maintenance-20261013T100951Z-43512b28/receipt.json`,
SHA256 `cf40a635e7bdc166b6f1157761c749883dffe5bffaffeee6e6d89ae475e365da`.
Первый browser preflight остановился до HTTP из-за неверного ожидания consumer;
исправлен без изменения среды. Успешный authenticated HEAD был один.

## Итоговая consumer-приёмка

Hermes в ordinary WebUI session лично принял source/capability в10:45:43UTC:
**CONSUMER_SOURCE_CAPABILITY_ACCEPTED, startup binding gap CLOSED**, других
конкретных capability blockers не найдено. Свежий ЖР probe PASS;21 retained
startup hashes и4 export ledger rows сверены лично. Полный Dashboard прочитан,
BOM/CRLF восстановлены и все3 raw hashes воспроизведены. Дополнительно дочитан
server dispatch: optional CTL/OSL/UsersSaaS отсутствуют, default subscriptions
BeforeStartApplication=False. Это read-only приёмка, native/HTTP/session0.

Protected root:
`/workspace/1c-harnest/.local/issue97-consumer-binding-20261013T103456Z-51450fb5/`.
`acceptance.json` SHA256 `dec73238275a9c94e8c41825a5bc79e3d5d9c91ede270b781003db09717609c5`;
`source-admission-v3.md` SHA256 `6d89cd47f4e941bf06f80d211fb76242c9d53e9d254ef811e0c6882469c21882`;
`manifest.json` SHA256 `bef263e60de86fc043ebbc4828070013225e22deab02e75934e8cd0eaeb72d26`.
HOME live==copy и полный tree comparison — проверенные operator receipts,
не выдаются за личное чтение consumer живой ИБ. Историческая v2 сохранена.

Обязательные способности #97 и ordinary post-cleanup приняты. Два разрешённых
bounded цикла выполняет #90: фактические parameter/rights/slot/logout outcomes
здесь NOT_RUN. Если config/extensions изменятся, повторно сверить затронутый
код с этой точной identity до переноса вывода. Ни полный #90 PASS, ни бессрочная
неизменность demo, ни merge/release этим результатом не объявляются.
