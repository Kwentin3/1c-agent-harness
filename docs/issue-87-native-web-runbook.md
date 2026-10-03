# #87: native web — проверенный reference и короткий runbook

**Локальный reference принят: native UI / пустой день / Refresh / restart PASS.
Сквозной refine и публичная доставка ещё не завершены.**

## Один источник процедуры

[Канонический recipe в 1c-enterprise-linux](../skills/1c/1c-enterprise-linux/references/native-training-web-reference.md)
содержит подготовку, проверенные компоненты/команду installer, условия двух
resource aliases, права service user, ежедневную приёмку и адресный rollback.
Здесь нет второго установщика или повторной реализации команд.

- **Готовая среда:** агент проверяет target/доступы и результат; не переустанавливает ПО.
- **Новая среда:** оператор получает конкретный ограниченный допуск и готовит отдельный
  экземпляр. Software остаётся root-owned в штатных paths; task data/evidence в `.local/`.
- **Приёмка:** actual native report + Refresh + свежая сессия после согласованного
  restart. HTML200 и `Publication successful` недостаточны.

## Что принято независимо

Источник — [первый operator handoff](https://github.com/Kwentin3/1c-agent-harness/issues/87#issuecomment-5967171085)
и [устранение 404/actual GUI](https://github.com/Kwentin3/1c-agent-harness/issues/87#issuecomment-5967779120).
[Sanitized intake + raw anchors](../experiments/issue87-web-publication/reference-native-intake.json),
[полные версии пакетов до diagnostic additions](../experiments/issue87-web-publication/reference-packages.txt).

Hermes скачал и сверил хеши 99 выбранных raw artifacts, ещё 9 recipe/config
artifacts; изучил authoring commands/exit receipts, disassembly, native bodies,
Playwright trace и actual report HTML. Архивы изучались как данные, не исполнялись.
Screenshot просмотрен как дополнительное, не основное доказательство.

| Утверждение | Доказательство / граница |
|---|---|
| Штатная установка и publisher | retained exact help/argv/rc0; package metadata; generated/derived config bytes independently read. Исполнение операторское |
| Причинный контроль 404 | `causal-control.json`: links removed →404; restored →200 / exact original JS hash. Authoring/rc0 inspected; не повторён Hermes |
| Fixed-prefix discovery mismatch | `vrscoret.so` `0x39b174` mask, `0x39b256–265` prefix strlen+1, `0x39b327` skip, `0x39b362–381` root/en; retained disassembly inspected. Причина этих exact bytes, не официальный vendor bulletin |
| Настоящий Dashboard | HTTP responses из trace содержат дату 2026-10-02, семь нулей и empty-day text, совпадают с iframe/скриншотом |
| GUI Refresh | trace `#form0_FormRefresh` click + другой server tempstorage path + два report responses200. Session URLs не публикуются |
| Network | operator response-event ledger157: все200/204; trace содержит183 resource snapshots, тоже200/204. Это разные счётчики, не 157 всех сетевых событий |
| Full container restart/persistence | operator exact stop/start commands/rc0 и IB receipt; новая browser session. Host action externally attested, не live Docker-проверка Hermes |
| Original inputs | свежая SSH-проверка CF/manifest/snapshot5099/demo/backup/config/VRD/runtime-locator/project-target: unchanged, frontdoor ready |
| Installed605 original files | operator hash comparison; manifest anchors прочитаны/сверены. Live bytes остановленного runtime недоступны Hermes |
| Экспорт обновлённой ИБ | retained оператором. Hermes UID10001 получил PermissionError при прямом hash; права не ослаблялись |

## Существенный вывод

Одна штатная установка **не** исправила 404. Исправление — явно объявленные два
relative symlink на собственные unchanged resources exact training 8.5.1.1150,
с неизменными Apache/VRD между causal lanes. Никакой URL rewrite, JS/HTML/binary
patch, подмены версии/UID или новых лицензий. Не называем финальный runtime
неизменённой vendor installation и не переносим workaround на другие сборки.
Условие применения/удаления и target/module hashes находятся в canonical recipe.

Failed intermediate control UID33/GID0 сохранён; он не является restart-приёмкой.
На этом ходе нет новых native runs Hermes, publisher repeats или CLI runs #85.
Подробные counts разных operator phases находятся в intake; исходный бюджет не сброшен.

## Harness/tool contract

Код companion/transport/runtime contract менять не требуется по текущим фактам:
`cf_materializer.runtime_paths` читает только абсолютный executor-injected
`ONE_C_HARNESS_RUNTIME_CONFIG`, не `.local/one-c-runtime.json` по cwd.
`require_runtime` проверяет platform/xvfb/fontconfig/libs. Штатные реальные paths
допустимы тем же контрактом; loader env runners задаёт vendor dir + declared libs.
Это не основание менять schema, добавлять fallback/discovery/SSH/install framework.
Новая reference web-приёмка проходила без такого loader override и **не доказала**
cold CF/Designer lifecycle текущего harness на новом runtime.

Runtime locator прежнего executor не переключён. В обычной SSH login-сессии
`ONE_C_HARNESS_RUNTIME_CONFIG` не задан: для cold/native режима нужен заранее
подготовленный executor launch env, а не скрытый файл или новая переменная в model args.
Warm admitted snapshot не требует запуска 1С.

## Source checks и remaining gates

`python3 -m unittest discover -s tests -v` — **344 tests, OK**; focused skill
manifest — **3 tests, OK**. [Remote source regression](../experiments/issue87-web-publication/reference-source-regression.json)
использовала bytes current source `585f182` (все 30 Python-файлов сверены), отдельную
физическую копию настоящего snapshot5099 и неизменённый project contract.
Warm `open → narrow → open` PASS; повтор тот же SnapshotRef. `verify` проверен
только на invalid-envelope refusal до native launch. Native0, original unchanged,
owned snapshot copy очищена. Source extract/evidence retained 558529 bytes, это task data,
не новый workspace/deployment. Preliminary assertion typo и cleanup read-only dirs
сохранены в regression limits; исправлялся только task diagnostic, не harness core.

Новый reference recipe установлен byte-identical каноническому файлу;
`skill_view` действительно дочитывает его. **Полная package parity ещё не PASS:**
в installed остаются прежние отличия в `SKILL.md` и
`references/standard-print-form-native-proof.md`; неизвестные/ценные дополнения
не удалялись и не объявлялись автоматически принятыми. Version equality ≠ parity.
No-paid граница #87 сохранена: новые reviewers/subagents не запускались.

1. Полная source/installed reconciliation и независимая fresh-agent discovery.
2. Cold CF и успешный native `verify` на новом runtime NOT_RUN; source/unit seam
   coverage и warm real-snapshot check их не заменяют.
3. Fresh-agent **web** воспроизведение на prepared reference, не чтение инструкций:
   нынешний reference остановлен, ordinary route не имеет Docker/start/access в него.
   Не запускать повтор скрытым административным допуском; оператор должен предоставить
   bounded готовую поверхность приёмки, не root credentials.
4. Nonzero GUI oracle, midnight/RLS и protected ingress не приняты этим empty-day контролем.
   Публичная доставка, merge и закрытие #87 остаются отдельными решениями.

`AGENTS.md` здесь не изменён: отдельная попытка уточнения границы software/data
не прошла обязательное подтверждение protected-file write. Отсутствие ответа не
считается согласием; повтор через другой инструмент не выполнялся. Новый recipe
не отменяет действующие read-only ограничения или owner gates.

[Предварительный admission](issue-87-reference-admission.md) сохранён исторически;
не переписываем прежние FAIL под новый PASS. Контрольная обновлённая ИБ/runtime/
evidence удерживаются для дальнейшей приёмки; cleanup/prune не выполнялся.
