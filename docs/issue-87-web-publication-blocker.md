# Issue #87: блокер веб-публикации Jet demo

Статус сохранённых проверок на 2026-10-02: **GOAL INCOMPLETE**.
[Контракт задачи](https://github.com/Kwentin3/1c-agent-harness/issues/87).
Это handoff исследования, **не рабочий runbook и не доказательство дефекта платформы**.
Публикация этого документа не сопровождается новым запуском 1С/Apache или проверкой
текущей доступности executor.

## Цель и уже достигнутая часть

Владелец должен открыть настоящий веб-клиент 1С с dashboard Jet за предыдущий
календарный день и проверить «Обновить» через защищённый маршрут.
Прикладной кандидат — #85 / PR #86; его bounded native-приёмка описана в
[RESULTS](../experiments/issue85-owner-dashboard/RESULTS.md).
Native-расчёт/создание формы не равны browser E2E.

В отдельной сохраняемой demo-ИБ подготовлены JetTr 1.0.3.1, dashboard и тестовые
продажи. Apache загружает штатное веб-расширение и выдаёт часть ресурсов.
**Не подтверждены:** запуск приложения в браузере, отображение dashboard,
«Обновить», рабочая защищённая ссылка и сохранение работоспособности после рестарта.

## Окружение и границы

- Учебная Linux x86_64 платформа **8.5.1.1150**, `webinstt`, неизменённый `wsap24t.so`.
- Rootless Apache **2.4.58 (Ubuntu)** из извлечённых пакетов, worker MPM;
  сохранённая конфигурация: `ServerLimit 1`, `StartServers 1`.
- Отдельная файловая demo-ИБ; кластер/PostgreSQL не используются.
- Исторически проверенный listener: `127.0.0.1:18087`, публикация `/jet`.
- Runtime, demo-ИБ, резервная копия, диагностика — на выделенном executor,
  в task-owned `.local/`; дистрибутивы и сырые журналы в Git не публикуются.
- Source/snapshot/manifest и существующие ИБ immutable. Demo-ИБ **не disposable**:
  её и runtime не удалять при cleanup. Прошлый checkpoint подтвердил сохранность
  demo/backup, неизменность snapshot (5 099 файлов) и отсутствие rewrite.
- Не изменены DNS, firewall, общий reverse proxy, системные пакеты или Hermes.
  Внешний HTTPS/MFA ещё не настроен; DNS не является текущим блокером.

## Проблема A: штатная утилита не создаёт публикацию

`webinstt -publish -apache24 ... -confPath <файл httpd.conf>` завершает операцию
с кодом **1**, `default.vrd` не создаётся. В выделенном контрольном запуске:

```text
This operation requires superuser (root) privileges.
Otherwise the application might function incorrectly.
Exception: Cannot read <task-owned scratch config>.
Apache web server not found
```

Пути в цитате обезличены. Сохранённая трассировка прежней попытки показывала
успешное открытие conf: сообщение само по себе **не доказывает отказ доступа**.
Успешное открытие также не доказывает правильный разбор conf/обнаружение Apache.

Контроль по встроенной help: запуск из каталога бинарников платформы, библиотечное
окружение, Apache в PATH, отдельные scratch config и каталог публикации.
Результат прежний. Действующая публикация byte-identical, Apache не перезапускался,
root не использовался. В одной более ранней locale-попытке отдельно наблюдалось
`apache2: not found`; это дефект окружения той попытки, не объяснение всех отказов.

**Неизвестно:** почему publisher не распознаёт подготовленный Apache/config;
поможет ли стандартная установка Apache или однократный root. Считать их готовым
исправлением нельзя.

## Проблема B: ручная публикация не завершает native bootstrap

Ручная публикация использует `Alias /jet`, `SetHandler 1c-application`,
`ManagedApplicationDescriptor` и VRD `base="/jet"`, без rewrite.
Сохранённые наблюдения:

| Запрос | Результат |
|---|---|
| `/jet/` | 200, bootstrap указывает `/jet/en/`, `LANG=en`, `REDIRECT=true` |
| `/jet/en/` | 404; JSON-ошибка 1С: `Error executing the query GET to resource /en:` |
| `/jet/en/scripts/mod_bootstrap_bootstrap.js` | 404 от штатного handler |
| `/jet/scripts/mod_bootstrap_bootstrap.js` | 200 |
| `/jet/mainform.html` | 200 |
| `/jet/en/mainform.html` | 404 |

Это не обычное отсутствие Apache Alias: запрос доходит до `1c-application`.
Но это **не устанавливает** причину ошибочной интерпретации locale-пути.
HTTP 200 bootstrap/mainform не означает запуск приложения.

## Проверенные гипотезы — не повторять без нового различающего факта

| Контроль | Сохранённый результат |
|---|---|
| Симметричный Alias без конечного slash, VRD `/jet` | locale root/script по-прежнему 404; исходная настройка восстановлена |
| VRD `base="/jet/"` | locale root/script 200; отдельный сохранённый контроль также дал `/jet/en/mainform.html` 200; HTML содержит `REDIRECT=true`, но этот флаг **сам по себе не доказывает цикл**; UI не подтверждён; откат |
| Locale процесса RU | корень остаётся `LANG=en`; `/ru/` и locale script 404 |
| Отдельный пользовательский `SystemLanguage=RU` | тот же результат; настройка удалена/исходная восстановлена |
| Publisher из каталога бинарников | rc1, `Cannot read … / Apache web server not found`; VRD не создан |

Предыдущий rewrite не устранил redirect и убран. Не наращивать новые rewrite,
не перехватывать bootstrap JS, не менять бинарники и не обходить лицензию.
Это отрицательные результаты отдельных контролей, не универсальное исключение
любых проблем Alias, локали или прав.

## Что дали help и официальные источники

1. **CLI help exact runtime:** `webinstt` без аргументов выводит usage (rc1);
   `-help`/`--help` отвергнуты. Usage подтверждает `-apache24` и `-confPath` как
   полный путь к конфигурационному **файлу** Apache.
2. **Installed help:** `frntendt_root.hbk:form_WebDeployDlg`:
   > Start the utility from the directory that contains the binary files of the platform
   > (it requires dynamic libraries included in the platform).

   Архив SHA-256 `823e774cd3597dcd961147dc51493f1fd4664ee4cfadd48c34e6036c5b71d3cb`;
   извлечённый HTML member SHA-256
   `94aff03fe38dc8af05be9defce15f100e19010327cdcacef88b56135bbdd7827`.
   HTML member не имеет расширения; прежний reader его пропускал. Исправленный
   диагностический reader не является полным HBK parser. Сама статья содержит
   отставшие списки Apache: exact executable usage имеет приоритет для CLI.
3. [Официальная Linux-инструкция](https://1c-dn.com/anticrisis/tools-and-technologies/embedded-web-client/setting-up/)
   требует root для публикации, но также прямо говорит:
   > When publishing using the webinst utility, the user gets a diagnostic message
   > but the publication continues.

   Рекомендует worker MPM и не более одного рабочего процесса на файловую
   публикацию — эти настройки уже присутствуют. Это generic/older guide,
   **не подтверждённый рабочий пример 8.5.1.1150**.
4. [Карточка Linux учебной 8.5.1.1150](https://online.1c.ru/catalog/programs/program/36179915/)
   перечисляет один сеанс, отсутствие client-server, пользовательских паролей и
   ОС-аутентификации. Отдельный запрет веб-клиента в перечне не указан;
   **это не доказывает поддержку/работоспособность веб-клиента этой сборки**.
5. [Лицензионное соглашение](https://online.1c.ru/admin/documents/agreement.php?ID=16463663)
   разрешает обучение/разработку/отладку, не реальный учёт.
   [Комьюнити-лицензия](https://v8.1c.ru/podderzhka-i-obuchenie/uchebnye-versii/)
   — отдельный вариант, не используемая здесь лицензия и не проверенное исправление.

Research: шесть официальных страниц получены, десять source-local цитат проверены;
artifact integrity PASS, delivery DEGRADED: точная применимость и locale routing
остались unknown. Поиск был неполным, часть retrieval шла через direct HTTP,
две страницы нормализованы из Windows-1251. Тайм-аут worker не означает отсутствие
источников; lead завершил audit сохранённого материала. Независимого подтверждения
нет: источники одного vendor. Windows tutorial и translation overview не являются
доказательством требуемой Linux-конфигурации. Компактная обезличенная выписка:
[evidence-summary.json](../experiments/issue87-web-publication/evidence-summary.json).
Она производна от retained local evidence, не замена полного research corpus;
сырые бинарники, внутренние адреса и connection strings не опубликованы.

## Разбор Dual Review (`dr-6f8d031dde3e4c98`)

[DeepSeek](https://github.com/Kwentin3/1c-agent-harness/pull/88#issuecomment-5950129544) и
[Gemini](https://github.com/Kwentin3/1c-agent-harness/pull/88#issuecomment-5950130757)
проверили исходный handoff на `aefd8bd07d64ceabff99268da38676b1d9f2374b`.
Эта последующая коррекция и [supplement](../experiments/issue87-web-publication/review-context-supplement.json)
не входят в тот reviewed SHA. Новые runtime-пробы не запускались.

- **Принято:** диагностика была неполно передана ревьюверам. Публикуем обезличенные
  Apache/VRD и дополнительные сохранённые результаты. Это не доказательство исправления.
- **Принято с сужением:** HTTP 200 locale script и `mainform.html` — положительный
  факт доступности ресурсов, не доказательство открытия ИБ/веб-приложения. По флагу
  `REDIRECT=true` нельзя в одиночку вывести browser loop; формулировка таблицы исправлена.
- **Не подтверждено:** Gemini утверждает, что JS сравнивает текущий pathname и не
  редиректит повторно. Цитируемый обрезанный JS не содержит такого условия; ни полный
  JS, ни bound pure-base browser trace в reviewed evidence этого не показывают.
  Сохранённый browser trace показывает повторные загрузки и пустой интерфейс, но
  **не связывает** их с точным VRD/rewrite состоянием; использовать его как доказательство
  pure `base="/jet/"` loop также нельзя. Следующий дешёвый шаг — восстановить привязку
  полного bootstrap JS и существующего browser trace к контрольной конфигурации.
- **Повтор не нужен:** предложенный `/jet/en/mainform.html` при `base="/jet/"` уже
  дал 200; `AcceptPathInfo On` уже испытывался без устранения 404; абсолютный
  `ServerRoot` есть в сохранённом конфиге и в прочитанном publisher trace.
  Сохранённый vendor-config контроль также дал `Syntax OK`, но publisher rc1;
  это сужает, а не полностью исключает гипотезу о parser/config.
- **Нельзя усиливать:** официальное предупреждение root нефатально по generic guide,
  но это не исключает влияния прав на последующую операцию exact binary. Root-причина
  всё ещё неизвестна. Читаемость ИБ, её языки и mismatch base/Alias — гипотезы,
  не доказанные объяснения; statics 200 не доказывают открытие ИБ.
- **Отклонён способ проверки:** заглушка `apache2`, возвращающая выдуманную строку
  версии, не доказывает работу реального Apache. Если после анализа сохранённой
  трассировки нужен новый контроль, предпочтителен logger, делегирующий настоящему
  бинарнику и сохраняющий его actual stdout/stderr/exit. Отсутствие вызова logger
  не доказывает hardcoded paths. Новый запуск потребует отдельного admission.
- **Принято замечание о следующем этапе:** «получить generated config» — целевой
  milestone, не готовая диагностическая команда. Сначала использовать сохранённые
  trace/argv/env/config для локализации discovery/parser failure. Эталон другой
  версии может быть сравнением, но не exact-version acceptance.

Некоторые line anchors в отзывах выходят за размер reviewed файлов; проверка здесь
сделана по реальным JSON-полям и retained источникам, не по ошибочным номерам строк.
Несанитизированные пути, сырые секреты/connection strings в Git не нужны.
Advisory review не разрешает native-запуск, root, install, merge или deploy.

## Следующий ограниченный этап / вопрос для помощи

**Рекомендация, не разрешение на запуск:** получить конфигурацию, штатно
сгенерированную `webinstt` этой версии для распознанного Apache 2.4, и сравнить
с ручной публикацией. До этого не менять runtime и не продолжать перебор rewrite.

Нужен ответ: **какое минимальное штатное окружение/конфигурацию ожидает
`webinstt 8.5.1.1150 -apache24 -confPath`, и как подтвердить обнаружение Apache?**
Особенно полезен воспроизводимый vendor/example того же Linux training build,
а не общее описание другой платформы или утверждение «просто sudo».

При необходимости системной установки Apache, root, новой лицензии, DNS/ingress
сначала представить владельцу точный объём, последствия и rollback и получить
отдельное решение. Текущий запрос — только публикация контекста, не такое разрешение.

Приёмка следующего этапа: publisher success + его generated config; затем native
bootstrap без 404/redirect loop, настоящий dashboard и «Обновить». Отдельно
доказать retention/immutable-source, рестарт и защищённый доступ. До этого #87
остаётся открытой; PR #86 не merge, новый runtime/deploy не разрешены.
