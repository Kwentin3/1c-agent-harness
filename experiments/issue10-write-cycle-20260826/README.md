# Issue #10 — frozen evidence package

Доказательство вертикального среза «изменить → нативно загрузить → доказать новое поведение»
на конфигурации Jet (issue #10). Прогон выполнен **заново, изолированно**, 2026-08-26, в новом
уникальном каталоге `.local/runs/issue10-write-cycle-final-20260826T173251`.

Это **санитизированный frozen evidence**: никаких CF, snapshot, информационных баз, больших raw
логов, секретов или приватных абсолютных путей. Приватные пути заменены на `<RUN_DIR>`.

## Содержимое

| Файл | Что это |
|---|---|
| `task-contract.json` | Frozen контракт: задача, locators, безопасные границы, ожидаемое поведение, immutable identities |
| `production-patch.diff` | Минимальный production patch: `StringToNumber` — **+4, −0** (две строки `StrReplace` + комментарий) |
| `instrumentation.diff` | Тестовая instrumentation: probe в `ManagedApplicationModule` — **+35, −0** |
| `full-work-copy.diff` | Полный diff экспериментальной work copy против snapshot (== сумма двух выше) |
| `evidence/green-receipt.txt` | Receipt изменённой конфигурации |
| `evidence/red-receipt.txt` | Receipt исходной конфигурации |
| `native-results.md` | `DumpResult` и хвосты логов `CREATEINFOBASE` / `DESIGNER` для каждого шага |
| `package-manifest.json` | SHA-256 всех артефактов пакета + immutable source identities |

## RED / GREEN (каждый case: `value###type`)

| Case | RED (исходная) | GREEN (изменённая) |
|---|---|---|
| `tab###` | `""###Undefined` | `1234###Number` |
| `nbsp###` | `""###Undefined` | `1234###Number` |
| `invalid###` | `""###Undefined` | `""###Undefined` |
| `decimal###` | `1234.56###Number` | `1234.56###Number` |
| `space###` | `567###Number` | `567###Number` |

`Undefined` кодируется **типом**, а не пустой строкой: пустая строка и `Undefined` различимы.
Проверка требует точное значение И тип для каждого из пяти cases, полный набор labels,
отсутствие дубликатов и лишних строк (см. `tests/test_issue10_evidence.py`).

## Как воспроизвести прогон с нуля

Prerequisites: стенд из `docs/lab.md` (платформа 1С учебная 8.5.1.1150, libs, fontconfig,
`xvfb-run`, `xkbcomp`), официальный Jet fixture `.cf` (hash `5694f9e4bd…`) и развёрнутый
immutable snapshot `.local/runs/training-jet-review-final/snapshot` + `snapshot.manifest`
(identity `70972b5e…`).

Шаги (все пути — абсолютные; `<RUN_DIR>` — новый уникальный каталог, который не должен
существовать до прогона):

```bash
RUN_DIR=.local/runs/issue10-write-cycle-<timestamp>          # уникальный, не существующий!
V=.local/platform/1cv8t/x86_64/8.5.1.1150
L=.local/platform/libs
export PATH="$L/usr/bin:$PATH"
export LD_LIBRARY_PATH="$V:$L/usr/lib/x86_64-linux-gnu"
export FONTCONFIG_FILE="$(pwd)/.local/platform/fonts.conf"
export HOME="$PWD/$RUN_DIR/home" TMPDIR="$PWD/$RUN_DIR/tmp"
export XDG_CACHE_HOME="$HOME/xdg-cache" XDG_CONFIG_HOME="$HOME/xdg-config" XDG_DATA_HOME="$HOME/xdg-data"
XRUN="$L/usr/bin/xvfb-run -a -s '-screen 0 1280x1024x8 -nolisten tcp'"
mkdir -p "$PWD/$RUN_DIR"/{logs,evidence,home,tmp,img,img-red}
```

1. **Проверка границ.** source CF, snapshot, manifest и platform лежат ВНЕ `$RUN_DIR`
   (см. `task-contract.json`). Нарушение — стоп.
2. **Копии работы.** `cp -r snapshot -> $RUN_DIR/img/files` (GREEN) и `-> $RUN_DIR/img-red/files`
   (RED); каждая — полная копия 5099 файлов, затем `chmod` только внутри копий.
3. **Production patch (GREEN).** В `img/files/CommonModules/StringFunctionsClientServer/Ext/Module.bsl`
   после строки `Value  = StrReplace(Value, " ", "");` в `StringToNumber` вставить 2 строки
   `StrReplace(Value, Chars.Tab, "")` и `StrReplace(Value, Chars.NBSp, "")` (см.
   `production-patch.diff`). В `img-red` НЕ патчить.
4. **Instrumentation.** В обе копии `Ext/ManagedApplicationModule.bsl` добавить вызов
   `Issue10WriteRuntimeReceipt(); Return;` в `OnStart` и процедуру probe (см.
   `instrumentation.diff`; путь receipt — `$RUN_DIR/evidence/<variant>-receipt.txt`).
5. **Создать ИБ** (для GREEN и RED отдельно, каждый файл `*.result` не должен существовать
   заранее):
   ```bash
   $XRUN $V/1cv8t CREATEINFOBASE "File=$PWD/$RUN_DIR/instr-ib" /DisableStartupDialogs /DisableStartupMessages /Out "$PWD/$RUN_DIR/logs/green-create.log" /DumpResult "$PWD/$RUN_DIR/logs/green-create.result"
   ```
   Проверить `DumpResult == 0`.
6. **Нативная загрузка** (на шаге используется родной `DESIGNER`):
   ```bash
   $XRUN $V/1cv8t DESIGNER /F "$PWD/$RUN_DIR/instr-ib" /LoadConfigFromFiles "$PWD/$RUN_DIR/img/files" /UpdateDBCfg /DisableStartupDialogs /DisableStartupMessages /Out "$PWD/$RUN_DIR/logs/green-load.log" /DumpResult "$PWD/$RUN_DIR/logs/green-load.result"
   ```
   Проверить `DumpResult == 0` и строку `Configuration successfully updated` в логе.
   Повторить 5–6 для RED (`red-ib`, `img-red/files`).
7. **Runtime.** Удалить старый receipt (не должен существовать), затем:
   ```bash
   $XRUN $V/1cv8t ENTERPRISE /F "$PWD/$RUN_DIR/instr-ib" /DisableStartupDialogs /DisableStartupMessages /DisplayManager "none" /Out "$PWD/$RUN_DIR/logs/green-run.log" &
   PID=$!
   # ждать появления receipt (максимум ~180 c), затем завершить процесс-группу:
   kill -KILL -$PID 2>/dev/null || kill -KILL $PID
   ```
   Повторить для RED. Receipt читать только после завершения записи (файл существует
   и непуст).
8. **Проверка.** Каждый receipt: ровно 5 строк `label###value###type`; значения и типы
   совпадают с таблицей выше (см. `tests/test_issue10_evidence.py`). Immutable source:
   source CF hash `5694f9e4bd…`, manifest identity `70972b5e…`, snapshot 5099/5099 без
   missing/mismatch/extra/symlink.

## Проверка пакета

```bash
python3 -m unittest tests.test_issue10_evidence -v
```

Тесты fail-closed: отклоняют изменённые/подделанные receipt, неверную статистику diff,
приватные пути и несовпадение immutable identities.
