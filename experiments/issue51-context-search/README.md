# Issue #51 — дешёвый поиск рабочего контекста

## Verdict

**`RG BASELINE WINS`**

Обычный `rg` уже даёт достаточный context packet. Минимальный каталог ускоряет сами lookup-вызовы, но не весь проход и более чем удваивает переданный контекст. Готовый code index не индексирует BSL и для поиска по BSL вызывает тот же `ripgrep`; измеримого продуктового выигрыша нет.

Ничего не интегрировать. Не добавлять index, MCP server или каталог в product dependencies.

## Frozen input

- JetTr `1.0.3.1` hierarchical dump;
- manifest SHA-256 `70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691`;
- 5,099 regular files / 61,789,112 bytes;
- одинаковые три задачи: deleted SupplierInvoice warehouse, equal InventoryTransfer warehouses и новая optional SalesInvoice payment due date;
- independent lane contexts, no issue history, no cross-lane outputs, no native 1C and no source writes.

Точные формулировки: [`tasks.json`](tasks.json). Машинные метрики и winner packet: [`results.json`](results.json).

## Comparison

| Lane | Владельцы / seam | Достаточный packet | Search calls | Files read | Context bytes | Lane elapsed | Extra setup |
|---|---:|---:|---:|---:|---:|---:|---:|
| `rg` | 3/3 | 3/3 | 26 | 10 | 96,313 | 344.01 s | 0 в обычной среде; 5.289 s bootstrap здесь |
| minimal catalog | 3/3 | 3/3 | 30 | 13 | 202,256 | 366.85 s | 4.581 s / 562,182 B |
| code-index-mcp | 3/3 | 2/3 | 34 | 10 | 93,548 | 425.54 s | 16.221 s + shared `rg`; 1,699,274 B |

`activeToolSeconds` отдельно: `rg` 8.189 s, catalog 1.064 s, MCP 20.016 s. Каталог выиграл только микровремя lookup, но агент прочитал больше файлов и получил 2.10× baseline context. MCP сэкономил лишь 2.9% context против `rg`, был медленнее и оставил form/date precedent новой задачи неизвестным.

## Minimal catalog

`experiment.py build-catalog` читает только штатный `ConfigDumpInfo.xml` и существующую файловую структуру; собственного BSL parser нет.

- build: 4.581 s;
- 4,147 metadata records;
- 562,182 bytes;
- после малого BSL-only изменения rebuild занял 1.649 s и дал byte-identical catalog SHA-256 `de0c9a38d71074ff23909537c580bcbdf3a0303fdfa3d75fabd1b7f00fab1af0`.

Каталог хорошо называет object package, но возвращает широкие списки XML/BSL. Он не сокращает задачу лучше корректного соглашения `object name → rg → source read`.

## Ready external candidate

Испытан наиболее узкий готовый кандидат:

- upstream: <https://github.com/johnhuang316/code-index-mcp>;
- package `code-index-mcp 2.17.1`;
- exact commit `d395cbf99e8e3e8bc280255a76a84a9ac6cb5528`;
- MIT license, LICENSE SHA-256 `6b73612bdc3ca20c7cd0144b4d4c74e58ed4d8dc420c09a5632a8d5493bd5779`;
- locked local installation, no credentials/semantic service/file watcher.

Observed contract:

- cold start 4.542 s; deep build 4.198 s;
- shallow/deep index: 3,370 supported files, **0 `.bsl` files**;
- `find_files("**/*.bsl")` → empty;
- BSL `get_file_summary` / `get_symbol_body` unsupported;
- `search_code_advanced` finds BSL only because its SearchService selects external `ripgrep` (`services/search_service.py:54-74`); authoritative extensions omit `.bsl` (`constants.py:12-87`).

After a disposable BSL edit, deep setup took 11.471 s and shallow refresh 4.056 s; the BSL index remained absent. MCP search found the new line through live `ripgrep`, not through indexed BSL symbols. This is wrapper cost, not material context capability.

The alternative `Consiliency/Code-Index-MCP` was not admitted: its own upstream describes a substantially larger multi-repository SQLite/FTS/plugin/server surface, unpublished native 1.4.0 package status and 2 GB/10 GB minimum. Testing it would violate the short/KISS comparison once the narrow candidate already exposed the decisive BSL gap.

## Winner packet on the new task

**Task:** optional `PaymentDueDate` on SalesInvoice; earlier calendar day blocks posting, blank/same/later allowed, draft allowed.

Small packet:

1. `Documents/SalesInvoice.xml:216-226` — posting and four recorder sets; add one optional date-only header attribute.
2. `Documents/SalesInvoice/Ext/ObjectModule.bsl:14-56` — object/server `Posting`; reject and return before initialization/movements.
3. `Documents/SalesInvoice/Ext/ObjectModule.bsl:74-82` — `BeforeWrite`; leave unchanged to preserve drafts.
4. `Documents/SalesInvoice/Forms/DocumentForm/Ext/Form.xml:271-315` — explicit header controls; add the user-editable field if standard form UX is in scope.
5. `Documents/BankPayment.xml:568-612` — existing optional date-only metadata precedent.

Boundary: metadata + explicit form field + an early calendar-day guard in object `Posting`; no register/common-module change. Unknowns remain exact labels/message, UUID/control IDs, and whether list/print/EDI exposure is separately required.

## Integrity and limits

Canonical copied snapshot matched every manifest hash before the lanes and remained byte-identical afterward. All candidate code, indexes and mutable copies lived in task-owned `.local/`; no native 1C, DB, CF, canonical snapshot or manifest mutation occurred.

This experiment measures one 5,099-file JetTr dump and three English-named business objects. It does not prove that `rg` dominates on every larger or obfuscated configuration. It proves that this snapshot/task family does not justify a persistent index today.
