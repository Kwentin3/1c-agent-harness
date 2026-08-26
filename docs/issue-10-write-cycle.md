# Issue #10 — цикл изменения и нативной проверки конфигурации 1С (R&D)

**Статус:** эксперимент выполнен и подтверждён; это R&D-отчёт, а не начало write-платформы.
Дата: 2026-08-26. Платформа: официальная учебная «1С:Предприятие 8.5, учебная версия 8.5.1.1150»,
Linux 64-bit. Конфигурация: официальный release asset `1Ci-Company/Jet` `v1.0.3.1-tr`.

Доказывается один горизонтальный срез:

> агент способен получить задачу → найти место изменения → внести минимальную правку →
> загрузить её в изолированную 1С → доказать новое поведение.

Не утверждается переносимость на другие конфигурации, metadata-объекты, старые платформы (#3),
другие агентные клиенты (#4) или production.

---

## 1. Выбранная задача и почему она достаточна

`StringFunctionsClientServer.StringToNumber` (`CommonModules/StringFunctionsClientServer/Ext/Module.bsl`)
преобразует строку в число без исключений. Она сворачивает только обычный пробел `" "` и не
обрабатывает непечатаемые разделители, появляющиеся при копировании чисел: табуляцию
(`Chars.Tab`) и неразрывный пробел (`Chars.NBSp`). Для `"1⇥234"` / `"1␣234"` она возвращает
`Undefined`.

**Фича:** принимать эти два разделителя при разборе числа, но по-прежнему отклонять нечисловой
текст (`12x3` → `Undefined`).

Достаточность: маленькая и локальная (одно место); наблюдаемое поведение «до/после»
(`Undefined` → `1234`); есть положительный, отрицательный и сохраняемый сценарии; не сводится к
константе; без GUI, внешних интеграций, production-данных и секретов.

## 2. Исходные locators

Локатор в **иммутабельном исходнике**
`CommonModules/StringFunctionsClientServer/Ext/Module.bsl`:

- комментарий контракта функции: 797–809;
- тело `Function StringToNumber(Val Value) Export`: 810–827.

В изменённой рабочей копии тело сдвинуто на +4 строки (810–832). Обе ссылки относятся к одному
коду; diff ниже приведён с контекстом по исходнику.

## 3. Honest tri-разделение diff

| Слой | Файл | Additions | Deletions |
|---|---|---|---|
| **Production patch (фича)** | `CommonModules/StringFunctionsClientServer/Ext/Module.bsl` | **+4** | −0 |
| **Test instrumentation (probe)** | `Ext/ManagedApplicationModule.bsl` | **+35** | −0 |
| **Итого: полный diff work copy** | 2 файла | +39 | −0 |

Точные файлы diff: [`production-patch.diff`](../experiments/issue10-write-cycle-20260826/production-patch.diff),
[`instrumentation.diff`](../experiments/issue10-write-cycle-20260826/instrumentation.diff),
[`full-work-copy.diff`](../experiments/issue10-write-cycle-20260826/full-work-copy.diff).

**Production patch** — ровно 4 строки (2 комментария + 2 `StrReplace`):

```text
@@ Function StringToNumber(Val Value) Export @@
	Value  = StrReplace(Value, " ", "");
+	// Digits are commonly separated by tab or a non-breaking space in copied
+	// text. Strip those as well, not just the regular space.
+	Value  = StrReplace(Value, Chars.Tab, "");
+	Value  = StrReplace(Value, Chars.NBSp, "");
```

`StringToNumber` сам по-прежнему не выполняет ввода-вывода (только `StrReplace` +
`New TypeDescription` + `AdjustValue` + `Return ?(...)`). Всё, что пишет файл — тестовый probe
(`ManagedApplicationModule`), а не реализация.

## 4. Runtime probe (тестовая instrumentation)

Probe добавляется **только в throwaway work copy**. Вызов в `OnStart` и процедура:

```bsl
// Probe-only (test harness, NOT part of the implementation)
Procedure Issue10WriteRuntimeReceipt()
	Receipt = New TextWriter("<RECEIPT_PATH>", TextEncoding.UTF8);
	WriteProbeCase(Receipt, "tab",     StringFunctionsClientServer.StringToNumber("1" + Chars.Tab  + "234"));
	WriteProbeCase(Receipt, "nbsp",    StringFunctionsClientServer.StringToNumber("1" + Chars.NBSp + "234"));
	WriteProbeCase(Receipt, "invalid", StringFunctionsClientServer.StringToNumber("12x3"));
	WriteProbeCase(Receipt, "decimal", StringFunctionsClientServer.StringToNumber("1234.56"));
	WriteProbeCase(Receipt, "space",   StringFunctionsClientServer.StringToNumber(" 567 "));
	Receipt.Close();
EndProcedure

Procedure WriteProbeCase(Receipt, Label, Result)
	TypeMarker = String(TypeOf(Result));
	If TypeMarker = "Number" Then
		ValueText = String(Result);
	Else
		ValueText = "";
	EndIf;
	Receipt.Write(Label + "###" + ValueText + "###" + TypeMarker + Chars.LF);
EndProcedure
```

Каждая строка receipt — `label###value###type`. `Undefined` кодируется **типом** (`###Undefined`),
а не пустой строкой: пустая строка, `Undefined` и ошибка выполнения различимы. В `OnStart`
добавляется `Issue10WriteRuntimeReceipt(); Return;` — это исполняет только probe, полный
жизненный цикл приложения в этом цикле не доказан (честная узость, см. §10).

## 5. Границы

| Роль | Путь (относительно repo root) |
|---|---|
| immutable source CF | `.local/dist/Jet-1.0.3.1-tr.cf` |
| immutable source snapshot | `.local/runs/training-jet-review-final/snapshot` |
| immutable manifest | `.local/runs/training-jet-review-final/snapshot.manifest` |
| writable work copy (GREEN) | `.local/runs/<run-id>/img` |
| writable work copy (RED) | `.local/runs/<run-id>/img-red` |
| disposable test ИБ | `.local/runs/<run-id>/instr-ib`, `red-ib` |
| evidence | `.local/runs/<run-id>/evidence` |

`<run-id>` — уникальный каталог, созданный заново для этого прогона; его несуществование
проверяется fail-closed (см. §6). source/snapshot/manifest/platform лежат **вне** run-каталога.
Все записи — только в work copy и disposable ИБ.

## 6. Исполнимый runbook (буквально повторяет прогон)

Следующий блок — законченный исполнимый скрипт. Выполняется из корня репозитория после
развёртывания стенда по `docs/lab.md` / `docs/lab-bootstrap.md` (платформа, libs, fontconfig,
Xvfb, xkbcomp) и восстановления immutable snapshot (см. §11).

```bash
#!/usr/bin/env bash
set -euo pipefail

# --- переменные (все абсолютные) -------------------------------------------
ROOT=$(pwd)                                                          # корень репозитория
V=$ROOT/.local/platform/1cv8t/x86_64/8.5.1.1150
L=$ROOT/.local/platform/libs
PKG=$ROOT/experiments/issue10-write-cycle-20260826
SNAP=$ROOT/.local/runs/training-jet-review-final/snapshot
MANIFEST=$SNAP/../snapshot.manifest
CF=$ROOT/.local/dist/Jet-1.0.3.1-tr.cf

CF_SHA=5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a
MAN_SHA=70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691

# --- строгие проверки (fail-closed) -------------------------------------------
# Receipt: байт-в-байт равен frozen expected из замороженного пакета
# (покрывает: nonsense/duplicate labels, unknown/missing labels, лишние и пустые строки)
receipt_ok() {
  local got=$1 expected=$2
  [ -s "$got" ] || return 1
  cmp -s "$got" "$expected" || return 1
}
# DumpResult: весь нормализованный файл (BOM, CR, LF удалены) ровно "0"
result_zero() {
  local f=$1
  [ "$(sed '1s/^\xEF\xBB\xBF//' "$f" | tr -d '\r\n')" = "0" ] || return 1
}
# Snapshot closure: missing/mismatch/extra/symlink/недопустимые типы — стоп
snapshot_verify() {
  python3 - "$SNAP" "$MANIFEST" <<'PY'
import hashlib, sys
from pathlib import Path
snap = Path(sys.argv[1]); manifest = Path(sys.argv[2])
entries = {}
for line in manifest.read_text(encoding='utf-8-sig').splitlines():
    if line.strip():
        digest, rel = line.split(maxsplit=1)
        entries[rel] = digest
missing, mismatch, extra, symlinks, nonregular = [], [], [], [], []
for p in snap.rglob('*'):
    if p.is_symlink():
        symlinks.append(str(p.relative_to(snap))); continue
    if p.is_dir():
        continue
    if not p.is_file():
        nonregular.append(str(p.relative_to(snap))); continue
    rel = p.relative_to(snap).as_posix()
    if rel not in entries:
        extra.append(rel); continue
    if hashlib.sha256(p.read_bytes()).hexdigest() != entries[rel]:
        mismatch.append(rel)
missing = [r for r in entries if not (snap / r).is_file() or (snap / r).is_symlink()]
problems = (missing, mismatch, extra, symlinks, nonregular)
if any(problems):
    print("SNAPSHOT_FAIL missing=%d mismatch=%d extra=%d symlinks=%d nonregular=%d"
          % tuple(len(x) for x in problems))
    sys.exit(1)
PY
}

# --- pre-flight: immutable identities + closure + fail-closed run-root --------
[ "$(sha256sum "$CF" | cut -d' ' -f1)" = "$CF_SHA" ]        || { echo "FAIL: source CF hash"; exit 1; }
[ "$(sha256sum "$MANIFEST" | cut -d' ' -f1)" = "$MAN_SHA" ] || { echo "FAIL: manifest identity"; exit 1; }
snapshot_verify || { echo "FAIL: snapshot closure (pre)"; exit 1; }

RUN_DIR=$ROOT/.local/runs/issue10-write-cycle-$(date -u +%Y%m%dT%H%M%S)
[ ! -e "$RUN_DIR" ] && mkdir -p "$RUN_DIR" || { echo "FAIL: run dir already exists: $RUN_DIR"; exit 1; }
mkdir -p "$RUN_DIR"/{logs,evidence,home,tmp}

export PATH="$L/usr/bin:$PATH"
export LD_LIBRARY_PATH="$V:$L/usr/lib/x86_64-linux-gnu"
export FONTCONFIG_FILE="$ROOT/.local/platform/fonts.conf"
export HOME="$RUN_DIR/home" TMPDIR="$RUN_DIR/tmp"
export XDG_CACHE_HOME="$HOME/xdg-cache" XDG_CONFIG_HOME="$HOME/xdg-config" XDG_DATA_HOME="$HOME/xdg-data"

XVFB=(xvfb-run -a -s "-screen 0 1280x1024x8 -nolisten tcp")

# --- work copies: физически отделённые копии snapshot ------------------------
cp -R "$SNAP/." "$RUN_DIR/img/"          # GREEN
cp -R "$SNAP/." "$RUN_DIR/img-red/"      # RED
chmod -R u+w "$RUN_DIR/img" "$RUN_DIR/img-red"    # запись только в копиях

# git apply внутри worktree пропускает пути под .local/ (gitignored) — уводим
# GIT_DIR в пустой каталог, чтобы патчи применялись по cwd:
mkdir -p "$RUN_DIR/git-dummy"
export GIT_DIR="$RUN_DIR/git-dummy"

# GREEN: production patch + instrumentation, receipt path -> green-receipt.txt
( cd "$RUN_DIR/img" \
  && git apply -p1 "$PKG/production-patch.diff" \
  && git apply -p1 "$PKG/instrumentation.diff" \
  && sed -i "s#<RUN_DIR>/evidence/runtime-receipt.txt#$RUN_DIR/evidence/green-receipt.txt#" Ext/ManagedApplicationModule.bsl )

# RED: только instrumentation (без production patch), receipt path -> red-receipt.txt
( cd "$RUN_DIR/img-red" \
  && git apply -p1 "$PKG/instrumentation.diff" \
  && sed -i "s#<RUN_DIR>/evidence/runtime-receipt.txt#$RUN_DIR/evidence/red-receipt.txt#" Ext/ManagedApplicationModule.bsl )

# --- GREEN: создать ИБ, нативно загрузить, исполнить, остановить группу -------
"${XVFB[@]}" "$V/1cv8t" CREATEINFOBASE "File=$RUN_DIR/instr-ib" \
  /DisableStartupDialogs /DisableStartupMessages \
  /Out "$RUN_DIR/logs/green-create.log" /DumpResult "$RUN_DIR/logs/green-create.result"
result_zero "$RUN_DIR/logs/green-create.result" || { echo "FAIL: green-create DumpResult"; exit 1; }

"${XVFB[@]}" "$V/1cv8t" DESIGNER /F "$RUN_DIR/instr-ib" \
  /LoadConfigFromFiles "$RUN_DIR/img" /UpdateDBCfg \
  /DisableStartupDialogs /DisableStartupMessages \
  /Out "$RUN_DIR/logs/green-load.log" /DumpResult "$RUN_DIR/logs/green-load.result"
result_zero "$RUN_DIR/logs/green-load.result" || { echo "FAIL: green-load DumpResult"; exit 1; }
grep -q "Configuration successfully updated" "$RUN_DIR/logs/green-load.log" \
  || { echo "FAIL: green-load log missing success marker"; exit 1; }

setsid "${XVFB[@]}" "$V/1cv8t" ENTERPRISE /F "$RUN_DIR/instr-ib" \
  /DisableStartupDialogs /DisableStartupMessages /DisplayManager "none" \
  /Out "$RUN_DIR/logs/green-run.log" &
PID=$!
ok=0
for i in $(seq 1 180); do
  if receipt_ok "$RUN_DIR/evidence/green-receipt.txt" "$PKG/evidence/green-receipt.txt"; then
    sleep 2; h1=$(sha256sum "$RUN_DIR/evidence/green-receipt.txt" | cut -d' ' -f1)
    sleep 1; h2=$(sha256sum "$RUN_DIR/evidence/green-receipt.txt" | cut -d' ' -f1)
    if [ "$h1" = "$h2" ]; then ok=1; break; fi
  fi
  kill -0 "$PID" 2>/dev/null || { echo "FAIL: ENTERPRISE exited before valid receipt"; exit 1; }
  sleep 1
done
[ "$ok" = "1" ] || { echo "FAIL: no byte-exact green receipt in 180s"; kill -KILL -"$PID" 2>/dev/null || true; exit 1; }
kill -KILL -"$PID" 2>/dev/null || kill -KILL "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true

# --- RED: то же для исходной конфигурации ------------------------------------
"${XVFB[@]}" "$V/1cv8t" CREATEINFOBASE "File=$RUN_DIR/red-ib" \
  /DisableStartupDialogs /DisableStartupMessages \
  /Out "$RUN_DIR/logs/red-create.log" /DumpResult "$RUN_DIR/logs/red-create.result"
result_zero "$RUN_DIR/logs/red-create.result" || { echo "FAIL: red-create DumpResult"; exit 1; }

"${XVFB[@]}" "$V/1cv8t" DESIGNER /F "$RUN_DIR/red-ib" \
  /LoadConfigFromFiles "$RUN_DIR/img-red" /UpdateDBCfg \
  /DisableStartupDialogs /DisableStartupMessages \
  /Out "$RUN_DIR/logs/red-load.log" /DumpResult "$RUN_DIR/logs/red-load.result"
result_zero "$RUN_DIR/logs/red-load.result" || { echo "FAIL: red-load DumpResult"; exit 1; }
grep -q "Configuration successfully updated" "$RUN_DIR/logs/red-load.log" \
  || { echo "FAIL: red-load log missing success marker"; exit 1; }

setsid "${XVFB[@]}" "$V/1cv8t" ENTERPRISE /F "$RUN_DIR/red-ib" \
  /DisableStartupDialogs /DisableStartupMessages /DisplayManager "none" \
  /Out "$RUN_DIR/logs/red-run.log" &
PID=$!
ok=0
for i in $(seq 1 180); do
  if receipt_ok "$RUN_DIR/evidence/red-receipt.txt" "$PKG/evidence/red-receipt.txt"; then
    sleep 2; h1=$(sha256sum "$RUN_DIR/evidence/red-receipt.txt" | cut -d' ' -f1)
    sleep 1; h2=$(sha256sum "$RUN_DIR/evidence/red-receipt.txt" | cut -d' ' -f1)
    if [ "$h1" = "$h2" ]; then ok=1; break; fi
  fi
  kill -0 "$PID" 2>/dev/null || { echo "FAIL: ENTERPRISE exited before valid receipt"; exit 1; }
  sleep 1
done
[ "$ok" = "1" ] || { echo "FAIL: no byte-exact red receipt in 180s"; kill -KILL -"$PID" 2>/dev/null || true; exit 1; }
kill -KILL -"$PID" 2>/dev/null || kill -KILL "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true

# --- post-flight: immutable identities + closure + точные receipts ------------
[ "$(sha256sum "$CF" | cut -d' ' -f1)" = "$CF_SHA" ]        || { echo "FAIL: source CF changed"; exit 1; }
[ "$(sha256sum "$MANIFEST" | cut -d' ' -f1)" = "$MAN_SHA" ] || { echo "FAIL: manifest changed"; exit 1; }
snapshot_verify || { echo "FAIL: snapshot closure"; exit 1; }
receipt_ok "$RUN_DIR/evidence/green-receipt.txt" "$PKG/evidence/green-receipt.txt" || { echo "FAIL: green receipt mismatch"; exit 1; }
receipt_ok "$RUN_DIR/evidence/red-receipt.txt" "$PKG/evidence/red-receipt.txt"     || { echo "FAIL: red receipt mismatch"; exit 1; }

echo "RUN OK: $RUN_DIR"
echo "  all steps passed: DumpResult==0, load logs updated, receipts byte-exact, snapshot closure clean"
```

**Замечания к runbook:**

- `XVFB` — bash-массив; `"${XVFB[@]}"` сохраняет вложенные кавычки `-s "...-nolisten tcp"`,
  поэтому команда не распадается на восемь аргументов.
- `git apply` внутри git-worktree **скипает** пути под `.local/` (они в `.gitignore`);
  runbook уводит `GIT_DIR` в пустой каталог, чтобы патчи применялись к файлам по cwd
  (проверено: без этого патч молча не применяется и probe не попадает в конфигурацию).
- Несуществование `RUN_DIR` проверяется до `mkdir` (fail-closed, race не рассматриваем: защита
  от злонамеренного процесса с тем же uid — честно оставленное ограничение).
- ENTERPRISE запускается через `setsid` — PID становится лидером собственной process group,
  и `kill -KILL -$PID` останавливает всю группу (включая `1cv8t`-ребёнка внутри `xvfb-run`),
  а не только wrapper.
- Ожидание receipt — байт-точное: `cmp` файла текущего run с frozen expected из пакета
  (`$PKG/evidence/*-receipt.txt`), плюс стабильность (хэш не меняется между двумя замерами
  через 2 с и 1 с), чтобы исключить завершение ENTERPRISE во время записи. `cmp` покрывает
  nonsense/duplicate/unknown/missing labels, лишние и пустые строки.
- `DumpResult` проверяется целиком: нормализованный файл (BOM/CR/LF удалены) должен быть
  ровно `"0"` — значения `10` или `error0` отклоняются.
- Оба load-лога дополнительно проверяются на `Configuration successfully updated`.
- Pre/post snapshot-проверка — closure: missing/mismatch/extra/symlink/недопустимые типы
  файлов приводят к `SNAPSHOT_FAIL` и стопу; `RUN OK` печатается только после всех проверок.

**Результаты этого прогона** — `RUN_DIR = .local/runs/issue10-write-cycle-20260826T190503`
(выполнен буквально этим runbook'ом из корня репозитория; receipts нового прогона
байт-в-байт равны receipts замороженного пакета):

| Шаг | `/DumpResult` | Лог |
|---|---|---|
| `green-create` | `0` | `Creation of infobase … completed successfully` |
| `green-load` | `0` | `Configuration successfully updated` |
| `red-create` | `0` | `Creation of infobase … completed successfully` |
| `red-load` | `0` | `Configuration successfully updated` |

Экстракты сохранены санитизированно в
[`native-results.md`](../experiments/issue10-write-cycle-20260826/native-results.md).
(Шаг ENTERPRISE не пишет `/DumpResult`; результат — строго валидный receipt.)

**Усиленный post-flight применён к артефактам этого прогона** (2026-08-26, без повторного
нативного прогона — каталог сохранён): receipts байт-в-байт равны frozen (`cmp`), все четыре
`*.result` нормализованно равны `"0"`, оба load-лога содержат `Configuration successfully
updated`, snapshot closure чист. Результат: все проверки прошли.

**Пять ложноположительных обходов (репродукция ревью владельца) отклоняются** усиленным
runbook'ом — проверено выполнением дословно извлечённых check-функций на поддельных входах:

| Обход | Результат |
|---|---|
| пять одинаковых строк `foo###999###Number` | `receipt_ok` ≠ 0 → FAIL |
| лишняя пустая строка в receipt | `cmp` ≠ 0 → FAIL |
| лишняя шестая строка | `cmp` ≠ 0 → FAIL |
| `DumpResult = "10"` | `result_zero` ≠ 0 → FAIL |
| `DumpResult = "error0"` | `result_zero` ≠ 0 → FAIL |
| лишний файл в snapshot | `SNAPSHOT_FAIL extra=1` → FAIL |
| listed-файл заменён symlink'ом с теми же байтами | `SNAPSHOT_FAIL symlinks=1` → FAIL |
| listed-файл заменён каталогом | `SNAPSHOT_FAIL missing=1` → FAIL |

Те же обходы закреплены регрессионными тестами `Issue10RunbookFailClosedTests`
(извлекают check-функции из этого дока и исполняют их через bash).

## 7. RED / GREEN (точное значение И тип)

`evidence/green-receipt.txt` (изменённая):

```text
tab###1234###Number
nbsp###1234###Number
invalid######Undefined
decimal###1234.56###Number
space###567###Number
```

`evidence/red-receipt.txt` (исходная):

```text
tab######Undefined
nbsp######Undefined
invalid######Undefined
decimal###1234.56###Number
space###567###Number
```

| Case | RED (исходная) | GREEN (изменённая) | Тип |
|---|---|---|---|
| `1⇥234` | value `""`, **type `Undefined`** | value `1234`, **type `Number`** | flip |
| `1␣234` | `""` / `Undefined` | `1234` / `Number` | flip |
| `12x3` | `""` / `Undefined` | `""` / `Undefined` | контроль |
| `1234.56` | `1234.56` / `Number` | `1234.56` / `Number` | сохранено |
| ` 567 ` | `567` / `Number` | `567` / `Number` | сохранено |

- **Положительный:** таб/NBSP теперь дают число.
- **Отрицательный:** `12x3` отклоняется в обеих версиях.
- **Сохраняемый:** десятичная и обычные пробелы не изменились.
- **Mutation power:** без правки `tab###`/`nbsp###` — `Undefined`; с правкой — `1234`.
  Контроли не флипаются → проверка не тавтология.
- **Типы:** значение и тип проверяются по каждому case; `###Undefined` != пустая строка.

## 8. Immutable source (до/после, с закрытием manifest)

- Source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
  (до и после — одинаковый).
- Manifest identity (SHA-256 байтов `snapshot.manifest`):
  `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691` (одинаковый до/после).
- Пофайловая сверка snapshot после прогона: **5099/5099 OK, missing 0, mismatch 0, extra 0,
  symlink 0** — проверка закрывает и отсутствующие, и лишние файлы, и ссылки.

## 9. Решение по инструментам

Нативных средств платформы достаточно: `CREATEINFOBASE`, `DESIGNER /LoadConfigFromFiles
/UpdateDBCfg`, `ENTERPRISE`. Новая зависимость, patch-engine, parser, RAG, MCP, graph, SDK,
runner или плагин-система не добавлялись. В репозиторий добавлены:
- небольшой frozen evidence package
  [`experiments/issue10-write-cycle-20260826/`](../experiments/issue10-write-cycle-20260826/);
- его fail-closed валидатор `tests/test_issue10_evidence.py`;
- этот отчёт.

Использованная ранее локальная обвязка `cc-1c-skills` (генераторы форм/драйверов) находится в
`.local/tools/`, предшествовала эксперименту и не входит в репозиторий.

## 10. Honest limits и переносимость

- Доказан **один** срез на **одной** учебной конфигурации Jet: BSL-логика одной функции.
  Не доказаны: перенос на другие конфигурации, metadata-объекты, старые платформы (#3),
  другие агентные клиенты (#4), серверный контекст, полный жизненный цикл приложения.
- Probe исполняется на клиенте файловой ИБ; в `OnStart` после probe стоит `Return`, поэтому
  доказано исполнение именно `StringToNumber`, а не полный старт/выход 1С. Это осознанная узость.
- Receipt записывается только probe (`TextWriter`); production-функция ввода-вывода не выполняет.
  Символы `\r\n` в receipt порождены платформенным `TextWriter`; значения детерминированы.
- Учебная редакция имеет лимит соединений с ИБ (`Infobase connections limitation reached`);
  «зависшая» клиентская сессия держит слот. Runbook завершает ENTERPRISE через `setsid` +
  `kill -KILL -$PID` (вся process group), поэтому осиротевшие сессии не остаются.
- Xvfb рендерится на глубине 8, чтобы обойти сегфолт рендерера (pixman/cairo) на глубине 24 в
  этом контейнере. Затрагивает только headless-дисплей, не логику BSL.
- Immutable-защита `.local/` — это права и конвенция, а не криптографическая граница: агент с
  тем же uid может записать файл. Защита от злонамеренного процесса с тем же uid осознанно
  оставлена ограничением; требование здесь — отсутствие фактического нарушения в принимаемом
  прогоне (что и проверяют pre/post identities).
- Никакого write-framework: это не эквивалент универсальной среды разработки 1С. Исходный
  CF, snapshot, manifest и исходная ИБ неизменяемы.

## 11. Восстановление immutable snapshot из чистого состояния

Если стенд разворачивается заново, immutable snapshot создаётся из source CF:

```bash
# 1) создать временную ИБ из CF
"${XVFB[@]}" "$V/1cv8t" CREATEINFOBASE "File=$TMP_IB" /DisableStartupDialogs /DisableStartupMessages /Out /dev/stdout /DumpResult /dev/stdout
# 2) загрузить конфигурацию и выгрузить split-dump
"${XVFB[@]}" "$V/1cv8t" DESIGNER /F "$TMP_IB" /LoadCfg "$CF" /UpdateDBCfg /DisableStartupDialogs /DisableStartupMessages
"${XVFB[@]}" "$V/1cv8t" DESIGNER /F "$TMP_IB" /DumpConfigToFiles "$SNAP" -Format Hierarchical /DisableStartupDialogs /DisableStartupMessages
# 3) зафиксировать manifest и identity (точно как в docs/lab.md: сортировка
#    Path-объектов Python, формат "<sha256><два пробела><relative POSIX path><LF>")
python3 - "$SNAP" <<'PY'
from pathlib import Path
import hashlib, sys
snap = Path(sys.argv[1])
files = sorted(path for path in snap.rglob('*') if path.is_file())
if len(files) != 5099:
    raise SystemExit(f'file_count={len(files)}, expected 5099')
with (snap / '..' / 'snapshot.manifest').open('w', encoding='utf-8', newline='\n') as out:
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out.write(f'{digest}  {path.relative_to(snap).as_posix()}\n')
PY
sha256sum "$MANIFEST"   # должно быть 70972b5e...
```

Порядок строк важен: манифест должен быть отсортирован так же, как в `docs/lab.md`
(Python `sorted` по `Path`-объектам, component-wise), иначе identity `70972b5e…` не
воспроизведётся. Проверено: `sort -k2` и locale-aware `sort` дают другой порядок строк
и другой identity; только указанный Python-вариант воспроизводит байт-в-байт.

После этого выполняется runbook из §6. Автоматическая проверка evidence-пакета:
`python3 -m unittest tests.test_issue10_evidence -v`.
