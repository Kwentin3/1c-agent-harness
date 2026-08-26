# Issue #10 — frozen evidence package

Доказательство вертикального среза «изменить → нативно загрузить → доказать новое поведение»
на конфигурации Jet (issue #10). Финальный чистый прогон выполнен **буквально исполнением
committed runbook** (2026-08-26, `docs/issue-10-write-cycle.md` §6) в новом уникальном
каталоге `.local/runs/issue10-write-cycle-20260826T190503`; его receipts байт-в-байт
совпадают с receipts этого пакета.

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

Единственный авторитетный исполнимый runbook — раздел §6 документа
`docs/issue-10-write-cycle.md` (bash-блок выполняется буквально из корня репозитория).
Краткий конспект его контракта:

1. **Pre-flight (fail-closed):** source CF hash `5694f9e4bd…`, manifest identity `70972b5e…`,
   `sha256sum -c` snapshot — иначе стоп. `RUN_DIR` генерируется с уникальным timestamp и
   **не должен существовать** до `mkdir`.
2. **Work copies:** `cp -R snapshot/. -> img` (GREEN) и `img-red` (RED), запись — только
   `chmod -R u+w` внутри копий.
3. **Diff:** в `img` применяются `production-patch.diff` + `instrumentation.diff`
   (`git apply -p1`), в `img-red` — только `instrumentation.diff`; путь receipt подставляется
   `sed` в `<variant>-receipt.txt`.
4. **Native:** `CREATEINFOBASE` → `DESIGNER /LoadConfigFromFiles /UpdateDBCfg` → `ENTERPRISE`
   для каждого варианта; `DumpResult == 0` и `Configuration successfully updated` проверяются.
5. **Lifecycle:** ENTERPRISE запускается через `setsid` (своя process group); ожидание —
   строгий receipt (5 непустых строк `label###value###type` + стабильность хэша), затем
   `kill -KILL -$PID` по всей группе.
6. **Post-flight (fail-closed):** те же immutable identities + строгие receipts, иначе стоп.

Все остальные прозовые описания в этом файле — не источник истины для воспроизведения.

## Проверка пакета

```bash
python3 -m unittest tests.test_issue10_evidence -v
```

Тесты fail-closed: ровно 5 непустых строк, ровно 3 поля, без игнорируемых строк,
duplicate/unknown/missing labels, точные value/type; множество файлов пакета == множество
manifest artifacts (исключая сам manifest); missing/changed/unlisted artifact → FAIL;
приватные пути и несовпадение immutable identities → FAIL.
