# 1С Harness: финализация документации и скилов

## Решение и границы

По решению владельца research arm Antigravity прекращён. Исторический результат
31/47 сохранён; client-specific adapter/unit protocol не включается в продукт.
Dual Review остаётся отдельной проверкой Git-кандидатов и не меняется.

Эта работа не запускает 1С, не меняет source CF, snapshot/manifest, live ИБ,
executor installation, Hermes runtime configuration или deployment. Merge и
закрытие адресных PR разрешены владельцем после проверки кандидатов.

## Разрешённые рассинхронизации

- #35: merge текущего main сохраняет оба routing trigger и новые lifecycle
  правила; manifest пересчитан. Initial failure, FIRST-PASS AUTONOMY FAIL и
  KISS FAIL не переписаны.
- #39: старые диагностические факты отделяются от текущей общей lifecycle
  инструкции; OnStart transport не объявляется универсальным победителем.
- #7/#4: закрытие abandoned направления не считается доказанной переносимостью.
- #56: замечания reviewer требуют проверки; дополнение документации и
  проверка retained evidence не заменяют новый native run.
- README/diagnostics: #77/#79/#81 уже смёржены. Для #77 есть исторический
  installed ordinary-chat result; source merge и tool schema не доказывают
  текущее deployment состояние #80.
- Git skills: восстановлены три существующих authored пакета; не выбран новый
  project license и не импортирован сторонний код.
- По review #35 уточнены description/When to Use generic semantic skill и
  подробный reference checklist; версия 0.3.1. Pre-native lessons остаются
  доменно нейтральными.
- Review #7 не требует salvage adapter: `one_c_harness/harness.py` уже имеет
  strict JSON (26ff/159), строковые ключи (201ff), strict output (511ff).
  Не-пустые admitted question IDs (371ff) и exact answer binding (488ff)
  отвергают пустой questionId. Реальная подстановка отвергнута без output;
  40 harness tests прошли.
- [Пакет #55](../experiments/issue55-supplier-document-number/README.md)
  закрывает реальные false-PASS oracle cases без изменения production/
  instrumentation patches, request и native receipt. Это retained replay,
  не новый native run; **ACCEPT / COST FAIL** не переписывается.

## Проверки восстановления

`python3 -m unittest tests.test_skill_sources -v` проверяет complete resource
file sets, sizes, SHA-256, package identities, versions и существование
references. Проверка требует три non-plugin пакета; до восстановления она
действительно падала на отсутствии `headless-1c-probing`.

Временная реконструкция packages по manifest должна побайтно совпадать с Git
и активными installed copies. Отдельная parity-check выполняется без изменения
установки. Новый профиль/fresh-agent discovery и native canary здесь не
выполняются и не подразумеваются. Это source recovery, не acceptance всех
описанных historical runtime procedures.

Полная проверка: `python3 -m unittest discover -s tests -q`. Exact-head CI,
результаты двух reviewers и adjudication публикуются на обычных рабочих PR;
неинформативный reviewer означает INCONCLUSIVE, не разрешение на merge.

## Проверки и гигиена при продолжении

- #56 прошёл финальное двойное source review и exact-head CI Python 3.9/3.12;
  пять retained-evidence tests повторно прошли перед merge. Оба reviewer reports
  опубликованы в PR; неточные Gemini line offsets проверены lead по исходнику.
- В локальном прогоне #82 дважды сработали разные timing-sensitive tests:
  `test_batch_timeout_cleans_child_process_group` (PID-файл не появился до
  таймаута) и `test_runtime_fifo_receipt_is_bounded_and_cleans_process`
  (внешний deadline 4 s). Каждый адресный повтор прошёл. Эти тесты и runner
  в данной работе не изменены; причина нестабильности не установлена.
  Не повышаем таймауты и не ослабляем проверку ради зелёного результата.
- Удалены 30 remote-веток: каждый tip проверен как ancestor main, соответствующий
  PR — MERGED; push выполнен atomically с exact-tip leases, отсутствие refs
  прочитано обратно. Ещё две merged ветки уже отсутствовали. Непринятые и
  не-ancestor historical candidates сохранены; evidence/`.local/` не удалены.

## Остальные issue

Не закрываются автоматически внешние prerequisites и не относящиеся к этой
работе Goal: старая платформа (#3), другой бизнес-сценарий (#69), открытые
экспериментальные gates (#36/#41). История и retained `.local/` evidence не
удаляются при Git branch hygiene. Машинная уборка дистрибутивов не входит в
этот merge и описывается отдельно историческим storage audit.
