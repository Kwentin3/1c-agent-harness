# Домашний engineering access (#97)

Дата: 2026-10-13. Кандидат доступа, без merge/release. Продуктовая приёмка #90
остаётся отдельной. Источник engineering/native кода: `bd40827a7e95bba9d08ed03d430559aca089c953`;
это потомок PR #95 (`0dbfa1c0cd9f61e547e95d4aef3b2d28531ad39c`).

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
но безопасный current-demo startup admission пока не доказан.
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
и другие hooks. Retained source не является свежим dump текущей конфигурации;
актуальная готовность startup и права пользователя ИБ не установлены.
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
обязательным no-business-write gate. Остаётся доказать current compiled-config/
extensions binding к проверенному retained source и безопасные server hooks;
HEAD/VRD binding сами по себе этого не подтверждают.
Владелец подтвердил: после HTTPauth сразу открывается demo, отдельной формы
1С нет. Дополнительный IB password не требуется; это не доказательство
административных прав или отключения startup updates.
Business-write-free startup и safe login/logout пока NOT_PROVEN;
продуктовые cycles NOT_RUN. При занятом/заблокированном slot не повторять
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
Canonical ledger теперь help2, exports4, session0, native14.0702081581112/900s,
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
Статус **PARTIAL / ORDINARY_ENGINEERING_RUNTIME_AND_POST_CLEANUP_ACCEPTED**:
остаётся current-demo safe-session capability gap. Два продуктовых login/logout
и fresh-event acceptance #90 не запускались; source candidate не merged/released.

Личная [final browser/post-init приёмка Hermes](https://github.com/Kwentin3/1c-agent-harness/issues/97#issuecomment-6142147442):
PASS, включая native init orphan adoption/reaping и повтор engineering/ЖР/diagnostics/
registered retained ТЖ после cutoff. Protected `final-acceptance-v2.json` SHA256
`6f4b59f76213cba9fd8ed1c4d3f70215f1f3979e160377dbbfb44faaad2d0597`;
`manifest-v2.json` SHA256 `d12c627aea7f53b638bdab099df5b565f6813ace3fd1f131ea320126acdfb897`,
102 files/390409 logical bytes. V2 исправляет ошибочный UI initialization gate;
source-admission-v2.md SHA256 `53fcab69e032ad468ed3a8345900b4254e7ca41f7983ed741e8d32bfee79b9a8`.
Полный #97 PARTIAL: current compiled configuration/active extensions binding
к проверенному retained source ещё NOT_PROVEN. Дополнительный IB password
не требуется; два предусмотренных #90 cycles остаются0/2.
