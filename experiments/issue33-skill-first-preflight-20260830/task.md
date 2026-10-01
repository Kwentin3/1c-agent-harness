# Fresh executor task

In Jet `1.0.3.1`, change the update of an email account's last-use date so that an older incoming date can never reduce the already stored `DateOfLastUse`. A newer date must still be stored, an equal date must remain a no-op, creating the first record must keep working, and an omitted date must retain its documented current-day behavior.

Before any production edit or native 1C launch, investigate the canonical snapshot and publish the short pre-native Markdown required by the public skills. Finish with `READY FOR NATIVE` or `CONTEXT BLOCKED`.

Do not modify production BSL/XML and do not run 1C for this task.