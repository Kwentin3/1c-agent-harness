# Домашний engineering access (#97)

Дата: 2026-10-13. Кандидат доступа, без merge/release. Продуктовая приёмка #90
остаётся отдельной. Источник установленного кода: `bd40827a7e95bba9d08ed03d430559aca089c953`;
это потомок PR #95 (`0dbfa1c0cd9f61e547e95d4aef3b2d28531ad39c`).

## Владельцы и границы

| Смысл | Владелец / контракт | Потребитель |
|---|---|---|
| Команды, процессы, disposable ИБ | обычный Hermes, SSH shell UID/GID10001 в выделенном namespace | разрешённая продуктовая issue |
| Изоляция и lifecycle доступа | оператор; pinned forced command → точный container ID | engineering SSH |
| ЖР текущей demo | существующий #94, фиксированный probe/export JSON | reader #90 |
| Native budget и admission | существующий canonical ledger #90 | native caller |
| HTTP credentials | native Hermes Secrets активного профиля | проверка HTTP и разрешённый будущий клиент |

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

Engineering namespace не имеет сети и не предоставляет current-demo login.
Retained canonical snapshot находится в reference
`/srv/goal91-jet/.local/targets/jettr-1.0.3.1/snapshot`; его manifest совпал с
immutable pin выше. SessionModule вызывает `StandardSubsystemsServer.SessionParametersSetting`,
тот — `BeforeStartApplication` (line3727). Этот путь включает
`CorrectSharedUserHomePage` (line3906, `CommonSettingsStorage.Save`) и
`HandleCopiedSettingsQueue` (line4039, `SystemSettingsStorage.Save`).
ManagedApplicationModule вызывает BeforeStart/OnStart библиотеки;
`DisableSystemStartupLogic` в клиенте не отменяет server session handler
и требует прав Administration/DataAdministration (ServerCall line200).
Состояние условий этих записей в живой ИБ без запуска не доказано;
retained snapshot сам по себе не является свежим dump текущей конфигурации.
Business-write-free startup, текущие занятые sessions и safe login/logout
capability поэтому остаются NOT_PROVEN, продуктовые cycles NOT_RUN.
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
four journal files, native0. Unit current-journal7 и engineering5 PASS.
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
