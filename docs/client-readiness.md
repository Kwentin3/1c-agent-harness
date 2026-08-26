# Готовность агентных клиентов

Harness не запускает модель и не включает универсальный adapter SDK. Для каждого
клиента отдельно фиксируются documented → installed → authenticated →
canary-proven → arm-proven.

## Текущая проверка

| Клиент/поверхность | Максимально доказанный уровень | Результат |
|---|---|---|
| Hermes subagent, baseline | arm-proven | 7/7 ответов, machine-valid locators, 45/47 oracle facts |
| Hermes subagent, indexed candidate | arm-proven | тот же контракт, 44/47 facts; индексы не приняты в MVP |
| AgentBridge Antigravity | arm-proven, quality gate failed | 7/7 machine-valid answers, 27 locators, 31/47 oracle facts, 0 dangerous false claims |
| standalone Codex/Claude/OpenCode/Gemini CLI | not installed | executable не найден в текущем workspace runtime |

Завершённый Antigravity arm доказывает, что bridge runner видит bounded read-only
bundle и может вернуть проверяемый артефакт общего контракта. Это не доказывает
равное качество модели: 31/47 ниже общего порога 90%. `arm-proven` описывает
техническую готовность поверхности, а не прохождение предметного eval.

## Внешняя предпосылка воспроизведения

Нужен авторизованный AgentBridge Antigravity runner с read-only монтированием
того же bundle. Клиент получает без изменений snapshot content ID, question
hash и locator rules из [`client-protocol.md`](client-protocol.md). Native
envelope извлекается тонким adapter без semantic repair. Подробный результат и
ограничения: [`antigravity-evaluation.md`](antigravity-evaluation.md).
