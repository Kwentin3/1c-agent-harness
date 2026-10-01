# Transparent correction

The initial preflight remains unchanged. This is the single permitted correction after the independent reviewer returned `CHECKLIST FAIL`.

## Corrected contract

- **Scope:** the claim is limited to the exported manager-module API `InformationRegisters.EmailAccountSettings.UpdateTheAccountUsageDate`; it does not prove global monotonicity for forms or direct record-set writers. The procedure is compiled for server, thick ordinary client, or external connection (`InformationRegisters/EmailAccountSettings/Ext/ManagerModule.bsl:11-12`) and performs its own lock/transaction/read/write path (`:46-100`).
- **Normalization and monotonicity:** normalize `Undefined` to `BegOfDay(CurrentSessionDate())` first, then apply the same monotonic rule as for an explicit date. Creation remains independent of the comparison.
- **Persisted-state matrix, with explicit pre-state:**
  1. existing `20`, explicit `10` → persisted `20`;
  2. existing `20`, explicit `25` → persisted `25`;
  3. existing `20`, explicit `20` → persisted `20`, with the task's no-write preservation retained as a static acceptance constraint for this manager API: `WritingRequired` starts `False` (`ManagerModule.bsl:61`), is set only inside the unequal-value branch (`:72-77`), and `RecordSet.Write()` is guarded by it (`:89-91`). A runtime side-effect witness remains unknown; this claim does not cover direct record-set writers outside the API scope);
  4. no record, explicit `15` → exactly one record with persisted `15`;
  5. existing date older than current session day, omitted input → persisted `BegOfDay(CurrentSessionDate())`;
  6. existing date equal to current session day, omitted input → persisted date unchanged;
  7. existing future date, omitted input → future persisted date retained;
  8. no record, omitted input → exactly one record with persisted `BegOfDay(CurrentSessionDate())`.
- **Counterimplementations killed by the matrix:** reversed comparison fails cases 1-2; explicit-only monotonicity with unconditional `Undefined` assignment fails case 7; a missing creation branch fails cases 4 and 8; a form-only check fails direct calls to the exported API.
- **Adjacent write mechanism:** a generic `BeforeWrite` subscription includes this record set (`EventSubscriptions/CheckSafeModeBeforeRecordingRecordingSet.xml:17-54`) and calls `CommonModules/StandardSubsystemsServer/Ext/Module.bsl:2045-2071`. It enforces safe-mode behavior but does not implement the scalar rule. A later native observation must use an admitted non-safe-mode context and must not bypass or alter this subscription.
- **Remaining unknown:** the persisted-state matrix is a pre-native contract, not runtime proof. Current production callers found at `CommonModules/EmailManagement/Ext/Module.bsl:221-230,712-727` and `Documents/OutgoingEmail/Ext/ObjectModule.bsl:133-143` omit the explicit date, so any later bounded experiment for explicit older/newer values must call the exported entry point directly.

## Correction metadata

- Executor: master Hermes Agent, model `gpt-5.6-sol`, provider `openai-codex`.
- Interval: `2026-08-30T11:14:43Z`–`11:16:24Z` (`101 s`).
- Native attempts: `0`; owner interventions: `0`.
- This metadata was added after final dual review identified that correction time had been omitted from the KISS accounting; the semantic contract above was not changed.

## Corrected verdict

`READY FOR NATIVE` for one bounded experiment against this manager API. This correction does not authorize a production BSL patch, native loop, or merge.
