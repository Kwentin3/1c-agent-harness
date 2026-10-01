# Историческая диагностика headless probe (issue #37)

## Статус и граница

Это короткая запись уроков конкретной аварии, а не выбор постоянного транспорта
и не доказательство бизнес-правила `BankReceipt`. Источник —
[issue #37](https://github.com/Kwentin3/1c-agent-harness/issues/37).
Первый вывод о client-local probe затем был сужен после server-crossing timeout;
постоянный request/response contract вынесен в #38.

Текущие инструкции: [#38 baseline и его ограничения](issue-38-headless-request-response.md),
[shared task route](../README.md), [канонические скилы](../skills/README.md).
Исторические marker/argv не являются готовой командой текущего runner.

## Что установила диагностика

- Task-specific probe, поставленный после `StandardSubsystemsClient.OnStart()`,
  не достиг записи receipt до timeout. Это ошибка порядка instrumentation,
  не доказательство невозможности headless выполнения на платформе.
- Harmless client-local probe, вставленный первым в `OnStart` с ранним `Return`,
  выдал receipt. Это ещё не доказывает серверный вызов.
- Последующие диагностические шаги исследовали exported server-call module,
  server-side `TextWriter` и disposable fixture stages до `BankReceipt.Fill`.
  Они не являются GREEN бизнес-правила и не доказывают корректность заполнения.
- Успешный `CREATEINFOBASE` и Designer load не гарантируют, что новый client/server
  путь компилируется и исполняется при первом `ENTERPRISE` входе.
- Runtime compile error `{ManagedApplicationModule(94,36)}: Expecting ')'`
  относится к throwaway probe. Точная причина parser failure не установлена;
  она не превращается в универсальное утверждение о языке.

## Переносимый урок

Сначала определить execution layer и точки наблюдения. Для раннего headless
probe сохранить неизменённый стандартный код, вставить task-owned блок внутри
существующего обработчика, собрать точную changed-file closure и проверять
свежие client/server identities. Отсутствие receipt, timeout и compile failure
нельзя переименовывать в business RED.

Наблюдать реальную операцию и реально существующие поля. В исследованном Jet
`BankReceipt.PaymentDetails` содержит `Document`, `PaymentAmount`, `Amount`,
но не `BankAccount`; поле заголовка и строки нельзя смешивать. Эти статические
факты относятся к исследованному snapshot, не ко всем конфигурациям.

## Что не установлено

- почему стандартный startup не вернулся;
- универсальность маршрута early OnStart для всех server APIs;
- корректность бизнес-правила #36 и заполненных данных;
- преимущество OnStart перед EPF или Test Manager/Test Client.

Новый native эксперимент требует отдельного бюджета и свежего task contract.
Этот документ не разрешает retry #36, GREEN, production patch или новый запуск.
