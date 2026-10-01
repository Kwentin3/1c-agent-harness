# Pre-native preflight

- **Change:** текущая экспортная серверная процедура перезаписывает `DateOfLastUse` при любом неравном значении; требуется обновлять дату только на более новую, сохранив no-op для равной и более старой даты.
- **Контекст:** `EmailAccountSettings` — независимый непериодический регистр с измерением `EmailAccount` и сохраняемым атрибутом `DateOfLastUse` типа `Date`:
  - `.local/runs/training-jet-review-final/snapshot/InformationRegisters/EmailAccountSettings.xml:163-167`
  - `.local/runs/training-jet-review-final/snapshot/InformationRegisters/EmailAccountSettings.xml:1021-1066`
  - `.local/runs/training-jet-review-final/snapshot/InformationRegisters/EmailAccountSettings.xml:1067-1083`
  - экспортный server-side entry point, блокировка, транзакция, чтение и запись: `.local/runs/training-jet-review-final/snapshot/InformationRegisters/EmailAccountSettings/Ext/ManagerModule.bsl:40-100`
  - реальные вызовы без явной даты: `.local/runs/training-jet-review-final/snapshot/CommonModules/EmailManagement/Ext/Module.bsl:221-230,712-727`; `.local/runs/training-jet-review-final/snapshot/Documents/OutgoingEmail/Ext/ObjectModule.bsl:133-143`.
- **Current scenario:** при сохранённой дате `2026-08-20` и входящей `2026-08-10` процедура блокирует запись по аккаунту, читает набор и из-за проверки `stored <> incoming` записывает `2026-08-10`, то есть уменьшает persisted scalar.
- **Preserved behavior:** новая дата должна сохраняться; равная — не вызывать запись; при отсутствии записи должна создаваться одна запись; `Undefined` должен по-прежнему преобразовываться в `BegOfDay(CurrentSessionDate())`.
- **Plausible wrong implementations:**
  1. Обратить сравнение и обновлять только при `stored > incoming`: старая дата продолжит уменьшать значение, новая перестанет сохраняться.
  2. Разрешить `stored <= incoming`: scalar будет верным, но равная дата перестанет быть no-op и вызовет лишнюю запись.
  3. Применить защиту только к существующей записи и пропустить ветку создания либо сравнить до нормализации `Undefined`.
- **Persisted/scalar observations:** матрица прямого вызова экспортной процедуры: `20→10 = 20`, `20→25 = 25`, `20→20 = 20` и `write_count=0`, отсутствие записи `→15 = count 1/date 15`, omitted date `→ BegOfDay(CurrentSessionDate())`. Эти наблюдения различают все перечисленные контрреализации.
- **Unknowns:** native 1C ещё не подтверждала фактический write-count и runtime-поведение; в snapshot нет production-вызова с явно переданной датой, поэтому следующий ограниченный эксперимент должен использовать прямой экспортный server entry point. Record-set module пуст, дополнительных write hooks не обнаружено.

## Metadata

- `start_utc: 2026-08-30T11:02:43Z`
- `end_utc: 2026-08-30T11:04:51Z`
- `duration_seconds: 128`
- `HEAD: f8b94fa4dd1644dd6d38d4c35d88f89d0796ba14`
- `TREE: 94531ecf9f210ef22edf4622264fbd912db66483`
- `verdict: READY FOR NATIVE`
- `native_attempts: 0`
- `files_modified: 0`
- `owner_interventions: 0`
- Front door: JSON `status=ready`; 5,099 snapshot files validated.
- Final Git status: clean.
- Source CF SHA-256: `5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a`
- Manifest SHA-256: `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`
- **Verification note:** первый non-native preflight-вызов ошибочно добавил неподдерживаемый subcommand `status`; повтор выполнен корректно как `python3 scripts/project_target.py`, без сброса таймера.
- **Прочитанные paths:** task, обе указанные skills, `project-target.json`, `scripts/project_target.py`, snapshot manifest, `Configuration.xml`, указанные выше XML/BSL locators и пустой `InformationRegisters/EmailAccountSettings/Ext/RecordSetModule.bsl`; дополнительно выполнен ограниченный exact-token scan по snapshot `*.bsl`/`*.xml`.

READY FOR NATIVE
