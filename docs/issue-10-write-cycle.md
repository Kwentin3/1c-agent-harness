# Issue #10 — Цикл изменения и нативной проверки конфигурации 1С (R&D)

Статус: **эксперимент выполнен, результат подтверждён в одноразовой ИБ; PR не смержен автоматически.**
Дата: 2026-08-26. Платформа: официальная учебная «1С:Предприятие 8.5, учебная версия 8.5.1.1150», Linux 64-bit.
Конфигурация: официальный release asset `1Ci-Company/Jet` `v1.0.3.1-tr`.

Это R&D по способу достижения цели, а не начало универсальной write-платформы. Эксперимент подтверждает
горизонтальный срез: **агент способен за один цикл получить задачу → найти место изменения → понять
существующую логику → внести минимальную правку → загрузить её в изолированную 1С → доказать новое
поведение.**

Не утверждается, что этот результат распространяется на старые платформы (#3), другие агентные клиенты
(#4) или production. Эти темы остаются отдельными этапами.

## 1. Выбранная задача и почему она достаточна

Функция `StringFunctionsClientServer.StringToNumber` (`CommonModules/StringFunctionsClientServer/Ext/Module.bsl`)
преобразует строку в число без вызова исключений. Она сворачивает только обычный пробел `" "` и не обрабатывает
типичные непечатаемые разделители, которые появляются при копировании чисел: табуляцию (`Chars.Tab`) и
неразрывный пробел (`Chars.NBSp`). Для `"1⇥234"` или `"1␣234"` она возвращает `Undefined`.

**Фича:** принимать эти два непечатаемых разделителя при разборе числа, но продолжать отклонять
нечисловой текст (`12x3` → `Undefined`).

Почему задача достаточна:

- маленькая и локальная: правка в одном модуле;
- поведение «до/после» наблюдаемо: `Undefined` → `1234`;
- есть и положительный (`1⇥234` → `1234`), и отрицательный (`12x3` → `Undefined`), и сохраняемый
  (`1234.56` → `1234.56`) сценарии;
- тест не сводится к функции, всегда возвращающей заранее известное значение: поведение зависит от входа;
- не требует GUI, внешней интеграции, production-данных или секретов.

## 2. Исходные locators и минимальный patch

Локатор функции в **иммутабельном исходнике**
`CommonModules/StringFunctionsClientServer/Ext/Module.bsl`:
- комментарий контракта функции: 797–809;
- тело `Function StringToNumber(Val Value) Export`: 810–827.

В **изменённой рабочей копии** тело сдвинуто на +4 строки (810–832), потому что добавлены 4 строки.
Обе ссылки относятся к одному и тому же коду; у приведённого ниже diff указан контекст по исходнику.

Изменение вносится **только в рабочую копию** `.local/runs/issue10-jet-string-whitespace/work-config`:

```text
До:
Value  = StrReplace(Value, " ", "");
...
После:
Value  = StrReplace(Value, " ", "");
// Digits are commonly separated by tab or a non-breaking space in copied
// text. Strip those as well, not just the regular space.
Value  = StrReplace(Value, Chars.Tab, "");
Value  = StrReplace(Value, Chars.NBSp, "");
...
```

Полный diff рабочей копии против иммутабельного snapshot: **ровно +4 строки** (2 комментария +
2 `StrReplace`), `0` удалённых; отличаются два файла — `StringFunctionsClientServer/Module.bsl` и
`Ext/ManagedApplicationModule.bsl` (probe). Больше ничего в конфигурации не менялось.

## 3. Границы (frozen в task-contract.json)

| Роль | Путь |
|---|---|
| immutable source CF | `.local/dist/Jet-1.0.3.1-tr.cf` |
| immutable source snapshot | `.local/runs/training-jet-review-final/snapshot` |
| immutable source manifest | `.local/runs/training-jet-review-final/snapshot.manifest` |
| writable work copy | `.local/runs/issue10-jet-string-whitespace/work-config` |
| disposable test IB (changed) | `.local/runs/issue10-jet-string-whitespace/instr-ib` |
| disposable test IB (original) | `.local/runs/issue10-jet-string-whitespace/red-ib` |
| evidence | `.local/runs/issue10-jet-string-whitespace/evidence` |

Все write-операции выполнялись только в work copy и disposable ИБ внутри `.local/`. Исходные source CF,
source snapshot и source manifest не записывались.

## 4. Runtime probe (тестовая инструментация)

Чтобы доказать, что изменённый BSL действительно исполняется внутри 1С, в одноразовую рабочую копию
добавлен `Issue10WriteRuntimeReceipt()` в `OnStart` модуля управляемого приложения. Он вызывает
production `StringToNumber` для пяти кейсов и пишет текстовый receipt в `run/home/issue10-runtime-receipt.txt`:

```text
1⇥234 (tab), 1␣234 (NBSP), 12x3, 1234.56, " 567 "
```

Probe не является реализацией. Он остаётся только в throwaway work copy и не попадает в исходник или
в репозиторий. Это осознанный выбор: так фича доказывается исполнением, а не парсингом файлов.

## 5. Нативная загрузка, проверка и runtime (точные команды)

Создание одноразовой файловой ИБ и нативная загрузка изменённой конфигурации:

```bash
1cv8t CREATEINFOBASE "File=<run>/instr-ib" /DisableStartupDialogs /DisableStartupMessages /Out <log> /DumpResult <result>
1cv8t DESIGNER /F "<run>/instr-ib" /LoadConfigFromFiles "<run>/work-config/files" /UpdateDBCfg /DisableStartupDialogs /DisableStartupMessages /Out <log> /DumpResult <result>
```

`/DumpResult` == `0`; в логе `Configuration successfully updated` — **платформа приняла изменение** (уровень 1).

Runtime-сценарий внутри одноразовой ИБ:

```bash
xvfb-run -a -s "-screen 0 1280x1024x8 -nolisten tcp" \
  1cv8t ENTERPRISE /F "<run>/instr-ib" /DisableStartupDialogs /DisableStartupMessages /DisplayManager "none" /Out <log>
```

## 6. RED / GREEN и сила теста

**Рабочая (изменённая) конфигурация** — `evidence/green-receipt.txt`:

```text
tab###1234
nbsp###1234
invalid###
decimal###1234.56
space###567
```

**Исходная конфигурация** (тот же probe, но без правки) — `evidence/red-receipt.txt`:

```text
tab###
nbsp###
invalid###
decimal###1234.56
space###567
```

| Вход | Исходная (RED) | Изменённая (GREEN) |
|---|---|---|
| `1`+TAB+`234` | Undefined | **1234** |
| `1`+NBSP+`234` | Undefined | **1234** |
| `12x3` | Undefined | Undefined |
| `1234.56` | 1234.56 | 1234.56 |
| ` 567 ` | 567 | 567 |

- **Положительный** сценарий: таб/неразрывный пробел теперь дают число.
- **Отрицательный** сценарий: `12x3` отклоняется в обеих версиях.
- **Сохраняемый** сценарий: десятичная и обычные пробелы ведут себя как раньше.

Тест различает старую и новую версию (mutation power): без правки `tab###`/`nbsp###` пусто (Undefined),
с правкой — `1234`. Это не тавтология: контроль падает при отсутствии фичи.

## 7. Hashes неизменного источника (до/после)

- Source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
  (совпадает с зафиксированным fixture hash из bootstrap).
- `work-config/original.cf` == source CF: да.
- Source snapshot: все **5099/5099** записей `snapshot.manifest` существуют на диске и совпадают по
  SHA-256 (0 missing, 0 mismatch) — снимок не изменялся.

Примечание: агрегатный content ID из `docs/lab.md` (`sha256:70972b5e…`) относится к другому прогону
выгрузки и другой конвенции хеширования. Авторитетное доказательство неизменности здесь — пофайловое
совпадение 5099/5099, а не агрегат.

## 8. Решение по инструментам

Нативных средств платформы оказалось достаточно для полного цикла edit → load → check → runtime:
`CREATEINFOBASE`, `DESIGNER /LoadConfigFromFiles /UpdateDBCfg`, `ENTERPRISE`. Никакая новая зависимость,
patch-engine, parser, RAG, MCP, graph, adapter SDK или тестовая система плагинов не добавлялась.
Единственное использованное вспомогательное средство — локальные `cc-1c-skills` генераторы форм/драйверов
в `.local/tools/`, предшествующие этому эксперименту и не добавленные в репозиторий.

## 9. Verdict независимого reviewer

Независимый критик (отдельный агент, работал read-only только с файлами и собственными замерами, не
опирался на этот отчёт) подтвердил **все 7 контрольных пунктов**:

1. **Иммутабельный источник** — ✅ источник CF `5694f9e4bd…` == `original.cf`; snapshot сверен
   `sha256sum -c`: 5099/5099 OK, 0 failed, 0 missing, exit 0.
2. **Минимальная правка только в рабочей копии** — ✅ единственный hunk, +4 строки, 0 удалённых;
   отличаются ровно 2 файла (Module.bsl и probe в ManagedApplicationModule).
3. **Probe — тестовая обвязка** — ✅ `Issue10WriteRuntimeReceipt()` есть и вызывается в `OnStart`;
   `StringToNumber` сам не выполняет ввода-вывода (только `StrReplace` + `AdjustValue` + `Return ?(...)`).
4. **Runtime внутри 1С** — ✅ подтверждено настоящими runtime-ошибками платформы в логах
   (`Object method not found (WriteString)`, `Training version limitation… / Infobase connections
   limitation…`), значениями receipts, BOM и возникновением отдельных ИБ/сессий.
5. **Проверка не тавтологична (mutation power)** — ✅ green `tab###1234,nbsp###1234` ↔ red
   `tab###,nbsp###` (пусто/Undefined); контроли (invalid/decimal/space) совпадают.
6. **Source не затронут, runtime не подменён парсингом** — ✅ mtime/mode неизменны (до прогона);
   результат — живое исполнение.
7. **Новые зависимости/артефакты** — ✅ в репозитории единственный новый файл
   `docs/issue-10-write-cycle.md`; весь ран-мусор в `.local/` (gitignored).

**Неразрешённые reviewer'ом технические детали (не опровергают доказательность):**

- **CRLF в receipt против `Chars.LF`.** Reviewer отметил, что не может воспроизвести байтовое
  происхождение receipt. Объяснение: receipt сохранялся посредством `shutil.copyfile` (побайтово),
  без какой-либо постобработки; следовательно `\r\n` порождён самим `TextWriter` платформы при
  записи, а не моим кодом. Значения строк детерминированы (выводимы из probe), а независимым
  подтверждением живого исполнения служат реальные runtime-ошибки платформы в логах.
- **`OnStart` в инструментированной копии завершается через `Return;`** (строки 58–59): это означает,
  что доказано исполнение именно `StringToNumber`, а не полного жизненного цикла приложения.
  Отчёт это фиксирует честно (см. §10). Полный жизненный цикл приложения не проверялся.
- **Локатор `:797-828`** — точный locator по иммутабельному исходнику (контракт 797–809, тело
  810–827); reviewer измерил тело в изменённом файле (810–832), что согласовано (сдвиг +4 строки).

Главный вывод reviewer: цикл «понять → минимальная правка → нативная загрузка → доказанное новое
поведение» **доказан на этом стенде**; правка минимальна и локальна; иммутабельный источник не изменён;
A/B-тест обладает mutation power.

## 10. Известные ограничения переносимости и честные границы

- Доказан **один** горизонтальный срез на **одной** учебной конфигурации Jet. Не доказаны: переносимость
  на другие конфигурации, изменение metadata-объектов (иначе, чем BSL-логика), старые платформы (#3),
  другие агентные клиенты (#4).
- Probe исполняется на клиенте (файловая ИБ); это валидное исполнение BSL, но не доказательство
  серверного контекста/процессов.
- В инструментированной копии `OnStart` завершается через `Return;` после вызова probe, поэтому
  доказано исполнение именно `StringToNumber`, а не полного жизненного цикла приложения. Это
  осознанная узость: целью было доказать исполнение целевой функции, а не полный старт/выход 1С.
- Receipt записывается только тестовым probe (`TextWriter`); сама production-функция `StringToNumber`
  ввода-вывода не выполняет. Символы `\r\n` в receipt порождены `TextWriter` платформы; файлы
  сохранялись побайтово (`shutil.copyfile`) без постобработки. Значения строк детерминированы
  и воспроизводимы из кода probe; независимым подтверждением живого исполнения служат
  реальные runtime-ошибки платформы в логах.
- Изменение минимально и локально; существующий read-only evidence harness не переделывался в write-framework.
- Учебная редакция вводит лимит соединений с ИБ. «Зависшая» клиентская сессия (например, не вышедший
  корректно процесс ENTERPRISE, убитый через `xvfb-run`-wrapper) держит слот и может на время исчерпать
  лимит `Infobase connections limitation reached`. Снимается завершением осиротевшего `1cv8t`-ребёнка
  и/или пересозданием одноразовой ИБ. Это влияло на тайминг, но не на результат.
- Xvfb рендерится на глубине 8 (`-screen 0 1280x1024x8`), чтобы обойти сегфолт рендерера
  (pixman/cairo) на глубине 24 в этом контейнере. Это затрагивает только headless-дисплей, не логику BSL.

## 11. Способ воспроизведения из чистого состояния

1. Развернуть стенд по `docs/lab.md` / `docs/lab-bootstrap.md` (платформа, libs, fontconfig, Xvfb, xkbcomp).
2. Скачать официальный Jet `v1.0.3.1-tr` fixture и проверить hash `5694f9e4…` (см. `docs/lab-bootstrap.md`).
3. Восстановить иммутабельный snapshot (если нужен источник для сверки):
   `1cv8t DESIGNER /F ib /DumpConfigToFiles snapshot -Format Hierarchical` в новый пустой каталог.
4. Создать writable work copy из исходного CF: `/DumpConfigToFiles`, или развернуть из split-каталога.
5. Применить patch из раздела 2 к `CommonModules/StringFunctionsClientServer/Ext/Module.bsl`.
6. Добавить probe из раздела 4 в `Ext/ManagedApplicationModule.bsl` (только в work copy).
7. `CREATEINFOBASE` → `DESIGNER /LoadConfigFromFiles ... /UpdateDBCfg` (проверить `DumpResult` == 0).
8. `xvfb-run -s "-screen 0 1280x1024x8"` → `ENTERPRISE /F ib`; после завершения прочитать receipt.
9. Повторить 7–8 для исходной версии (без patch) — получить RED (пустые `tab###`/`nbsp###`).
10. Сверить source CF и snapshot hashes (раздел 7).

Все пути и переменные среды зафиксированы в `task-contract.json` и `evidence/EVIDENCE.md`.
