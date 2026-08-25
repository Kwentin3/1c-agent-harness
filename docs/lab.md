# Нативная лаборатория 1С под Linux

Статус проверки: **25 августа 2026 года**. Документ фиксирует результат этапа 0 и минимальный способ повторить нативную полную выгрузку в уже подготовленном Hermes Workspace. Это не универсальный установщик и не security boundary для недоверенных процессов с тем же uid.

## Проверенный результат

- Hermes Workspace и Git-корень: `/workspace/1c-agent-harness`.
- Контейнер: Debian 13 (trixie), `x86_64`, пользователь `hermeswebui` (uid 1024).
- Платформа: официальная **«1С:Предприятие 8.5, учебная версия 8.5.1.1150»**, Linux 64-bit.
- Исполняемый файл: `.local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t`.
- Режим: файловая ИБ, пакетный `DESIGNER`, Xvfb только для инициализации GTK; управления окнами нет.
- Fixture: официальный release asset `1Ci-Company/Jet` — `v1.0.3.1-tr/1.0.3.1.cf`.
- Нативная операция: полная `DESIGNER /DumpConfigToFiles -Format Hierarchical` в новый пустой каталог, без `-update`, `-force` или `-listFile`.
- Результат: 5 099 файлов, включая 1 258 BSL-файлов, `Configuration.xml`, `ConfigDumpInfo.xml` и метаданные нескольких типов.
- Две независимо созданные ИБ, дополнительный ручной прогон штатными командами и выгрузка через `cc-1c-skills` дали одинаковый набор путей и SHA-256 содержимого каждого файла.
- Идентификатор проверенного содержимого: `sha256:70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`.
- Каталог стабильного handoff-снимка создан `2026-08-25T17:09:01.543872806Z`; проверка и запись `snapshot.json` завершены `2026-08-25T17:09:12.073226Z`. Shell exit code каждой из трёх платформенных команд — `0`, содержимое каждого `/DumpResult` — `0`.

`Полная` здесь означает штатный полный режим выгрузки 1С и подтверждённый ожидаемый состав smoke-конфигурации. Это не утверждение, что простой файловый эвристический тест способен доказать полноту произвольной конфигурации.

## Происхождение

### Платформа

Официальная страница:

<https://online.1c.ru/catalog/programs/program/36179915/>

Получение дистрибутива требует персонально заполнить анкету и принять лицензионное соглашение. Это единственный интерактивный precondition **получения платформы**; временная подписанная ссылка не сохраняется.

| Артефакт | SHA-256 |
|---|---|
| `setup-training-8.5.1.1150-x86_64.run` | `396b7065b9efb6272093f1bda5eab647081a13d9ccbb4c5cfb0e711346d5af28` |

Учебная редакция не требует программной лицензии или аппаратного ключа. Её ограничения подходят лаборатории: обучение и тестирование, файловая ИБ, один сеанс, без клиент-сервера, хранилища конфигурации и производственного учёта.

### Smoke-fixture

Официальный release:

<https://github.com/1Ci-Company/Jet/releases/tag/v1.0.3.1-tr>

Прямой asset:

<https://github.com/1Ci-Company/Jet/releases/download/v1.0.3.1-tr/1.0.3.1.cf>

| Артефакт | SHA-256 |
|---|---|
| `Jet-1.0.3.1-tr.cf` | `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a` |

Перед каждым прогоном fixture копировался в новый run-каталог. SHA-256 исходника и рабочей копии проверялся до и после операций; во всех проверенных прогонах он остался одинаковым. Эта проверка доказывает равенство наблюдаемого содержимого в контрольных точках, но не является защитой от вредоносного процесса с тем же uid.

## Локальная раскладка

Все закрытые и машинно-зависимые данные находятся в игнорируемом `.local/`:

```text
.local/
├── dist/                         # официальный installer и fixture
├── platform/
│   ├── 1cv8t/                    # учебная платформа
│   └── libs/                     # локальный GUI/Xvfb runtime
├── tools/
│   ├── cc-1c-skills/             # внешний checkout
│   └── cc-1c-skills-venv/        # изолированный Python runtime
└── runs/
    └── training-jet-review-final/
        ├── input/                # рабочая копия CF
        ├── ib/                   # отдельная файловая ИБ
        ├── snapshot/             # точка входа этапа 1
        ├── logs/                 # /Out, /DumpResult и Xvfb logs
        └── snapshot.manifest     # SHA-256 каждого файла
```

Платформа, installer, fixture, база, checkout и снимки не попадают в Git.

Точка входа этапа 1 и связанные доказательства:

```text
.local/runs/training-jet-review-final/snapshot/           # read-only рабочий снимок
.local/runs/training-jet-review-final/snapshot.manifest   # 5 099 SHA-256 записей
.local/runs/training-jet-review-final/snapshot.json       # версия, время, счётчики и content ID
.local/runs/training-jet-review-final/logs/               # /Out, /DumpResult, Xvfb
```

## Fail-closed smoke после новой сессии

Чистая подготовка окружения описана отдельно в [bootstrap-рецепте](lab-bootstrap.md). После его `LAB_READY` откройте Bash, задайте **новый** `RUN` и вставьте следующий блок целиком в тот же shell. Он не продолжает работу после ошибки, до `/LoadCfg` проверяет fixture, запрещает повторное использование run-каталога и утверждает все критерии фиксированного Jet smoke.

```bash
set -euo pipefail
ROOT=/workspace/1c-agent-harness
V="$ROOT/.local/platform/1cv8t/x86_64/8.5.1.1150"
L="$ROOT/.local/platform/libs"
RUN="$ROOT/.local/runs/manual-check-01"  # каждый запуск — новое имя
SOURCE="$ROOT/.local/dist/Jet-1.0.3.1-tr.cf"
FIXTURE_SHA=5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a
CONTENT_ID=70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691

test -f "$SOURCE"
test ! -L "$SOURCE"
printf '%s  %s\n' "$FIXTURE_SHA" "$SOURCE" | sha256sum -c -
if [[ -e "$RUN" || -L "$RUN" ]]; then
  printf 'Refusing existing RUN: %s\n' "$RUN" >&2
  exit 1
fi
mkdir "$RUN"
mkdir -p "$RUN"/{input,ib,snapshot,logs,home,tmp,xdg-cache,xdg-config,xdg-data}
cp -- "$SOURCE" "$RUN/input/Jet-1.0.3.1-tr.cf"
printf '%s  %s\n' "$FIXTURE_SHA" "$RUN/input/Jet-1.0.3.1-tr.cf" | sha256sum -c -

export PATH="$L/usr/bin:$PATH"
export LD_LIBRARY_PATH="$V:$L/usr/lib/x86_64-linux-gnu"
export FONTCONFIG_FILE="$ROOT/.local/platform/fonts.conf"
export HOME="$RUN/home" TMPDIR="$RUN/tmp"
export XDG_CACHE_HOME="$RUN/xdg-cache" XDG_CONFIG_HOME="$RUN/xdg-config" XDG_DATA_HOME="$RUN/xdg-data"

"$L/usr/bin/xvfb-run" -a -e "$RUN/logs/create-xvfb.log" \
  "$V/1cv8t" CREATEINFOBASE "File=$RUN/ib" \
  /DisableStartupDialogs /DisableStartupMessages \
  /Out "$RUN/logs/create.log" /DumpResult "$RUN/logs/create.result"
CREATE_EXIT=$?

"$L/usr/bin/xvfb-run" -a -e "$RUN/logs/load-xvfb.log" \
  "$V/1cv8t" DESIGNER /F "$RUN/ib" \
  /DisableStartupDialogs /DisableStartupMessages \
  /LoadCfg "$RUN/input/Jet-1.0.3.1-tr.cf" \
  /Out "$RUN/logs/load.log" /DumpResult "$RUN/logs/load.result"
LOAD_EXIT=$?

"$L/usr/bin/xvfb-run" -a -e "$RUN/logs/dump-xvfb.log" \
  "$V/1cv8t" DESIGNER /F "$RUN/ib" \
  /DisableStartupDialogs /DisableStartupMessages \
  /DumpConfigToFiles "$RUN/snapshot" -Format Hierarchical \
  /Out "$RUN/logs/dump.log" /DumpResult "$RUN/logs/dump.result"
DUMP_EXIT=$?

[[ "$CREATE_EXIT" == 0 && "$LOAD_EXIT" == 0 && "$DUMP_EXIT" == 0 ]]
python3 - "$RUN" <<'PY'
from pathlib import Path
import hashlib
import sys

run = Path(sys.argv[1])
for name in ('create', 'load', 'dump'):
    value = (run / 'logs' / f'{name}.result').read_text(encoding='utf-8-sig').strip()
    if value != '0':
        raise SystemExit(f'{name} DumpResult={value!r}, expected 0')

root = run / 'snapshot'
if not (root / 'Configuration.xml').is_file() or not (root / 'ConfigDumpInfo.xml').is_file():
    raise SystemExit('required snapshot XML is missing')
files = sorted(path for path in root.rglob('*') if path.is_file())
if len(files) != 5099:
    raise SystemExit(f'file_count={len(files)}, expected 5099')
bsl = sum(path.suffix.lower() == '.bsl' for path in files)
if bsl != 1258:
    raise SystemExit(f'bsl_count={bsl}, expected 1258')
with (run / 'snapshot.manifest').open('w', encoding='utf-8', newline='\n') as output:
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        output.write(f'{digest}  {path.relative_to(root).as_posix()}\n')
PY

printf '%s  %s\n' "$CONTENT_ID" "$RUN/snapshot.manifest" | sha256sum -c -
printf '%s  %s\n' "$FIXTURE_SHA" "$SOURCE" | sha256sum -c -
printf '%s  %s\n' "$FIXTURE_SHA" "$RUN/input/Jet-1.0.3.1-tr.cf" | sha256sum -c -
chmod -R a-w -- "$RUN/snapshot" "$RUN/snapshot.manifest"
echo "LAB_SMOKE_OK run=$RUN"
```

`CONTENT_ID` — SHA-256 UTF-8 manifest из 5 099 строк, отсортированных стандартным порядком Python `Path`; строка имеет формат `<sha256><два пробела><relative POSIX path><LF>`, включая финальный LF.

Этот путь был повторно выполнен буквально 25 августа 2026 года в run `manual-docs-check`; набор 5 099 файлов и их SHA-256 совпал с эталонным снимком (`only_actual=0`, `only_expected=0`, `changed=0`).

## Одноразовая подготовка окружения

Полный рецепт из пустого Workspace — installer, relocation, зафиксированные Debian-пакеты, `fonts.conf`, XKB и readiness gate — находится в [docs/lab-bootstrap.md](lab-bootstrap.md). Административные команды рассчитаны на чистый доверенный single-user контейнер и должны выполняться без конкурирующих процессов workspace uid.

Фактическое состояние текущего контейнера отличается от предлагаемого чистого пути через APT:

- `/usr/bin/xkbcomp` был разово скопирован из распакованного Debian-пакета; SHA-256 `eca6986af7d15277394b8476b8ad85229ee1a1a879d43d2a526f106af3761550`;
- `/usr/share/X11/xkb` также скопирован из локального package extraction;
- эти два назначения не зарегистрированы как установленные пакеты в dpkg текущего контейнера;
- `/tmp/.X11-unix` имеет режим `01777`, но в текущем контейнере принадлежит `hermeswebui`; clean bootstrap нормализует его до стандартного владельца `root`;
- `ldd` проходит без `not found` только с `LD_LIBRARY_PATH`, указанным в runbook выше.

## Проверка `cc-1c-skills`

Внешняя зависимость использовалась отдельным checkout, без копирования кода и глобальной активации:

- repository: <https://github.com/Nikolay-Shirokov/cc-1c-skills>;
- commit: `7409bacd47846dc96b66a9f943fa990224abbc6e`;
- license: MIT;
- `lxml==6.1.2` установлен только в `.local/tools/cc-1c-skills-venv/`.

Проверено:

- `db-dump-xml.py -Mode Full -Format Hierarchical` создал 5 099 файлов и 1 258 BSL-файлов;
- набор путей и SHA-256 содержимого совпал с прямой нативной выгрузкой;
- `cf-info.py` прочитал `Configuration.xml`: `JetTr`, vendor `1Ci (1C International)`, версия `1.0.3.1`, compatibility `Version8_3_24`, 1 662 объекта;
- эти значения отдельно сопоставлены с исходным XML.

Вывод: кандидат уменьшает ручную оркестрацию и пригоден как внешняя зависимость. Нативные команды платформы остаются независимым источником истины; собственного wrapper в репозиторий не добавлено.

## Ограничения

1. `/workspace` находится в writable layer Docker overlay. Обычный stop/start текущего контейнера сохраняет данные, но пересоздание контейнера без bind mount/volume — нет.
2. Учебная редакция предназначена для обучения и тестирования, не для production или реального учёта.
3. `read-only snapshot` в этом этапе означает дисциплину дальнейшего использования и снятые Unix write bits у проверенного снимка, а не filesystem immutability: владелец может вернуть права записи.
4. Runbook рассчитан на доверенный single-user Workspace и не защищает от процессов с тем же uid, которые одновременно подменяют пути или файлы.
5. Xvfb нужен только для GTK-инициализации пакетного Designer; GUI не является интерфейсом агента.
