# #90 — handoff документационного пакета

Статус: **DONE для локального docs пакета; GitHub proposals NOT_APPLIED**.
Рабочая ветка `docs/issue90-debts`, frozen base
`646273a44e47223d920911bdaec4bd35ae2b9ed6`, tree
`4bb37d169b631cb2c71501c862e6f89f24742de4`.
Коммит этого документа и соседних docs передаётся parent для объединения;
самостоятельных push/PR, review dispatch, merge/closures нет.

## Что передано

- README/ROADMAP и актуальные summaries coding admission, native web runbook,
  #71/#73 согласованы с #91 CLOSED и #86/#88 MERGED.
- `goal91-final.md` получил только отдельный post-merge pointer; весь прежний
  текст/source/installed identity/receipt hashes сохранён byte-for-byte.
- `issue90-debt-disposition.md`: семь строк #85/#87/#71/#73/#36/#37/#41,
  доказательства, пробелы, принятый scope и safe owner decisions.
- `.local/issue90-debt-proposals.json` (ignored, **не в коммите**): два точных
  body patches #91/#92 с исходными updatedAt/body SHA256 и полными proposed bodies;
  семь terminal comment текстов и conditional closure/keep-open решения.
- Local evidence: `issue90-debt-live.json`, `issue90-debt-linked.json`,
  `issue90-debt-pr-api.json`, `issue90-debt-validation.json`; небольшие read/write
  docs scripts `update-debt-docs.py`, `validate-debt-docs.py` в assigned `.local`.
  Parent должен забрать JSON до удаления этого worktree; cherry-pick его не переносит.

## Фактически выполненные команды и результаты

Все команды из assigned worktree, без обращения к runtime/credentials.

| Команда / проверка | Результат |
|---|---|
| `pwd; git branch --show-current; git rev-parse HEAD; git status --short` | assigned worktree, `docs/issue90-debts`, exact frozen base, исходно clean |
| `gh issue view N --repo Kwentin3/1c-agent-harness --json number,title,body,comments,state,url,updatedAt` | полные bodies/comments #90/#91/#92/#85/#87/#71/#73/#36/#37/#41; linked #89/#72/#74/#39/#38 отдельно сохранены |
| `gh api repos/Kwentin3/1c-agent-harness/issues/N` | counts для целевых old issues совпадают: #85 4, #87 17, #71 2, #73 3, #36 14, #37 4, #41 3; #91 53, #92 0 |
| Повторное `gh issue view 90` | учтён новый progress comment [6033635310](https://github.com/Kwentin3/1c-agent-harness/issues/90#issuecomment-6033635310); body контракт не изменён, comments теперь 2 |
| `gh api repos/Kwentin3/1c-agent-harness/pulls/{86,88}` | оба merged; SHA #86 `9fcb7ad2493b6fa8e53c5922cf139fe19339bfc0`, #88 `646273a44e47223d920911bdaec4bd35ae2b9ed6` |
| `gh api .../commits/SHA/check-runs?per_page=100` | на каждом merge SHA Python3.9/3.12 completed/success; exact head CI тоже success |
| `gh api .../commits/SHA/status` | legacy pending при пустом statuses; не называть провалом check-runs |
| `gh api .../branches/main` | main равен frozen base/merge #88 |
| `gh api .../pulls/{72,74,39}` | merged; source citations закреплены полными merge/head SHA |
| `python3 .local/validate-debt-docs.py` | 2 exact body patches / 7 disposition, JSON и old-body hashes согласованы, local links существуют; goal91 old bytes preserved, historical checkpoint/receipts unchanged |
| `git diff --check` | PASS; staged повторяется перед commit |

Один первоначальный composite read-only validation был отклонён terminal hook
с сообщением о gateway restart, хотя команда не содержала service action.
Проверка документационных байтов отдельным прозрачным локальным Python-script
прошла; gateway/runtime не менялись. Native/unit suite не запускалась: docs-only
проверки не требуют платформы и не должны открывать новый native budget.
Own local artifacts меньше 2MiB; unknown/evidence не удалялись.

## Решения parent перед GitHub записью

1. Перечитать текущие #91/#92 bodies/state/comments, проверить updatedAt и body
   SHA256 proposals; это preflight, не обещание атомарной CAS GitHub. Если изменилось,
   заново adjudicate точный patch, не перезаписать чужую правку.
2. #85/#87: proposed completed **только в принятой #91 границе**, не nonzero/RLS/
   production PASS. Перед закрытием опубликовать точный terminal evidence итог.
3. #71/#73: не completed широких первоначальных promises. Получить явное принятие
   design/prototype и retained-receipt scope либо оставить один конкретный
   incident/source acceptance остаток, связанный с #92.
4. #36/#37/#41: оставить OPEN до конкретного owner disposition. Cancellation
   not_planned не подтверждена; #41 mistaken retirement явно отменён. Никаких
   retry/BankReceipt/compile-hardening запусков ради административного закрытия.
5. Git-tracked docs через обычный parent PR/review workflow; local commit не является
   опубликованным handoff/closure. После отдельно разрешённых writes проверить readback.
   Source acceptance, installed revision, current access и historical runtime
   receipts всегда разные утверждения. #90 live-source приёмка этим пакетом не выполнена.
