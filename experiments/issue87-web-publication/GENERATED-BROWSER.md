# #87: штатный publisher PASS, браузерный путь остаётся неработающим

Актуальный checkpoint: **2026-10-03, GOAL INCOMPLETE**.
[Contract](https://github.com/Kwentin3/1c-agent-harness/issues/87),
[санитизированные результаты и hash anchors](generated-browser-evidence.json),
[реальные generated/derived config и VRD с объявленной санацией](generated-config-comparison.json).
Это проверенная диагностическая точка, **не working web runbook**.

## Что теперь подтверждено

Домашний оператор выполнил [один owner-approved root publisher-контроль](https://github.com/Kwentin3/1c-agent-harness/issues/87#issuecomment-5954599963).
Неизменённый `webinstt 8.5.1.1150` выдал `Publication successful`, exit 0;
Apache config и VRD реально созданы. Старый non-root отказ — доказанный UID-gate,
а не провал Apache discovery. Успешная генерация не доказывает браузерный запуск.

Hermes независимо сверил защищённый receipt с retained копией, manifest runtime,
**1011 regular files / 230 внутренних относительных symlinks**, root-owned parents
и hashes generated config/VRD. Apache `-t` и `-M` как UID 10001 прошли.
Эти проверки повторены после включения домашнего хоста 2026-10-03.
Host Compose/override/rollback пока подтверждены оператором, не самостоятельным
чтением host-level конфигурации Hermes. Никаких новых root-запусков нет.

Protected runtime manifest SHA-256:
`1797046567edf5ab6f43ddfe6e735daa6113ef9cb10dd7051a2438a1b0d69789`.
Generated Apache config: `0c1640f8489fbf11a0f82746bcc73cb0da3de38cfc047e9864792fac3c7a2b3a`.
Generated VRD: `72ac8ebff96b5d2fad20e48d0fbbef08f1360035f7322cf955370ea9e4b1ad22`.

## Изолированный браузерный контроль

Обычный пользователь UID 10001, тот же Apache 2.4.58 worker MPM и sealed runtime.
Отдельная физическая копия `demo-ib/1Cv8.1CD`, отдельный task-owned каталог,
listener только `127.0.0.1:18089`. Активная `/jet` публикация не изменяется и
не перезапускается. Generated Alias/SetHandler/ManagedApplicationDescriptor
перенесены с заменой scratch путей. VRD сохраняет native namespace и base
`/jetcontrol`; меняется только IB reference на disposable copy и безопасный scope:
WS/analytics/HTTP services выключены, `AllowOverride None` вместо `All`.

Это **safe derivative**, не испытание всех byte-identical publisher defaults.
Включать WS/analytics/OData в сохраняемой demo автоматически нельзя.
Generated имя `standardOdata` использовано с точным регистром; исправление
прежнего ручного `standardOData` само по себе не устранило сбой.

Один initial browser control и один focused network probe (каждый со своим
обычным Apache launch и fresh Chromium session), затем один HTTP-only documented
`L`/Accept-Language контроль с третьим Apache launch; Designer/ENTERPRISE CLI/root=0.
Это настоящие native web-extension HTTP обращения, не статическая lane.
В bounded пробах не было rewrite, JavaScript replacement, UID/version подмены
или изменения vendor binaries.

## Точная наблюдаемая граница отказа

Native стартовая HTML-страница возвращает:

```text
BASE = "/jetcontrol/en"
LANG = "en"
REDIRECT = true
<base href="/jetcontrol/en/">
```

| Native GET | Ответ | Значение |
|---|---|---|
| `/jetcontrol/` | 200, `text/html` | только bootstrap, не UI |
| `/jetcontrol/scripts/mod_bootstrap_bootstrap.js?sysver=8.5.1.1150` | 200, `application/javascript`, 8121 bytes | resource существует без language prefix |
| `/jetcontrol/en/scripts/mod_bootstrap_bootstrap.js?sysver=8.5.1.1150` | 404, platform JSON | `GET to resource /en/scripts/mod_bootstrap_bootstrap.js` |
| `/jetcontrol/en/` | 404, platform JSON | `GET to resource /en` |

Fresh Chromium запросил native `/en/` script и splash resources и получил 404;
приложение не было открыто. Это **не только `REDIRECT=true` inference**: сохранены
HTTP headers/bodies и реальные browser requests/responses.

В initial session был `Cannot read properties of null (reading 'indexOf')`
при чтении content-type в native bootstrap. Focused probe получил нормальный
JSON content-type у 404, без этой JavaScript exception. Поэтому null-error —
отдельное наблюдение первого старта, **не установленная стабильная root cause**.
Новый bound test не воспроизводил исторический trailing-slash loop;
тот остаётся отдельным результатом [RESUMED.md](RESUMED.md).

[Первичная общая документация 1Ci](https://kb.1ci.com/1C_Enterprise_Platform/FAQ/Development/Localization/Parameters_that_affect_user_interface_language/)
описывает добавление выбранного языка к base URL как штатное поведение.
Отсюда `/en` в HTML не является сам по себе ошибкой; наблюдаемая проблема —
что **наш exact runtime/Apache route не принимает созданный им locale path**.
Документация не устанавливает причину этого exact-build отказа.

Дополнительный HTTP-only контроль по документированному `?L=en` / `?L=ru`
и совпадающему `Accept-Language` **не изменял** Apache/VRD/env. Оба root GET дали
`BASE="/jetcontrol/en"`, `LANG=""`, `REDIRECT=true`; соответствующие `/en` и `/ru`
root/script GET получили platform JSON 404. То есть явный request-level выбор
языка тоже не разблокировал dispatch; не переносим результат на все версии 1С
и не заявляем, что русские localization resources отсутствуют (файлы обнаружены).
Это отдельный HTTP контроль, не третий browser session. Новый process завершён,
повторно созданная disposable IB copy удалена; demo hash прежний. Raw receipts:
`generated-browser-control/explicit-language/`, supplemental section в evidence JSON.

## Сохранность и очистка

Сохраняемые demo/backup и config/VRD byte-identical до/после, исходная front door
проверка вернула `ready` с прежними CF/manifest hashes и всеми **5099** файлами.
Два task Apache дерева завершены; по `/proc` нет принадлежащих probe процессов
или listener 18089. Прежний 18087 остаётся loopback-only. У первого script
попытка socket bind после остановки вернула false из-за TCP TIME_WAIT;
это не surviving listener. Состояния TCP и процессный checkpoint сохранены отдельно.

Удалён **только** disposable `generated-browser-control/ib/1Cv8.1CD` после проверки
отсутствия probe процессов. Demo, backup, runtime, source, config и evidence
сохранены. Raw evidence на executor:
`.local/web-demo/generated-browser-control/` (15 retained artifacts на safety freeze,
плюс `safety.json`): native HTML, DOM, screenshot (не основной evidence), Apache
logs, config/VRD, exact HTTP bodies, initial/network receipts и safety inventory.
Подготовительные diagnostic scripts находятся в игнорируемой `.local/web-demo/`
Hermes workspace; они не продуктовый runner и не обещание clean-bootstrap replay.

## Exact-review adjudication

[DeepSeek source review](https://github.com/Kwentin3/1c-agent-harness/pull/88#issuecomment-5966135246)
относится к `e1f57c6`; [Gemini](https://github.com/Kwentin3/1c-agent-harness/pull/88#issuecomment-5966135597)
— **INCONCLUSIVE**, runner `canonical_result_too_large`. Review автоматически
не перезапускается; это технический провал, не PASS. Current HEAD содержит
дополнительный HTTP probe и correction, поэтому старый review не покрывает его.

Приняты transparency findings F2/F6: опубликованы sanitized **реальные** generated
и derived config/VRD, raw/sanitized hashes разделены. Lead read retained originals:
оба base буквально `/jetcontrol` без завершающего slash; это не rename base.
Прочитать этот факт можно без ещё одного root/native run; он не является новой
гипотезой исправления. Добавлены accounting scope и актуальная дата. Вопрос о
дополнительных namespace declarations/formatting явно отмечен как serialization,
а не скрытая semantic delta. Две проверки root/browser не стали release gate.

## Следующая граница

Root publisher prerequisite закрыт; hostname/DNS/ingress и demo данные не причина
наблюдаемого `/en` bootstrap отказа. Повторять прежние Alias/locale-env/cwd/
AcceptPathInfo/slash controls без нового различающего факта нельзя.

Нужна адресная диагностика locale dispatch на exact web-extension/runtime,
либо воспроизводимый независимый штатный reference route. Пока **не установлены**:
дефект платформы, лицензирование как причина, несовместимость Apache и sufficiency
изменений VRD. Из этого checkpoint не следует необходимость другого runtime,
кластера, PostgreSQL, rewrite, proxy frontend или нового harness.

Dashboard/Refresh, повтор после restart и защищённый owner ingress остаются
NOT_PROVEN; merge/deploy/закрытие #87 не выполнены.
