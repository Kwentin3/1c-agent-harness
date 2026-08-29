# Frozen fresh-agent challenge

Frozen before the issue #27 product patch.

## Prompt

> Подготовь рабочий контур для небольшой серверной доработки 1С. До запуска 1С зафиксируй точную идентичность целевой конфигурации и назови единственный поддерживаемый путь для native RED/GREEN. Не запускай 1С и не вноси бизнес-изменений.

## Executor boundary

The single fresh executor receives only:

- the prompt above;
- a clean repository tree from the candidate branch;
- published repository documentation and canonical skills;
- the existing laboratory.

The executor is not given issue #25 or PR #26, acceptance hashes, file counts, versions, snapshot or fixture directory names, a ready command, a private handoff, or an installed-only reference absent from the exact repository/canonical-skill tree.

The coordinator may start and time the challenge but must not supplement, correct, or complete the executor answer. Timeout or an incomplete answer is a failure. The limit is 600 seconds, there is one acceptance attempt, and parent takeover is forbidden.

## Prohibited actions

The challenge performs no native 1C calls and no business metadata or BSL changes.
