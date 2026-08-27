# Third-party attribution for issue #14

This experiment uses the official `1Ci-Company/Jet-TR` v1.0.3.1 configuration as a local, immutable laboratory input.

- Jet-TR repository: <https://github.com/1Ci-Company/Jet-TR>
- Jet-TR license: MIT, <https://github.com/1Ci-Company/Jet-TR/blob/develop-tr/LICENSE.md>
- Copyright: `Copyright (c) 2025 1Ci (1C International)`

The existing `Ext/ManagedApplicationModule.bsl` file in the immutable snapshot contains its own explicit header:

- `Copyright (c) 2024, OOO 1C-Soft`
- Creative Commons Attribution 4.0 International (CC BY 4.0)
- License URL stated by the source file: <https://creativecommons.org/licenses/by/4.0/legalcode>

Any published instrumentation diff that includes context from that module must retain this attribution. The production patch is confined by the frozen contract to `Documents/InventoryWriteOff/Ext/ObjectModule.bsl`; the source snapshot, CF, disposable infobases, private absolute paths, and large raw logs are not published.

This file records upstream notices and experiment boundaries; it is not a license selection for `1c-agent-harness` and is not legal advice.
