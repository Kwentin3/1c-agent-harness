# Готовность агентных клиентов

Harness не запускает модель и не включает универсальный adapter SDK. Для каждого
клиента отдельно фиксируются documented → installed → authenticated →
canary-proven → arm-proven.

## Текущая проверка

| Клиент/поверхность | Максимально доказанный уровень | Результат |
|---|---|---|
| Hermes subagent, baseline | arm-proven | 7/7 ответов, machine-valid locators, 45/47 oracle facts |
| Hermes subagent, indexed candidate | arm-proven | тот же контракт, 44/47 facts; индексы не приняты в MVP |
| AgentBridge Antigravity | canary-proven | auth ready, `AGY_READY`; два frozen arm attempts завершились `cli_exit_nonzero` |
| standalone Codex/Claude/OpenCode/Gemini CLI | not installed | executable не найден в текущем workspace runtime |

Canary Antigravity доказывает bridge runner и credential context, но не доступ к
локальному snapshot. Оба attempts одной и той же frozen задачи упали до создания
answer artifact, поэтому считать Antigravity вторым работающим клиентом нельзя.

## Внешняя предпосылка второго arm

Нужен один из вариантов:

1. исправленный Antigravity runner с read-only доступом к выбранному workspace;
2. установленный и однократно авторизованный второй coding-agent CLI, который
   поддерживает headless запуск и явную read-only policy.

После этого клиент получает без изменений snapshot content ID, question hash,
answer schema и locator rules из [`client-protocol.md`](client-protocol.md). Новый
универсальный adapter или третий гипотетический клиент не требуется.
