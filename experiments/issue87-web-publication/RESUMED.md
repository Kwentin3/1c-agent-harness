# #87 — возобновление Goal: найден root-gate штатного publisher

**GOAL INCOMPLETE; работа возобновлена владельцем.** Достигнута конкретная
граница: следующий штатный publisher-контроль требует отдельного разрешения root.
Это не завершение Goal и не утверждение, что root исправит веб-клиент.

Машиночитаемые наблюдения и source hashes: [resume-evidence.json](resume-evidence.json).
Исходный [handoff](../../docs/issue-87-web-publication-blocker.md) и прежние отзывы
сохраняются как история; прежний вывод «root-причина неизвестна» для publisher
заменён ниже. Отзывы на старый SHA не распространяются на это уточнение.

## Подтверждённые результаты

### 1. Полный JS и один привязанный browser-контроль

В неизменённом bootstrap установленной 8.5.1.1150 флаг `window.REDIRECT`
попадает в условие, вызывающее `window.location.replace`; проверки текущего
pathname в этой ветке нет. Сохранены полный JS, его SHA-256 и оба HTML-ответа.

Один свежий браузерный запуск: только VRD `base="/jet/"`, действующий конфиг
без rewrite, хеши конфигурации/VRD до/во время/после. Оба корня возвращают
одинаковый bootstrap с `REDIRECT=true`; записано **204 навигации на `/jet/en/`**,
`mainform.html` не запрошен. Публикация затем восстановлена byte-for-byte.

Это доказывает loop **для этого привязанного чистого контроля**, а не для
непривязанных старых browser traces и не для любой публикации 1С.
Гипотеза «добавить конечный slash — приложение уже заработало» закрыта.

### 2. Publisher обнаруживает настоящий Apache

В полном сохранённом `parser.trace` настоящий `apache2 -v` возвращает
`Apache/2.4.58`, pipeline возвращает `2.4.58`, и publisher читает эти байты.
Он также открывает установленный `wsap24t.so` и читает конфиг.
Следовательно, общее «Apache not found» не локализует отказ на проверке версии.
Установка Apache вслепую не является обоснованным следующим шагом.

### 3. Ненулевой UID сам вызывает отказ компонента публикации

Два bounded запуска неизменённого publisher на отдельных копиях конфигурации
под GDB дали сначала `core::IOException` из `vrscoret.so`, затем обёртку
`vrscore::VResourceDeploymentException` и сообщение `Cannot read conf`.
Ранее возникающие и обработанные startup-исключения отделены от этого отказа.

После этого **без запуска inferior** просмотрен control flow того же ELF:

- `vrscoret.so + 0x3c2a40`: вызов штатного `getuid`;
- `+ 0x3c2a45`: проверка возвращённого UID на ноль;
- `+ 0x3c2a4f`: при ненулевом UID переход к `+ 0x3c4b15`;
- этот путь создаёт и выбрасывает `core::IOException`;
- динамически зафиксированный return offset этого throw — `+ 0x3c4b40`.

Идентичность `vrscoret.so`: SHA-256
`29aee4993151419c206bc42dba288e5fdd7ac8b8a70a994023fc5a65131a9612`.
Сырые debugger logs/статический listing остаются в task-owned evidence executor;
бинарники и сторонний код в продукт/Git не копируются.

**Вывод:** UID zero — необходимая предпосылка наблюдаемого пути публикации
этой exact сборки. Generic help о продолжении после root-warning относится
к предупреждению CLI; не исключает последующий root-gate внутри компонента.
Успешное `open/read` конфига также не исключает этот gate.

**Не доказано:** что root достаточно для успешной публикации; что generated
публикация устранит loop; что учебный веб-клиент запрещён либо дефектен.
Подмена `getuid`, patch бинарника, LD_PRELOAD и изменение условий лицензии
не рассматриваются.

## Минимальный запрос владельцу: один root-контроль

Разрешить **один** UID-zero запуск штатного `webinstt -publish -apache24`
той же сборки внутри существующего executor-контейнера, в отдельном
**root-owned staging**, без системной установки Apache и без постоянного sudo.

Перед привилегированным запуском нужны:

1. Административный способ однократного исполнения на домашнем executor;
   обычный SSH executor не получает постоянных новых прав.
2. Root-owned staging для проверенного publisher/runtime dependency closure,
   реального Apache и отдельного scratch config/publication; не выполнять
   root-процесс непосредственно из пользовательски записываемого workspace.
   Идентичности staged bytes сверяются с retained manifest до исполнения.
3. Ссылку на новую task-owned sandbox ИБ/директорию в connection string;
   **не открывать/не копировать/не менять сохраняемую demo или исходные ИБ**.
   Для этой проверки требуется только генерация конфигурации, не запуск ИБ.
4. Штатные бинарники, реальные version outputs, отдельная конфигурация;
   никаких rewrite, подмены bootstrap, fake version, UID/library hooks.

Сигнал успеха: exit 0, новый VRD и generated Apache-конфиг, затем проверка
конфига реальным Apache в непривилегированном режиме. Если возникает другой
отказ — сохранить точный результат и остановить этот контроль; не расширять
права/инсталляцию автоматически. Ничего не переносить в действующую публикацию
до просмотра generated diff и следующего непривилегированного admission.

Rollback: завершить только отмеченный one-shot процесс, сохранить обезличенный
результат, удалить **только** созданный root-owned staging по проверенному
inventory. Существующие runtime/demo/backup/snapshot/сервисы сохраняются.
Firewall/DNS/shared proxy/ingress/merge/релиз не входят в это разрешение.
Доступ к настоящему dashboard, Refresh и защищённый ingress остаются последующими
критериями Goal, не результатом данного publisher-контроля.

## Проверенная сохранность и воспроизведение доказательств

- Canonical snapshot совпал с prior prepare-audit: **5 099 файлов**.
- Действующие Apache-конфиг и VRD восстановлены; rewrite отсутствует.
- Только owned Apache parent/worker остались; debugger/browser/publisher детей нет.
- Listener — только loopback. Demo и `demo-before-web.dt` сохранены.
- В debugger-проверках demo/backup/бинарники/config/VRD совпали до/после по SHA-256.
- Root/Designer/ENTERPRISE запусков этого возобновления — **0**;
  browser controls — **1**, publisher invocations под GDB — **2**.
- GDB 15.1 и минимальные зависимости взяты из официального Ubuntu package index,
  версии и SHA-256 закреплены; archives total **7 786 792 bytes**.
  Это временный внешний diagnostic в `.local/`, не продуктовая зависимость;
  системные пакеты не установлены, платформа не менялась. После диагностики
  удалены только task-created `resume-gdb/root` и `resume-gdb/downloads`;
  raw logs, scratch configs, manifest и source evidence сохранены.

Source receipts доступны на executor: `resume-base-browser/result.json`,
`resume-gdb/{probe,branch}/result.json`, `resume-gdb/parser-static.txt`, manifest.
В локальном task evidence сохранены `resume-*.json` и минимальные scripts.
Новая root-проверка **не выполнялась**. Обычный CI проверяет репозиторий,
но не является повтором native/browser evidence.
