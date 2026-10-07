# #90 — disposition долгов после #91

Документационная сверка 7 октября 2026, без native/deploy и без GitHub writes.
#91 CLOSED; #86/#88 MERGED. #90 остаётся отдельной продуктовой Goal свежего ЖР,
а #92 — backlog расширений. Предложения ниже **не означают**, что старые issues
уже закрыты: при сверке все семь OPEN. Исторические checkpoints не переписаны.

## Post-merge source и CI

| PR | Merge commit в main | Проверенные checks на этом SHA |
|---|---|---|
| #86 | [`9fcb7ad2493b6fa8e53c5922cf139fe19339bfc0`](https://github.com/Kwentin3/1c-agent-harness/commit/9fcb7ad2493b6fa8e53c5922cf139fe19339bfc0) | [Python 3.9/3.12 SUCCESS](https://github.com/Kwentin3/1c-agent-harness/actions/runs/37587456237) |
| #88 | [`646273a44e47223d920911bdaec4bd35ae2b9ed6`](https://github.com/Kwentin3/1c-agent-harness/commit/646273a44e47223d920911bdaec4bd35ae2b9ed6) | [Python 3.9/3.12 SUCCESS](https://github.com/Kwentin3/1c-agent-harness/actions/runs/37588975039) |

REST API подтвердил merged=true, merge times 07:27:41Z / 07:42:16Z и main
`646273a44e47223d920911bdaec4bd35ae2b9ed6`. Каждый merge имеет два completed/success
check-runs, с совпадающим `head_sha`; legacy combined status `pending` имеет
ноль statuses и не заменяет check-runs. [Owner merge completion](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6033389802).

Исполненный/установленный source остаётся
`eaab4cf3b6c563e11388f02676acb54f0302d004`; [исполненный отчёт](https://github.com/Kwentin3/1c-agent-harness/blob/2dc5f79416e450b252b85c60a0e23578086015d0/docs/goal91-final.md)
и receipt hashes не заменяются merge SHA. Merge/CI — source acceptance, не новая
native-приёмка, deployment или доказательство доступности demo сейчас. Runtime
сведения здесь — опубликованное evidence предыдущих окон, не новое чтение среды.

## Компактная таблица решений

| Issue | Доказано | Не доказано / остаток | Принятый scope и безопасный disposition / owner decision | Закреплённые citations |
|---|---|---|---|---|
| #85 | Strict native dashboard oracle PASS, attempt3, 3/4; расчёт, spreadsheet/top5, form-server creation, empty/loss/repeat/date cases. #91 отдельно подтверждает настоящий empty-day web/Refresh. | Restricted-role/RLS, ties, zero-value invoices, nonzero web, другие runtimes; observed state comparison не глобальный write audit. | Узкий прикладной slice принят через #91, source #86 merged. Предложить terminal comment и **completed** в этой границе; расширения #92, не расходовать четвёртый слот. | [Native terminal / exact head](https://github.com/Kwentin3/1c-agent-harness/issues/85#issuecomment-5947242321), [результат](https://github.com/Kwentin3/1c-agent-harness/blob/264ad94183509f15cfccfc96c7cdaa65d9957fce/experiments/issue85-owner-dashboard/RESULTS.md), [scope #91](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6015496546) |
| #87 | Local native reference, causal resource aliases, real dashboard/Refresh и restart; позднее защищённая постоянная demo, восстановление и login/Refresh/Exit приняты в #91. | Nonzero web/workflow, полный host reboot/credential recovery в финальном окне, универсальная web/production поддержка; текущая доступность не перечитана. | Принята protected delivery с допустимым empty-day. Предложить **completed** с terminal boundary; nonzero/workflow #92. Не объявлять первоначальную ненулевую цель исполненной и не давать новый lifecycle допуск. | [Local intake](https://github.com/Kwentin3/1c-agent-harness/issues/87#issuecomment-5968528098), [persistent delivery contract](https://github.com/Kwentin3/1c-agent-harness/issues/89#issuecomment-6019437901), [final completion](https://github.com/Kwentin3/1c-agent-harness/issues/91#issuecomment-6032686960) |
| #71 | KISS design и bounded deterministic prototype; #72 merged. Последующее ТЖ/ЖР развитие принято отдельно. | Широкий исходный incident/RAC/OS/DB/runtime→code сценарий и root cause не доказаны prototype или журналами. | Предложить закрыть **completed только после явного принятия владельцем сокращённого design/prototype контракта**; иначе OPEN с одним остатком: выбор/приёмка конкретного incident source в #92. #91 не расширяет prototype до production. | [Prototype checkpoint](https://github.com/Kwentin3/1c-agent-harness/issues/71#issuecomment-5728455948), [design at merge](https://github.com/Kwentin3/1c-agent-harness/blob/8a9b31ac805923ba08f31017b9efd7b167fe4669/docs/issue-71-runtime-diagnostics.md) |
| #73 | Real retained native-run receipts: 28 records, 21 completed / 3 exits / 4 timeouts; investigate→expand трёх exits; #74 merged. | Не текущие sessions/cluster/incident, не root cause; historical mtime не дата runtime event. Task-local source canary не perpetual installed proof. | Предложить **completed только при подтверждении владельцем retained-receipt slice**, не исходного live-cluster обещания; иначе OPEN с конкретным остатком incident/source acceptance #92. Свежий ЖР/current installed positive selection/page/record — #90, в #91 NOT_RUN. | [Real bounded checkpoint](https://github.com/Kwentin3/1c-agent-harness/issues/73#issuecomment-5730334566), [tracked receipt at merge](https://github.com/Kwentin3/1c-agent-harness/blob/05f7876b87201df5cd631ead8fb2881dcce88d9c/docs/issue-73-runtime-diagnostics-live-receipt.json) |
| #36 | Corrected Round2 context tournament выбрал D; это отдельный context PASS. Native original/v2/v3/v4 terminal **PRODUCT FAIL**; GREEN не исполнен. | BankReceipt business RED/GREEN, patch correctness и product integration не доказаны. | **Оставить OPEN** до решения владельца: архивировать terminal experiment без PASS либо выбрать отдельно замороженного преемника после #41. Отмены направления не найдено: автоматическое not_planned запрещено. Один остаток — owner disposition, связать #92; ни retry, ни бюджет не переносить. | [Context adjudication](https://github.com/Kwentin3/1c-agent-harness/issues/36#issuecomment-5470494328), [v4 terminal FAIL / hashes](https://github.com/Kwentin3/1c-agent-harness/issues/36#issuecomment-5471980970) |
| #37 | Startup-order/client-local smoke, отдельная server-crossing граница; transport-neutral архив #39 принят. #38 и #91 позже доказали конкретные working routes, текущий materializer получил process-owner regression. | Почему standard startup ждёт; универсальность early OnStart; enforcement запрета helper вне .local и весь первоначальный isolation/root-cause контракт не закрыты архивом или поздним PASS. | **Оставить OPEN** с одним остатком: owner решает, требуется ли отдельный write-isolation enforcement successor в #92 либо архивная disposition. Не выдавать #39 docs acceptance за original-contract completed. | [Reopen](https://github.com/Kwentin3/1c-agent-harness/issues/37#issuecomment-5470798489), [archival boundary](https://github.com/Kwentin3/1c-agent-harness/issues/37#issuecomment-5927812944), [archive exact source](https://github.com/Kwentin3/1c-agent-harness/blob/cf0b3af3217513359c828dad86941c7b19f8a62f/docs/issue-37-headless-probe-observability.md), [current process-owner evidence](https://github.com/Kwentin3/1c-agent-harness/blob/eaab4cf3b6c563e11388f02676acb54f0302d004/docs/goal91-coding-admission.md) |
| #41 | Harmless compile-hardening contract frozen; client-neutral, ошибочная Antigravity-retirement closure отменена. Поздний #38 server route/current #91 native не являются exact #41 receipt. | Smoke с обеими success/intentional server failure ветками и всеми error-only branches exact contract не подтверждён. | **Оставить OPEN**: owner выбирает необходимость самостоятельного gate или явно отменяет как not_planned. Нельзя отменять по association с Antigravity и нельзя автоматически запускать старый <=120s бюджет. Остаток/решение — #92. | [Freeze / exact contract hash](https://github.com/Kwentin3/1c-agent-harness/issues/41#issuecomment-5471983918), [closure correction](https://github.com/Kwentin3/1c-agent-harness/issues/41#issuecomment-5927735665), [последующий #38 route](https://github.com/Kwentin3/1c-agent-harness/issues/38#issuecomment-5494494937) |

Comment anchors закрепляют конкретную запись discussion, но её body может редактироваться;
source/receipt citations закреплены полным SHA, historical native hashes сохранены
в cited terminal receipts. Ни один terminal FAIL не повышен до PASS. Последующее
принятое развитие перекрывает конкретные route/reader потребности, не автоматически
все критерии старых контрактов. Новые tests/native здесь не выполнялись.

## Передача владельцу / parent

Точные предложения body patches #91/#92 и семь terminal comments/closure decisions
подготовлены локально в `.local/issue90-debt-proposals.json`, **не применены**.
Перед записью parent обязан перечитать body/comments/state, проверить unchanged
`updatedAt` и SHA256 body (не атомарная GitHub CAS), adjudicate scope и получить
недостающие owner decisions. #36/#37/#41 не закрывать автоматически; #71/#73
не закрывать как весь первоначальный production контракт. Только после публикации
проверить readback и актуализировать статус. Source docs commit не является
GitHub issue closure. Parent выполняет обычный PR/review workflow; этот пакет
не push/PR и не авторизует merge/release.
