from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

MANIFEST_SELF = "package-manifest.json"
PACKAGE_NAME = "issue14-business-rule-20260827"
EXPECTED_SOURCE_CF_SHA256 = "5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a"
EXPECTED_SNAPSHOT_MANIFEST_SHA256 = "70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691"
EXPECTED_BASE_PRODUCTION_FILE_SHA256 = "86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c"
EXPECTED_PATCH_SHA256 = "73d484d337c320f45204fbd0c95940c9d5ead1922f7cb4b88f2229c32e6c43e3"
EXPECTED_CANONICAL_PATCHED_FILE_SHA256 = "d8124e2942426edf82394673561f96d914c8cf35503ccdc0048eb613e801ea3a"
EXPECTED_PRIMARY_HISTORICAL_PATCHED_FILE_SHA256 = "aac9b1b60a16c3aa57cab1e5e050e0cf526d9d941cc43c2a079269e72ae4f3ef"
EXPECTED_INSTRUMENTATION_SHA256 = "42806ff6bafcbd7f4be64fd49c7035a6c3a290a1863b4ba0cd0ae47c37643d6e"
EXPECTED_NATIVE_RUN_BINDINGS = {'canonical-green-1': {'appliedInstrumentation': {'localOnlyAppliedFileSha256': {'CommonModules/JetServerCall/Ext/Module.bsl': '8a5a29413302bae0dec3fbb446596f4939259a1487cdc615dd547fc9a784f0b3',
                                                                                 'Ext/ManagedApplicationModule.bsl': '01fe526ab32583814d9ace200321d3bc9027a9422a0b2c30a38e64967b2e326f'},
                                                  'templateSha256': '42806ff6bafcbd7f4be64fd49c7035a6c3a290a1863b4ba0cd0ae47c37643d6e',
                                                  'templateSubstitutions': {'<RECEIPT_FILE>': '<RUN_DIR>/evidence/repeat-receipt.txt',
                                                                            '<RUN_MODE>': 'green-production-patch',
                                                                            '<RUN_NONCE>': 'repeat-full-b8b623837201433d',
                                                                            '<STAGE_FILE>': '<RUN_DIR>/evidence/repeat-stage.txt'}},
                       'mode': 'green-production-patch',
                       'outputs': {'createDumpResult': '0',
                                   'createLogSha256': 'ac9c0f6776a26e1afb1283df650b791215a54d71681e0b5ced546ae2c9339965',
                                   'createResultSha256': 'e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083',
                                   'createSuccessMarker': 'completed successfully',
                                   'loadDumpResult': '0',
                                   'loadLogSha256': '4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86',
                                   'loadResultSha256': 'e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083',
                                   'loadSuccessMarker': 'Configuration successfully updated',
                                   'runtimeCompletionObserved': True,
                                   'runtimeHarnessStatus': 'complete_marker',
                                   'runtimeLogSha256': '6a36c876e98c4bd8564400657343bacb934673813f1f18f6d89c128b8bd1be52',
                                   'runtimeProcessReturn': -15,
                                   'runtimeReceiptCompleteMarker': 'complete###true',
                                   'runtimeResultJsonSha256': 'aa5c0c0b9e5504222d40bba1ab1350760a31fbd7f56611938cc344fe8ac71f7d'},
                       'phase': 'repeat-GREEN-clean-run',
                       'productionBytes': {'actualRunProductionFileSha256': 'd8124e2942426edf82394673561f96d914c8cf35503ccdc0048eb613e801ea3a',
                                           'baseFileSha256': '86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c',
                                           'patchedFileSha256': 'd8124e2942426edf82394673561f96d914c8cf35503ccdc0048eb613e801ea3a',
                                           'productionPatchSha256': '73d484d337c320f45204fbd0c95940c9d5ead1922f7cb4b88f2229c32e6c43e3',
                                           'role': 'canonical-published-patch-application-green-1'},
                       'rawLocalReceiptSha256': 'b9e82b37f7bc3ceb1871bb84793f5a9c5c1fb39c2bda4f902e3e1bf4434642d6',
                       'receiptFile': 'repeat-green-receipt.txt',
                       'receiptLocal': '<RUN_DIR>/evidence/repeat-receipt.txt',
                       'receiptSha256': '7ad3eabca42d387f0c9472f1542bd31ae7a15841cfecd63e6ffc60b952495dad',
                       'runNonce': 'repeat-full-b8b623837201433d',
                       'stageLocal': '<RUN_DIR>/evidence/repeat-stage.txt',
                       'summaryFile': 'repeat-green-summary.json',
                       'summarySha256': '2fe7403c2263aef068aff0f7fe77b6dbd3f673a890030d53b77e67310fd80427'},
 'canonical-green-2': {'appliedInstrumentation': {'localOnlyAppliedFileSha256': {'CommonModules/JetServerCall/Ext/Module.bsl': '8a5a29413302bae0dec3fbb446596f4939259a1487cdc615dd547fc9a784f0b3',
                                                                                 'Ext/ManagedApplicationModule.bsl': '4b7ba569f6af99d6aa0db6534a6915ea733291b0be84b3a7c5f4ed97401cf6b8'},
                                                  'templateSha256': '42806ff6bafcbd7f4be64fd49c7035a6c3a290a1863b4ba0cd0ae47c37643d6e',
                                                  'templateSubstitutions': {'<RECEIPT_FILE>': '<RUN_DIR>/evidence/canonical-green-2-receipt.txt',
                                                                            '<RUN_MODE>': 'green-production-patch',
                                                                            '<RUN_NONCE>': 'canonical-green-2-d5db4eaef975447b',
                                                                            '<STAGE_FILE>': '<RUN_DIR>/evidence/canonical-green-2-stage.txt'}},
                       'mode': 'green-production-patch',
                       'outputs': {'createDumpResult': '0',
                                   'createLogSha256': '9f4d01a1529738c97eddb22446fd13abeeadc54717e5227a914fe8667e5837ac',
                                   'createResultSha256': 'e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083',
                                   'createSuccessMarker': 'completed successfully',
                                   'loadDumpResult': '0',
                                   'loadLogSha256': '4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86',
                                   'loadResultSha256': 'e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083',
                                   'loadSuccessMarker': 'Configuration successfully updated',
                                   'runtimeCompletionObserved': True,
                                   'runtimeHarnessStatus': 'complete_marker',
                                   'runtimeLogSha256': '6a36c876e98c4bd8564400657343bacb934673813f1f18f6d89c128b8bd1be52',
                                   'runtimeProcessReturn': -15,
                                   'runtimeReceiptCompleteMarker': 'complete###true',
                                   'runtimeResultJsonSha256': '5294cc96a5fca8754bd442d51517a124023fe488405fef8ff5f3f4782fa0c08d'},
                       'phase': 'canonical-GREEN-2-clean-run',
                       'productionBytes': {'actualRunProductionFileSha256': 'd8124e2942426edf82394673561f96d914c8cf35503ccdc0048eb613e801ea3a',
                                           'baseFileSha256': '86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c',
                                           'patchedFileSha256': 'd8124e2942426edf82394673561f96d914c8cf35503ccdc0048eb613e801ea3a',
                                           'productionPatchSha256': '73d484d337c320f45204fbd0c95940c9d5ead1922f7cb4b88f2229c32e6c43e3',
                                           'role': 'canonical-published-patch-application-green-2'},
                       'rawLocalReceiptSha256': '2221d1b82259e95ae27d2bacd02e212cf67e78a1c68d43f77e5567d45c8c2f0d',
                       'receiptFile': 'canonical-green-2-receipt.txt',
                       'receiptLocal': '<RUN_DIR>/evidence/canonical-green-2-receipt.txt',
                       'receiptSha256': '55dfbb2dd6c81a28d0270c2a942bda35d48f39bb30092a43141856f1af4b0120',
                       'runNonce': 'canonical-green-2-d5db4eaef975447b',
                       'stageLocal': '<RUN_DIR>/evidence/canonical-green-2-stage.txt',
                       'summaryFile': 'canonical-green-2-summary.json',
                       'summarySha256': '2013c6fee66deaa998ed7145e46c23883a4aa913bcc43bc06310a3965d3c2b5e'},
 'green-production-historical': {'appliedInstrumentation': {'localOnlyAppliedFileSha256': {'CommonModules/JetServerCall/Ext/Module.bsl': '8a5a29413302bae0dec3fbb446596f4939259a1487cdc615dd547fc9a784f0b3',
                                                                                           'Ext/ManagedApplicationModule.bsl': '57bca83145426d2ba7054a46f8c7183177ab397abcb09b2391a65a4a4a46a7f4'},
                                                            'templateSha256': '42806ff6bafcbd7f4be64fd49c7035a6c3a290a1863b4ba0cd0ae47c37643d6e',
                                                            'templateSubstitutions': {'<RECEIPT_FILE>': '<RUN_DIR>/evidence/green-receipt.txt',
                                                                                      '<RUN_MODE>': 'green-production-patch',
                                                                                      '<RUN_NONCE>': 'green-full-7d54ba68acb84d6a',
                                                                                      '<STAGE_FILE>': '<RUN_DIR>/evidence/green-stage.txt'}},
                                 'mode': 'green-production-patch',
                                 'outputs': {'createDumpResult': '0',
                                             'createLogSha256': '01f5f8bce7deeab5cfcbc503edaeef39b85acd9ae47671d019ad3e5e361ac673',
                                             'createResultSha256': 'e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083',
                                             'createSuccessMarker': 'completed successfully',
                                             'loadDumpResult': '0',
                                             'loadLogSha256': '4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86',
                                             'loadResultSha256': 'e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083',
                                             'loadSuccessMarker': 'Configuration successfully updated',
                                             'runtimeCompletionObserved': True,
                                             'runtimeHarnessStatus': 'complete_marker',
                                             'runtimeLogSha256': '6a36c876e98c4bd8564400657343bacb934673813f1f18f6d89c128b8bd1be52',
                                             'runtimeProcessReturn': -15,
                                             'runtimeReceiptCompleteMarker': 'complete###true',
                                             'runtimeResultJsonSha256': 'da92ae5a3f6cbf1ee46bf06c75db64ea64867ffcb504bdb97d3e40e2061707bf'},
                                 'phase': 'GREEN-production-patch',
                                 'productionBytes': {'actualRunProductionFileSha256': 'aac9b1b60a16c3aa57cab1e5e050e0cf526d9d941cc43c2a079269e72ae4f3ef',
                                                     'baseFileSha256': '86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c',
                                                     'patchedFileSha256': 'aac9b1b60a16c3aa57cab1e5e050e0cf526d9d941cc43c2a079269e72ae4f3ef',
                                                     'productionPatchSha256': '73d484d337c320f45204fbd0c95940c9d5ead1922f7cb4b88f2229c32e6c43e3',
                                                     'role': 'historical-green-patched-by-local-crlf-preserving-edit'},
                                 'rawLocalReceiptSha256': 'e9a29799bd40a5524a8885fd756c517b43cd41c9b03d65a17d47da6cfa47ce25',
                                 'receiptFile': 'green-production-receipt.txt',
                                 'receiptLocal': '<RUN_DIR>/evidence/green-receipt.txt',
                                 'receiptSha256': '4bc33c9a99ea99b0025dd12c5069664f661f83fad4e4a8beafb28ecf51e0dab1',
                                 'runNonce': 'green-full-7d54ba68acb84d6a',
                                 'stageLocal': '<RUN_DIR>/evidence/green-stage.txt',
                                 'summaryFile': 'green-production-summary.json',
                                 'summarySha256': '1a7df795c5d4e6e63144669fc8e276456b10bcfbdf91b6151b25c167ee513913'},
 'red-source': {'appliedInstrumentation': {'localOnlyAppliedFileSha256': {'CommonModules/JetServerCall/Ext/Module.bsl': 'b7733aaf621da9ccf6b2c0d940885da116d971f9cbfca5a091a17f9c499461c1',
                                                                          'Ext/ManagedApplicationModule.bsl': '9a700de1745d952ee503f20b624fb862cbb167453648ade0c6d7292ade350997'},
                                           'templateSha256': '42806ff6bafcbd7f4be64fd49c7035a6c3a290a1863b4ba0cd0ae47c37643d6e',
                                           'templateSubstitutions': {'<RECEIPT_FILE>': '<RUN_DIR>/evidence/red-receipt.txt',
                                                                     '<RUN_MODE>': 'red-source-logic',
                                                                     '<RUN_NONCE>': 'red-full-7e9c5a00437242c2',
                                                                     '<STAGE_FILE>': '<RUN_DIR>/evidence/red-stage.txt'}},
                'mode': 'red-source-logic',
                'outputs': {'createDumpResult': '0',
                            'createLogSha256': 'ae38624a5f5989040004255aca17277145899dde53675692ee63aa22221eb2bc',
                            'createResultSha256': 'e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083',
                            'createSuccessMarker': 'completed successfully',
                            'loadDumpResult': '0',
                            'loadLogSha256': '4d841be04b71dd0ee7cfebcfa7af194d74902e2ec1c213987889d7d3940c0f86',
                            'loadResultSha256': 'e45825471ed10290785b62676dc5f453d228a1e1d933c45a733e9bb239c9e083',
                            'loadSuccessMarker': 'Configuration successfully updated',
                            'runtimeCompletionObserved': True,
                            'runtimeHarnessStatus': 'complete_marker_legacy_completeTrue',
                            'runtimeLogSha256': '6a36c876e98c4bd8564400657343bacb934673813f1f18f6d89c128b8bd1be52',
                            'runtimeProcessReturn': -15,
                            'runtimeReceiptCompleteMarker': 'complete###true',
                            'runtimeResultJsonSha256': '18465742cd288d48a60bebe7cd5b0ec0f69561843f3cf1ba249bc77be6a0708b'},
                'phase': 'RED-before-production-patch',
                'productionBytes': {'actualRunProductionFileSha256': '86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c',
                                    'baseFileSha256': '86f383323de83d4912c99854ec6db7cbf59e2265d62a97d8143a46eacba07d9c',
                                    'patchedFileSha256': None,
                                    'productionPatchSha256': None,
                                    'role': 'source-unpatched'},
                'rawLocalReceiptSha256': '24410de9c97a71be96037914634159476631f4641a6c0648ff95d0101348225e',
                'receiptFile': 'red-source-receipt.txt',
                'receiptLocal': '<RUN_DIR>/evidence/red-receipt.txt',
                'receiptSha256': '0960822c0fa4a30df0314d74d545a8f8814faa1131bd1336d499de5492cb77ad',
                'runNonce': 'red-full-7e9c5a00437242c2',
                'stageLocal': '<RUN_DIR>/evidence/red-stage.txt',
                'summaryFile': 'red-source-summary.json',
                'summarySha256': '3c915833e6a5b559fc17a0b4aa2b676d1a3d8b3c44e862f1e59035c4ca6911fc'}}


REQUIRED_ARTIFACTS = {
    "ATTRIBUTION.md",
    "README.md",
    "canonical-green-2-evidence.md",
    "canonical-green-2-receipt.txt",
    "canonical-green-2-summary.json",
    "green-production-evidence.md",
    "green-production-receipt.txt",
    "green-production-summary.json",
    "instrumentation.diff",
    "native-invocations.json",
    "pre-production-review-1.md",
    "pre-production-review-2.md",
    "production-patch.diff",
    "red-source-evidence.md",
    "red-source-receipt.txt",
    "red-source-summary.json",
    "repeat-green-evidence.md",
    "repeat-green-receipt.txt",
    "repeat-green-summary.json",
    "runtime-entrypoint-gap.md",
    "semantic-contract-checklist.md",
    "task-contract-amendment-1.json",
    "task-contract-amendment-2.json",
    "task-contract.json",
}

CASES = [
    "negative_single",
    "zero_single",
    "mixed_same_product",
    "insufficient_stock_positive",
    "normal_positive",
    "minimum_positive",
    "all_positive_multi_duplicate",
]
INVALID_QUANTITY_CASES = ["negative_single", "zero_single", "mixed_same_product"]
VALID_CASES = ["normal_positive", "minimum_positive", "all_positive_multi_duplicate"]
CASE_KEYS = [
    "begin",
    "rowCount",
    "draftSucceeded",
    "draftError",
    "postCallSucceeded",
    "postError",
    "postedAfter",
    "inventoryBeforeA",
    "inventoryAfterA",
    "costQuantityBeforeA",
    "costQuantityAfterA",
    "costAmountBeforeA",
    "costAmountAfterA",
    "inventoryBeforeB",
    "inventoryAfterB",
    "costQuantityBeforeB",
    "costQuantityAfterB",
    "costAmountBeforeB",
    "costAmountAfterB",
    "inventoryMovementRowsA",
    "inventoryMovementQuantityA",
    "costMovementRowsA",
    "costMovementQuantityA",
    "costMovementAmountA",
    "inventoryMovementRowsB",
    "inventoryMovementQuantityB",
    "costMovementRowsB",
    "costMovementQuantityB",
    "costMovementAmountB",
    "end",
]

EXPECTED_ROW_COUNTS = {
    "negative_single": "1",
    "zero_single": "1",
    "mixed_same_product": "3",
    "insufficient_stock_positive": "1",
    "normal_positive": "1",
    "minimum_positive": "1",
    "all_positive_multi_duplicate": "3",
}

GREEN_EXPECTED = {
    "negative_single": {
        "draftSucceeded": "true",
        "postCallSucceeded": "false",
        "postedAfter": "false",
        "inventoryAfterA": "10",
        "inventoryAfterB": "10",
        "costQuantityAfterA": "10",
        "costAmountAfterA": "10",
        "inventoryMovementRowsA": "0",
        "inventoryMovementQuantityA": "0",
        "costMovementRowsA": "0",
        "costMovementQuantityA": "0",
        "costMovementAmountA": "0",
    },
    "zero_single": {
        "draftSucceeded": "true",
        "postCallSucceeded": "false",
        "postedAfter": "false",
        "inventoryAfterA": "10",
        "inventoryAfterB": "10",
        "costQuantityAfterA": "10",
        "costAmountAfterA": "10",
        "inventoryMovementRowsA": "0",
        "inventoryMovementQuantityA": "0",
        "costMovementRowsA": "0",
        "costMovementQuantityA": "0",
        "costMovementAmountA": "0",
    },
    "mixed_same_product": {
        "draftSucceeded": "true",
        "postCallSucceeded": "false",
        "postedAfter": "false",
        "inventoryAfterA": "10",
        "inventoryAfterB": "10",
        "costQuantityAfterA": "10",
        "costAmountAfterA": "10",
        "inventoryMovementRowsA": "0",
        "inventoryMovementQuantityA": "0",
        "costMovementRowsA": "0",
        "costMovementQuantityA": "0",
        "costMovementAmountA": "0",
    },
    "insufficient_stock_positive": {
        "draftSucceeded": "true",
        "postCallSucceeded": "false",
        "postedAfter": "false",
        "inventoryAfterA": "10",
        "inventoryMovementRowsA": "0",
    },
    "normal_positive": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "6",
        "inventoryAfterB": "10",
        "costQuantityAfterA": "6",
        "costAmountAfterA": "6",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "4",
        "inventoryMovementRowsB": "0",
    },
    "minimum_positive": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "9.999",
        "inventoryAfterB": "10",
        "costQuantityAfterA": "9.999",
        "costAmountAfterA": "10",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "0.001",
        "inventoryMovementRowsB": "0",
    },
    "all_positive_multi_duplicate": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "6",
        "inventoryAfterB": "8",
        "costQuantityAfterA": "6",
        "costQuantityAfterB": "8",
        "costAmountAfterA": "6",
        "costAmountAfterB": "8",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "4",
        "inventoryMovementRowsB": "1",
        "inventoryMovementQuantityB": "2",
    },
}

RED_EXPECTED = {
    "negative_single": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "11",
        "costQuantityAfterA": "11",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "-1",
    },
    "zero_single": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "10",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "0",
    },
    "mixed_same_product": {
        "draftSucceeded": "true",
        "postCallSucceeded": "true",
        "postedAfter": "true",
        "inventoryAfterA": "7",
        "inventoryMovementRowsA": "1",
        "inventoryMovementQuantityA": "3",
    },
    "insufficient_stock_positive": {
        "draftSucceeded": "true",
        "postCallSucceeded": "false",
        "postedAfter": "false",
        "inventoryAfterA": "10",
        "inventoryMovementRowsA": "0",
    },
    "normal_positive": GREEN_EXPECTED["normal_positive"],
    "minimum_positive": GREEN_EXPECTED["minimum_positive"],
    "all_positive_multi_duplicate": GREEN_EXPECTED["all_positive_multi_duplicate"],
}

SUMMARY_TO_RECEIPT = {
    "green-production-summary.json": "green-production-receipt.txt",
    "repeat-green-summary.json": "repeat-green-receipt.txt",
    "canonical-green-2-summary.json": "canonical-green-2-receipt.txt",
    "red-source-summary.json": "red-source-receipt.txt",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_files(package: Path) -> set[str]:
    return {
        p.relative_to(package).as_posix()
        for p in package.rglob("*")
        if p.is_file()
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rewrite_manifest(package: Path) -> None:
    """Refresh only hash/size fields; used by negative tests.

    This simulates an attacker who changes an artifact and then updates the
    manifest. Semantic validation must still catch wrong evidence values.
    """
    manifest_path = package / MANIFEST_SELF
    manifest = load_json(manifest_path)
    manifest["artifacts"] = {}
    manifest["artifactStats"] = {}
    for path in sorted(package.rglob("*")):
        if not path.is_file() or path.name == MANIFEST_SELF:
            continue
        rel = path.relative_to(package).as_posix()
        manifest["artifacts"][rel] = sha256(path)
        manifest["artifactStats"][rel] = path.stat().st_size
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_manifest(package: Path) -> dict[str, Any]:
    manifest = load_json(package / MANIFEST_SELF)
    if manifest.get("schemaVersion") != 1:
        raise AssertionError("manifest schemaVersion mismatch")
    if manifest.get("package") != PACKAGE_NAME:
        raise AssertionError("manifest package mismatch")
    expected = set(manifest["artifacts"])
    actual = package_files(package) - {MANIFEST_SELF}
    if actual != expected:
        raise AssertionError(
            f"package/manifest closure broken: unlisted={sorted(actual - expected)} missing={sorted(expected - actual)}"
        )
    if expected != REQUIRED_ARTIFACTS:
        raise AssertionError(
            f"artifact set mismatch: extra={sorted(expected - REQUIRED_ARTIFACTS)} missing={sorted(REQUIRED_ARTIFACTS - expected)}"
        )
    for rel, expected_hash in manifest["artifacts"].items():
        path = package / rel
        if sha256(path) != expected_hash:
            raise AssertionError(f"artifact hash mismatch: {rel}")
        if manifest["artifactStats"].get(rel) != path.stat().st_size:
            raise AssertionError(f"artifact size mismatch: {rel}")
    ids = manifest["sourceImmutableIdentities"]
    if ids["sourceCfSha256"] != EXPECTED_SOURCE_CF_SHA256:
        raise AssertionError("source CF hash mismatch")
    if ids["manifestIdentitySha256"] != EXPECTED_SNAPSHOT_MANIFEST_SHA256:
        raise AssertionError("snapshot manifest hash mismatch")
    if ids["snapshotFileCount"] != 5099:
        raise AssertionError("snapshot file count mismatch")
    cpb = manifest["canonicalProductionBytes"]
    if cpb["baseFileSha256"] != EXPECTED_BASE_PRODUCTION_FILE_SHA256:
        raise AssertionError("base production file hash mismatch")
    if cpb["productionPatchSha256"] != EXPECTED_PATCH_SHA256:
        raise AssertionError("production patch hash mismatch")
    if cpb["patchedFileSha256"] != EXPECTED_CANONICAL_PATCHED_FILE_SHA256:
        raise AssertionError("canonical patched file hash mismatch")
    return manifest


def validate_no_private_paths(package: Path) -> None:
    # Placeholders such as ``<RUN_DIR>/home`` are intentional. What must not
    # appear in committed evidence is a real host absolute path.
    private_path = re.compile(r"(?<!>)/(workspace|home)/")
    for rel in package_files(package):
        if rel == MANIFEST_SELF:
            continue
        text = (package / rel).read_text(encoding="utf-8", errors="replace")
        if private_path.search(text):
            raise AssertionError(f"private absolute path leaked in {rel}")


def parse_receipt(path: Path) -> dict[str, list[str]]:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    lines = text.splitlines()
    if len(lines) != 214:
        raise AssertionError(f"{path.name}: expected exactly 214 lines, got {len(lines)}")
    parsed: dict[str, list[str]] = defaultdict(list)
    for line in lines:
        if not line.strip():
            raise AssertionError(f"{path.name}: empty line")
        if "###" not in line:
            raise AssertionError(f"{path.name}: malformed line {line!r}")
        key, value = line.split("###", 1)
        if not key or "#" in key:
            raise AssertionError(f"{path.name}: malformed key {key!r}")
        parsed[key].append(value)
    expected_keys = {"nonce", "mode", "complete"}
    expected_keys.update(f"{case}.{key}" for case in CASES for key in CASE_KEYS)
    if set(parsed) != expected_keys:
        raise AssertionError(
            f"{path.name}: key mismatch missing={sorted(expected_keys - set(parsed))} unknown={sorted(set(parsed) - expected_keys)}"
        )
    for key, values in parsed.items():
        if key == "complete":
            if values != ["false", "true"]:
                raise AssertionError(f"{path.name}: complete marker sequence mismatch {values!r}")
        elif len(values) != 1:
            raise AssertionError(f"{path.name}: duplicate key {key}")
    return parsed


def scalar(rows: dict[str, list[str]], key: str) -> str:
    values = rows.get(key)
    if values is None or len(values) != 1:
        raise AssertionError(f"missing scalar receipt key {key}")
    return values[0]


def validate_receipt_expectations(path: Path, expected: dict[str, dict[str, str]]) -> dict[str, list[str]]:
    rows = parse_receipt(path)
    for case in CASES:
        if scalar(rows, f"{case}.begin") != "true" or scalar(rows, f"{case}.end") != "true":
            raise AssertionError(f"{path.name}: case boundary mismatch {case}")
        if scalar(rows, f"{case}.rowCount") != EXPECTED_ROW_COUNTS[case]:
            raise AssertionError(f"{path.name}: rowCount mismatch {case}")
        for before_key in [
            "inventoryBeforeA",
            "costQuantityBeforeA",
            "costAmountBeforeA",
            "inventoryBeforeB",
            "costQuantityBeforeB",
            "costAmountBeforeB",
        ]:
            if scalar(rows, f"{case}.{before_key}") != "10":
                raise AssertionError(f"{path.name}: opening balance mismatch {case}.{before_key}")
        for metric, expected_value in expected[case].items():
            actual = scalar(rows, f"{case}.{metric}")
            if actual != expected_value:
                raise AssertionError(f"{path.name}: {case}.{metric} expected {expected_value!r}, got {actual!r}")
    return rows


def validate_summary_observations(package: Path, summary_name: str, receipt_rows: dict[str, list[str]]) -> None:
    summary = load_json(package / summary_name)
    receipt_name = SUMMARY_TO_RECEIPT[summary_name]
    if summary.get("receiptSha256") != sha256(package / receipt_name):
        raise AssertionError(f"{summary_name}: receiptSha256 mismatch")
    obs = summary["observations"]

    def assert_case_values(case: str, values: dict[str, Any], location: str) -> None:
        for metric, expected_value in values.items():
            if metric == "case":
                continue
            receipt_key = f"{case}.{metric}"
            actual_from_receipt = scalar(receipt_rows, receipt_key)
            if str(expected_value) != actual_from_receipt:
                raise AssertionError(
                    f"{summary_name}: {location}.{metric}={expected_value!r} differs from receipt {receipt_key}={actual_from_receipt!r}"
                )

    if summary_name == "red-source-summary.json":
        for case, values in obs["redFailures"].items():
            assert_case_values(case, values, f"redFailures.{case}")
        assert_case_values(obs["negativeControl"]["case"], obs["negativeControl"], "negativeControl")
        for case, values in obs["validPreservation"].items():
            assert_case_values(case, values, f"validPreservation.{case}")
    else:
        for case, values in obs["invalidCasesRejectedAtomically"].items():
            assert_case_values(case, values, f"invalidCasesRejectedAtomically.{case}")
        assert_case_values(obs["existingNegativeControl"]["case"], obs["existingNegativeControl"], "existingNegativeControl")
        for case, values in obs["validPreservation"].items():
            assert_case_values(case, values, f"validPreservation.{case}")


def validate_production_patch(package: Path) -> None:
    lines = (package / "production-patch.diff").read_text(encoding="utf-8").splitlines()
    if lines[:3] != [
        "--- a/Documents/InventoryWriteOff/Ext/ObjectModule.bsl",
        "+++ b/Documents/InventoryWriteOff/Ext/ObjectModule.bsl",
        "@@ -11,0 +12,6 @@",
    ]:
        raise AssertionError("production patch target/hunk mismatch")
    if sum(1 for line in lines if line.startswith("--- ")) != 1 or sum(1 for line in lines if line.startswith("+++ ")) != 1:
        raise AssertionError("production patch must touch exactly one file")
    added = [line[1:] for line in lines if line.startswith("+") and not line.startswith("+++")]
    removed = [line for line in lines if line.startswith("-") and not line.startswith("---")]
    expected_added = [
        "\tFor Each InventoryRow In Inventory Do",
        "\t\tIf InventoryRow.Quantity <= 0 Then",
        "\t\t\tCancel = True;",
        "\t\t\tReturn;",
        "\t\tEndIf;",
        "\tEndDo;",
    ]
    if removed:
        raise AssertionError(f"production patch must be additive only, removed={removed!r}")
    if added != expected_added:
        raise AssertionError(f"production patch added lines mismatch: {added!r}")
    if sha256(package / "production-patch.diff") != EXPECTED_PATCH_SHA256:
        raise AssertionError("production patch SHA mismatch")


def validate_instrumentation_and_native_binding(package: Path, receipt_rows_by_name: dict[str, dict[str, list[str]]]) -> None:
    inst = (package / "instrumentation.diff").read_text(encoding="utf-8")
    inst_sha = sha256(package / "instrumentation.diff")
    if inst_sha != EXPECTED_INSTRUMENTATION_SHA256:
        raise AssertionError("instrumentation template SHA mismatch")
    if "Documents/InventoryWriteOff/Ext/ObjectModule.bsl" in inst:
        raise AssertionError("instrumentation diff must not include production patch target")
    for placeholder in ["<RECEIPT_FILE>", "<STAGE_FILE>", "<RUN_NONCE>", "<RUN_MODE>"]:
        if placeholder not in inst:
            raise AssertionError(f"instrumentation diff missing placeholder {placeholder}")
    if "canonical-green-2-receipt.txt" in inst or '"green-production-patch"' in inst:
        raise AssertionError("instrumentation diff still contains run-specific receipt or mode")
    for line_no, line in enumerate(inst.splitlines(), start=1):
        if line.endswith((" ", "\t")):
            raise AssertionError(f"instrumentation diff has trailing whitespace on line {line_no}")
    added = [line for line in inst.splitlines() if line.startswith("+") and not line.startswith("+++")]
    removed = [line for line in inst.splitlines() if line.startswith("-") and not line.startswith("---")]
    if len(added) != 328 or removed:
        raise AssertionError("instrumentation size/shape mismatch")

    native = load_json(package / "native-invocations.json")
    if native["instrumentation"]["sha256"] != EXPECTED_INSTRUMENTATION_SHA256:
        raise AssertionError("native binding instrumentation hash mismatch")
    if native["instrumentation"].get("addedLines") != 328 or native["instrumentation"].get("removedLines") != 0:
        raise AssertionError("native binding instrumentation stats mismatch")
    if native["instrumentation"].get("templatePlaceholders") != ["<RECEIPT_FILE>", "<STAGE_FILE>", "<RUN_NONCE>", "<RUN_MODE>"]:
        raise AssertionError("native binding instrumentation placeholder mismatch")
    if native["instrumentation"].get("nativeCommandPlaceholders") != ["<RUN_DIR>"]:
        raise AssertionError("native command placeholder mismatch")
    expected_runs = set(EXPECTED_NATIVE_RUN_BINDINGS)
    if set(native["runs"]) != expected_runs:
        raise AssertionError("native binding run set mismatch")

    for label, expected in EXPECTED_NATIVE_RUN_BINDINGS.items():
        run = native["runs"][label]
        binding = run.get("binding")
        if not binding:
            raise AssertionError(f"{label}: missing binding")
        if run["phase"] != expected["phase"]:
            raise AssertionError(f"{label}: phase mismatch")
        if run.get("receiptLocal") != expected["receiptLocal"]:
            raise AssertionError(f"{label}: receiptLocal mismatch")

        outputs = run["outputs"]
        for key, expected_value in expected["outputs"].items():
            if outputs.get(key) != expected_value:
                raise AssertionError(f"{label}: output identity {key} mismatch")
        if outputs["createDumpResult"] != "0" or outputs["loadDumpResult"] != "0":
            raise AssertionError(f"{label}: native DumpResult mismatch")
        if outputs["loadSuccessMarker"] != "Configuration successfully updated":
            raise AssertionError(f"{label}: missing load success marker")
        if outputs["runtimeReceiptCompleteMarker"] != "complete###true":
            raise AssertionError(f"{label}: missing runtime complete marker binding")
        if outputs.get("runtimeCompletionObserved") is not True:
            raise AssertionError(f"{label}: runtime completion was not observed")

        commands = run["commands"]
        expected_modes = {"create": "CREATEINFOBASE", "load": "DESIGNER", "runtime": "ENTERPRISE"}
        for command_name, expected_mode in expected_modes.items():
            command = commands[command_name]
            if command[:4] != ["xvfb-run", "-a", "-s", "-screen 0 1280x1024x8 -nolisten tcp"]:
                raise AssertionError(f"{label}: xvfb prefix mismatch in {command_name}")
            if command[4] != ".local/platform/1cv8t/x86_64/8.5.1.1150/1cv8t" or command[5] != expected_mode:
                raise AssertionError(f"{label}: native command mode mismatch in {command_name}")
            joined = " ".join(command)
            if "<RUN_DIR>" not in joined:
                raise AssertionError(f"{label}: command lacks run-root placeholder")

        receipt_file = expected["receiptFile"]
        summary_file = expected["summaryFile"]
        summary = load_json(package / summary_file)
        rows = receipt_rows_by_name[receipt_file]
        if scalar(rows, "nonce") != expected["runNonce"] or scalar(rows, "mode") != expected["mode"]:
            raise AssertionError(f"{label}: receipt nonce/mode mismatch")
        if summary["runNonce"] != expected["runNonce"]:
            raise AssertionError(f"{label}: summary runNonce mismatch")
        if summary["receiptSha256"] != expected["receiptSha256"] or summary["receiptSha256"] != sha256(package / receipt_file):
            raise AssertionError(f"{label}: published receipt hash mismatch")
        if summary["rawLocalReceiptSha256"] != expected["rawLocalReceiptSha256"]:
            raise AssertionError(f"{label}: raw local receipt hash mismatch")

        if binding["runNonce"] != expected["runNonce"] or binding["mode"] != expected["mode"]:
            raise AssertionError(f"{label}: binding nonce/mode mismatch")
        if binding["summary"] != {"path": summary_file, "sha256": expected["summarySha256"]}:
            raise AssertionError(f"{label}: summary binding mismatch")
        if binding["publishedReceipt"] != {
            "path": receipt_file,
            "sha256": expected["receiptSha256"],
            "rawLocalSha256": expected["rawLocalReceiptSha256"],
        }:
            raise AssertionError(f"{label}: receipt binding mismatch")
        if binding["productionBytes"] != expected["productionBytes"]:
            raise AssertionError(f"{label}: production byte binding mismatch")
        applied = binding["appliedInstrumentation"]
        expected_applied = expected["appliedInstrumentation"]
        if applied != expected_applied:
            raise AssertionError(f"{label}: applied instrumentation binding mismatch")
        if applied["templateSha256"] != EXPECTED_INSTRUMENTATION_SHA256:
            raise AssertionError(f"{label}: applied instrumentation template hash mismatch")
        substitutions = applied["templateSubstitutions"]
        if substitutions["<RECEIPT_FILE>"] != expected["receiptLocal"]:
            raise AssertionError(f"{label}: receipt substitution mismatch")
        if substitutions["<STAGE_FILE>"] != expected["stageLocal"]:
            raise AssertionError(f"{label}: stage substitution mismatch")
        if substitutions["<RUN_NONCE>"] != expected["runNonce"] or substitutions["<RUN_MODE>"] != expected["mode"]:
            raise AssertionError(f"{label}: nonce/mode substitution mismatch")

def observation_vector(rows: dict[str, list[str]]) -> dict[str, str]:
    comparison_keys = [
        "rowCount",
        "draftSucceeded",
        "postCallSucceeded",
        "postedAfter",
        "inventoryAfterA",
        "inventoryAfterB",
        "costQuantityAfterA",
        "costQuantityAfterB",
        "costAmountAfterA",
        "costAmountAfterB",
        "inventoryMovementRowsA",
        "inventoryMovementQuantityA",
        "inventoryMovementRowsB",
        "inventoryMovementQuantityB",
        "costMovementRowsA",
        "costMovementQuantityA",
        "costMovementAmountA",
        "costMovementRowsB",
        "costMovementQuantityB",
        "costMovementAmountB",
    ]
    return {f"{case}.{key}": scalar(rows, f"{case}.{key}") for case in CASES for key in comparison_keys}


def validate_canonical_green(package: Path, receipt_rows_by_name: dict[str, dict[str, list[str]]]) -> None:
    repeat = load_json(package / "repeat-green-summary.json")
    canon2 = load_json(package / "canonical-green-2-summary.json")
    if repeat["inputs"]["patchedProductionFileSha256"] != EXPECTED_CANONICAL_PATCHED_FILE_SHA256:
        raise AssertionError("canonical GREEN #1 patched hash mismatch")
    if canon2["inputs"]["patchedProductionFileSha256"] != EXPECTED_CANONICAL_PATCHED_FILE_SHA256:
        raise AssertionError("canonical GREEN #2 patched hash mismatch")
    if not canon2["canonicalization"]["byteIdenticalPatchedProductionFile"]:
        raise AssertionError("canonical GREEN byte equality flag is false")
    if canon2["canonicalization"]["canonicalGreen1PatchedProductionFileSha256"] != EXPECTED_CANONICAL_PATCHED_FILE_SHA256:
        raise AssertionError("canonicalization green1 hash mismatch")
    if canon2["canonicalization"]["primaryGreenHistoricalPatchedProductionFileSha256"] != EXPECTED_PRIMARY_HISTORICAL_PATCHED_FILE_SHA256:
        raise AssertionError("historical primary GREEN hash mismatch")
    if observation_vector(receipt_rows_by_name["repeat-green-receipt.txt"]) != observation_vector(receipt_rows_by_name["canonical-green-2-receipt.txt"]):
        raise AssertionError("canonical GREEN observation vectors differ")


def validate_report(package: Path) -> None:
    text = (package / "README.md").read_text(encoding="utf-8")
    required_snippets = [
        "Cost was dominated by finding a reliable data-backed posting entrypoint",
        "Approximate wall-clock ranges",
        "Reused from issue #10",
        "Manual steps that remain",
        "Instrumentation size:",
        "No claim is made for empty documents, UI validation/messages, imports, undo-posting, reposting",
    ]
    for snippet in required_snippets:
        if snippet not in text:
            raise AssertionError(f"README missing report snippet: {snippet}")


def validate_package(package: Path) -> None:
    validate_manifest(package)
    validate_no_private_paths(package)
    validate_production_patch(package)
    rows_by_receipt = {
        "red-source-receipt.txt": validate_receipt_expectations(package / "red-source-receipt.txt", RED_EXPECTED),
        "green-production-receipt.txt": validate_receipt_expectations(package / "green-production-receipt.txt", GREEN_EXPECTED),
        "repeat-green-receipt.txt": validate_receipt_expectations(package / "repeat-green-receipt.txt", GREEN_EXPECTED),
        "canonical-green-2-receipt.txt": validate_receipt_expectations(package / "canonical-green-2-receipt.txt", GREEN_EXPECTED),
    }
    for summary_name, receipt_name in SUMMARY_TO_RECEIPT.items():
        validate_summary_observations(package, summary_name, rows_by_receipt[receipt_name])
    validate_instrumentation_and_native_binding(package, rows_by_receipt)
    validate_canonical_green(package, rows_by_receipt)
    validate_report(package)
