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
	Receipt = New TextWriter("<RUN_DIR>/evidence/<variant>-receipt.txt", TextEncoding.UTF8);
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
| writable work copy (GREEN) | `.local/runs/<run-id>/img/files` |
| writable work copy (RED) | `.local/runs/<run-id>/img-red/files` |
| disposable test ИБ | `.local/runs/<run-id>/instr-ib`, `red-ib` |
| evidence | `.local/runs/<run-id>/evidence` |

`<run-id>` — уникальный каталог, созданный заново для этого прогона; он не существовал до
прогона. source/snapshot/manifest/platform лежат **вне** run-каталога; проверяется
физическая непересекаемость до первой записи. Все записи — только в work copy и disposable ИБ.

## 6. Точные native-шаги и результаты

Переменные (абсолютные пути):

```bash
ROOT=<REPO_ROOT>                       # корень рабочей копии репозитория
RUN_DIR=$ROOT/.local/runs/issue10-write-cycle-final-20260826T173251   # уникальный, не существовал
V=$ROOT/.local/platform/1cv8t/x86_64/8.5.1.1150
L=$ROOT/.local/platform/libs
export PATH="$L/usr/bin:$PATH"
export LD_LIBRARY_PATH="$V:$L/usr/lib/x86_64-linux-gnu"
export FONTCONFIG_FILE="$ROOT/.local/platform/fonts.conf"
export HOME="$RUN_DIR/home" TMPDIR="$RUN_DIR/tmp"
export XDG_CACHE_HOME="$HOME/xdg-cache" XDG_CONFIG_HOME="$HOME/xdg-config" XDG_DATA_HOME="$HOME/xdg-data"
XRUN="$L/usr/bin/xvfb-run -a -s '-screen 0 1280x1024x8 -nolisten tcp'"
```

**GREEN** (изменённая конфигурация). Каждый `*.result` не должен существовать заранее:

```bash
# 1. создать файловую ИБ
$XRUN "$V/1cv8t" CREATEINFOBASE "File=$RUN_DIR/instr-ib" \
  /DisableStartupDialogs /DisableStartupMessages \
  /Out "$RUN_DIR/logs/green-create.log" /DumpResult "$RUN_DIR/logs/green-create.result"
# 2. нативно загрузить изменённую конфигурацию и привести БД в исполнимое состояние
$XRUN "$V/1cv8t" DESIGNER /F "$RUN_DIR/instr-ib" \
  /LoadConfigFromFiles "$RUN_DIR/img/files" /UpdateDBCfg \
  /DisableStartupDialogs /DisableStartupMessages \
  /Out "$RUN_DIR/logs/green-load.log" /DumpResult "$RUN_DIR/logs/green-load.result"
# 3. runtime-сценарий внутри disposable ИБ
$XRUN "$V/1cv8t" ENTERPRISE /F "$RUN_DIR/instr-ib" \
  /DisableStartupDialogs /DisableStartupMessages /DisplayManager "none" \
  /Out "$RUN_DIR/logs/green-run.log" &
PID=$!
# ожидать появления receipt (<= 180 c), затем завершить процесс-группу:
for i in $(seq 1 180); do [ -f "$RUN_DIR/evidence/green-receipt.txt" ] && break; sleep 1; done
kill -KILL -$PID 2>/dev/null || kill -KILL $PID 2>/dev/null || true
```

**RED** (исходная конфигурация, тот же probe, без production-правки):
те же три шага для `red-ib`, `img-red/files`, `red-receipt.txt`.

**Exit status и DumpResult этого прогона** (реальные значения):

| Шаг | `/DumpResult` | Лог |
|---|---|---|
| `green-create` | `0` | `Creation of infobase … completed successfully` |
| `green-load` | `0` | `Configuration successfully updated` |
| `red-create` | `0` | `Creation of infobase … completed successfully` |
| `red-load` | `0` | `Configuration successfully updated` |

Экстракты сохранены санитизированно в
[`native-results.md`](../experiments/issue10-write-cycle-20260826/native-results.md).
(Шаг ENTERPRISE не пишет `/DumpResult`; результат — receipt.)

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
/UpdateDBCfg`, `ENTERPRISE`. Новая зависимость, patch-engine, parser, RAG, MCP, graph, SDK или
плагин-система не добавлялись. В репозиторий добавлены:
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
  «зависшая» клиентская сессия держит слот. Безопасное завершение — `kill` на всю
  процесс-группу (`kill -KILL -$PID`) и/или пересоздание одноразовой ИБ. Влияет на тайминг,
  не на результат.
- Xvfb рендерится на глубине 8, чтобы обойти сегфолт рендерера (pixman/cairo) на глубине 24 в
  этом контейнере. Затрагивает только headless-дисплей, не логику BSL.
- Никакого write-framework: это не эквивалент универсальной среды разработки 1С. Исходный
  CF, snapshot и исходная ИБ неизменяемы.

## 11. Воспроизведение из чистого состояния

1. Развернуть стенд: `docs/lab.md` / `docs/lab-bootstrap.md` (платформа, libs, fontconfig,
   Xvfb, xkbcomp).
2. Получить Jet `v1.0.3.1-tr` CF, проверить `SHA-256 = 5694f9e4bd…`.
3. Восстановить immutable snapshot: `DESIGNER /DumpConfigToFiles -Format Hierarchical`
   в новый пустой каталог + `snapshot.manifest` (identity `70972b5e…`).
4. Создать уникальный `<RUN_DIR>` (не должен существовать; иначе стоп).
5. Скопировать snapshot в `img/files` и `img-red/files`, разрешить запись только внутри копий.
6. В `img/files` применить production patch (см. §3); в `img-red` — не патчить.
7. В обе копии внести probe и вызов в `OnStart` (см. §4; пути receipt —
   `<RUN_DIR>/evidence/<variant>-receipt.txt`).
8. Выполнить шаги §6 для GREEN и RED: `CREATEINFOBASE` → `DESIGNER /LoadConfigFromFiles
   /UpdateDBCfg` → `ENTERPRISE` (проверить `DumpResult == 0`, `Configuration successfully updated`,
   receipt существует; после — завершить процесс-группу).
9. Сверить receipts с таблицей §7 (точные значения И типы, 5 строк, без дубликатов).
10. Сверить immutable source: CF hash и manifest identity — до/после; snapshot 5099/5099,
    missing/mismatch/extra/symlink = 0.

Автоматическая проверка evidence-пакета: `python3 -m unittest tests.test_issue10_evidence -v`.
