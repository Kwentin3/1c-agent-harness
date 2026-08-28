from __future__ import annotations

import hashlib
import gzip
import importlib.util
import json
import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
EXPECTED_FILES = {
    'README.md',
    'behavior-summary.json',
    'clean-repeat-receipt.txt',
    'cost-ledger.json',
    'green-receipt.txt',
    'instrumentation.diff.gz',
    'metadata-only-red-receipt.txt',
    'native-runs.json',
    'oracle.py',
    'production-patch.diff.gz',
    'source-baseline-receipt.txt',
    'source-identity.json',
    'validate.py',
}
PHASES = ('source-baseline', 'metadata-only-red', 'green', 'clean-repeat')
CASES = ('P1', 'B1', 'P2', 'P3', 'P4', 'N1', 'N2', 'N3', 'N4', 'R1', 'R2')
POSITIVES = ('P1', 'B1', 'P2', 'P3', 'P4', 'R1')
NEGATIVES = ('N1', 'N2', 'N3', 'N4')
EXPECTED_TREES = {
    'source-baseline': '767311bd84ca55d9497d7dfca53b818975d08c3b5b3662bde77d999e4fbb7f4f',
    'metadata-only-red': 'd57ca89d4da558e4ef0d23377513ded8b2f2d896ceed8340041c760c720a518b',
    'green': '978c3953f95dff49d6fa1893d87b684178d885569fb7c4e31feff713b5be1a8d',
    'clean-repeat': '978c3953f95dff49d6fa1893d87b684178d885569fb7c4e31feff713b5be1a8d',
}
EXPECTED_PATCH_PAYLOADS = {
    'production': 'fe02c1b534af164294a2be3d37acccd0f36b6e392f7957c5b2a4e860e52b97f3',
    'instrumentation': 'c42cd1aa71b8d66a692ab89deaef7290623611946c682f70f510fad9d22b1f0f',
}
EXPECTED_FILE_HASHES = {
    'Documents/SalesInvoice.xml': {
        'sourceSha256': '2aadf05f9fc93e482fc6a450d914b58a2f657162a341757d547d4da07b9ef27a',
        'productionSha256': '1ea8e3b768b92e8653b48dfbb2c47b0784b9b9a69423eb37f8f644338773198a',
    },
    'Documents/SalesInvoice/Ext/ObjectModule.bsl': {
        'sourceSha256': '535bbbee743a15a92d536c824dd2b69418f6e1d0429b31d9f0b9ca2084a65611',
        'productionSha256': 'c644e1eb7a277354047f126f89eb29b6eb4836d910dd63d105c751751ccf0183',
    },
}
EXPECTED_RECEIPTS = {
    'source-baseline': ('95cbe060b1c5be7cf2edb7b070ea32bb0c6be9118f7a65d0fdc1e090e1cebe68', 'ff2913017c8f772cda621a7a06419a3cf1da7df6b17e8375eaa13b235976f43e'),
    'metadata-only-red': ('ffb760c4870966266e707e1d0d7f6e5ba6032486e84d0c366c0ebf4c57ee52f8', '4061670b7d00711516e85d83c6212e34397979037dd3ddcdadb184c10ce4577c'),
    'green': ('b0035a8dce6f2296a28be8221f0579a6ab9a124aae0a59e08be1ed792535042f', 'f697477fff094b00a6f1956fb501c054ff6c1eb24d6b27066cd3ee5948b5627b'),
    'clean-repeat': ('ec64911b5b3385de646c7d6c38d6396c911a6d949b5e8403cd017d100bd05f8d', 'f697477fff094b00a6f1956fb501c054ff6c1eb24d6b27066cd3ee5948b5627b'),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str):
    return json.loads((PACKAGE / name).read_text(encoding='utf-8'))


def load_oracle():
    spec = importlib.util.spec_from_file_location('issue23_oracle', PACKAGE / 'oracle.py')
    if spec is None or spec.loader is None:
        raise AssertionError('cannot load oracle')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def diff_payload(path: Path) -> bytes:
    return gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()


def diff_counts(path: Path):
    files = []
    added = removed = 0
    for line in diff_payload(path).decode('utf-8').splitlines():
        if line.startswith('+++ b/'):
            files.append(line[6:])
        elif line.startswith('+') and not line.startswith('+++'):
            added += 1
        elif line.startswith('-') and not line.startswith('---'):
            removed += 1
    return files, added, removed


def main() -> None:
    manifest = load_json('package-manifest.json')
    assert manifest['schemaVersion'] == 1
    artifacts = manifest['artifacts']
    assert set(artifacts) == EXPECTED_FILES
    actual = {path.name for path in PACKAGE.iterdir() if path.name != 'package-manifest.json'}
    assert actual == EXPECTED_FILES
    for name, digest in artifacts.items():
        assert sha(PACKAGE / name) == digest, name

    forbidden_private_roots = ('/' + 'workspace/', '.local/runs/' + 'native-cycle/')
    for path in PACKAGE.iterdir():
        if path.is_file() and path.suffix != '.gz':
            text = path.read_text(encoding='utf-8', errors='strict')
            for forbidden in forbidden_private_roots:
                assert forbidden not in text, path.name

    oracle = load_oracle()
    baseline = oracle.parse(PACKAGE / 'source-baseline-receipt.txt')
    red = oracle.parse(PACKAGE / 'metadata-only-red-receipt.txt')
    green = oracle.parse(PACKAGE / 'green-receipt.txt')
    repeat = oracle.parse(PACKAGE / 'clean-repeat-receipt.txt')
    oracle.validate_baseline(baseline)
    oracle.validate_behavior(green)
    oracle.validate_behavior(repeat)
    red_failed = False
    try:
        oracle.validate_behavior(red)
    except AssertionError:
        red_failed = True
    assert red_failed, 'metadata-only RED unexpectedly satisfies behavior oracle'
    assert red['metadata.attributeExists'] == ('true', 'Boolean')
    assert red['metadata.dateOnly'] == ('true', 'Boolean')
    for case in NEGATIVES:
        assert red[f'{case}.postedAfter'] == ('true', 'Boolean')
    green_view = {k: v for k, v in green.items() if k not in {'nonce', 'run.R'} and not k.endswith(('.documentRef', '.documentDate', '.dueDateInput', '.draftDueDate', '.postDueDate'))}
    repeat_view = {k: v for k, v in repeat.items() if k not in {'nonce', 'run.R'} and not k.endswith(('.documentRef', '.documentDate', '.dueDateInput', '.draftDueDate', '.postDueDate'))}
    assert green_view == repeat_view
    assert len(green_view) == 236

    behavior = load_json('behavior-summary.json')
    assert behavior['baseline']['attributeExists'] is False
    assert behavior['metadataOnlyRed']['metadata'] == {'attributeExists': True, 'name': 'PaymentDueDate', 'containsDate': True, 'dateOnly': True}
    assert behavior['green']['metadata'] == behavior['metadataOnlyRed']['metadata']
    assert behavior['repeatEquivalence'] == {'semanticLabelsCompared': 236, 'ignoredRunVariantLabels': 57, 'equal': True}
    for case in POSITIVES:
        assert behavior['green']['cases'][case]['postedAfter'] is True
        assert set(behavior['green']['cases'][case]['movements'].values()) == {'1'}
    for case in NEGATIVES + ('R2',):
        item = behavior['green']['cases'][case]
        assert item['postedAfter'] is False
        assert set(item['movements'].values()) == {'0'}
        assert item['before'] == item['after']

    identity = load_json('source-identity.json')
    assert identity['sourceCfSha256'] == '5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a'
    assert identity['snapshotManifestSha256'] == '70972b5e11901ca31c7f7ec67dca03f78986206b024be01aeb34e0e1f3ff6691'
    assert identity['snapshotClosure'] == {'declaredFiles': 5099, 'actualFiles': 5099, 'missing': 0, 'extra': 0, 'mismatch': 0, 'symlink': 0, 'writable': 0}
    assert identity['files'] == EXPECTED_FILE_HASHES
    assert identity['productionTreeSha256'] == EXPECTED_TREES['green']
    assert identity['greenRepeatTreeIdentityEqual'] is True
    assert identity['applicationProof']['payloadsAppliedFromExactGitCandidate'] is True
    assert all(identity['applicationProof']['reconstructsGreenBytes'].values())
    assert identity['applicationProof']['canonicalization']['terminalNewlineRequiredFor'] == ['CommonModules/JetServerCall/Ext/Module.bsl']
    production_archive = PACKAGE / 'production-patch.diff.gz'
    production_payload = diff_payload(production_archive)
    production_files, production_added, production_removed = diff_counts(production_archive)
    assert production_files == ['Documents/SalesInvoice.xml', 'Documents/SalesInvoice/Ext/ObjectModule.bsl']
    assert (production_added, production_removed) == (52, 0)
    assert identity['productionPatch']['archiveSha256'] == sha(production_archive)
    assert identity['productionPatch']['payloadSha256'] == hashlib.sha256(production_payload).hexdigest()
    assert identity['productionPatch']['payloadSha256'] == EXPECTED_PATCH_PAYLOADS['production']
    instrumentation_archive = PACKAGE / 'instrumentation.diff.gz'
    instrumentation_payload = diff_payload(instrumentation_archive)
    instrumentation_files, instrumentation_added, instrumentation_removed = diff_counts(instrumentation_archive)
    assert instrumentation_files == ['Ext/ManagedApplicationModule.bsl', 'CommonModules/JetServerCall/Ext/Module.bsl']
    assert (instrumentation_added, instrumentation_removed) == (247, 0)
    assert identity['instrumentation']['archiveSha256'] == sha(instrumentation_archive)
    assert identity['instrumentation']['payloadSha256'] == hashlib.sha256(instrumentation_payload).hexdigest()
    assert identity['instrumentation']['payloadSha256'] == EXPECTED_PATCH_PAYLOADS['instrumentation']
    patch_text = production_payload.decode('utf-8')
    assert patch_text.count('<Name>PaymentDueDate</Name>') == 1
    assert patch_text.count('ValueIsFilled(PaymentDueDate)') == 1
    assert 'BegOfDay(PaymentDueDate) < BegOfDay(Date)' in patch_text
    for forbidden in ('CurrentDate', 'AddMonth', 'AddDay'):
        assert forbidden not in patch_text
    for component_call in ('Day', 'Month', 'Year'):
        assert re.search(r'(?<!Of)' + component_call + r'\(PaymentDueDate\)', patch_text) is None

    native = load_json('native-runs.json')
    assert [item['phase'] for item in native['runs']] == list(PHASES)
    compacted_logical_bytes = 0
    for item in native['runs']:
        phase = item['phase']
        assert item['status'] == 'runtime_contract_completed'
        assert item['input']['sourceTreeSha256'] == EXPECTED_TREES[phase]
        prepared = item['preparedInvocation']
        assert prepared['sourceBefore'] == prepared['sourceAfter'] == prepared['copiedBeforeFreeze'] == prepared['frozenInputIdentity']
        assert prepared['sourceBefore']['sha256'] == EXPECTED_TREES[phase]
        assert prepared['generatedBindingKind'] == '1c-enterprise-launch-parameter'
        assert prepared['generatedBindingStatus'] == 'generated'
        assert item['create']['processReturn'] == 0 and item['create']['dumpResult'] == '0'
        assert item['load']['processReturn'] == 0 and item['load']['dumpResult'] == '0'
        assert item['load']['successMarker'] == 'Configuration successfully updated'
        assert item['runtime']['completed'] is True and item['runtime']['completeMarker'] == 'complete###true'
        assert item['runtime']['stableReads'] == 2
        assert (item['runtime']['rawReceiptSha256'], item['runtime']['publishedReceiptSha256']) == EXPECTED_RECEIPTS[phase]
        assert item['runtime']['publishedReceiptSha256'] == sha(PACKAGE / item['runtime']['publishedReceipt'])
        compaction = item['storageCompaction']
        assert compaction['status'] == 'completed'
        assert compaction['manualCleanupActions'] == 0
        assert compaction['completedRemovedPaths'] == ['frozen-input', 'run/work-copy', 'run/ib', 'run/home', 'run/tmp']
        compacted_logical_bytes += compaction['removedLogicalBytes']

    cost = load_json('cost-ledger.json')
    assert cost['elapsedToPackagedCandidateSeconds'] == 5222
    assert cost['nativeAttempts'] == cost['runPreparedCalls'] == 4
    assert cost['ownerInterventions'] == 1
    assert cost['ownerInterventionBreakdown'] == {'semanticOr1c': 0, 'operationalStorage': 1}
    assert cost['manualLifecycleActionsOutsideRunPrepared'] == 0
    incident = cost['operationalStorageIncident']
    assert incident['exactAllocationAtEnospcKnown'] is False
    assert incident['exactPerCommandCreatorHistoryKnown'] is False
    assert incident['issue23PreparedCopiesCreated'] == 4
    assert incident['issue23ConsumedPreparedCopiesRemovedBeforePackaging'] == 2
    assert incident['issue23PreparedCopiesRetainedAtRecovery'] == [
        '.local/prepared/issue23-green',
        '.local/prepared/issue23-repeat',
    ]
    assert incident['issue23ExternalReviewRootsAtRecovery']['count'] == 3
    assert incident['issue23ExternalReviewRootsAtRecovery']['allocatedBytes'] == 181727232
    assert incident['excludedPostIncidentPolicyTree'] == '.local/prepared/storage-policy-evidence-candidate'
    assert compacted_logical_bytes == 898852430
    assert incident['runPreparedCompaction'] == {
        'invocations': 4,
        'removedLogicalBytes': compacted_logical_bytes,
        'ownedTargetsOnly': True,
        'doesNotOwnPreparedOrExternalReviewRoots': True,
    }
    recovery = incident['recovery']
    assert recovery['ownerAuthorizationRequired'] is True
    assert recovery['elapsedSeconds'] == 806.624
    assert recovery['allowlistedPathsRemoved'] == 16
    assert recovery['removalPasses'] == 2
    assert recovery['permissionRetryAfterFullRevalidation'] == 1
    assert recovery['reclaimedAllocatedBytes'] == 5002485760
    assert recovery['largestRemovedPath'] == '.local/platform/1cv8'
    assert recovery['largestRemovedPathAllocatedBytes'] == 4155269120
    assert recovery['filesystemAtRecoveryStart'] == {'availableGiBDisplay': 4.5, 'usedPercent': 88}
    assert recovery['filesystemAfterRecovery'] == {'availableGiBDisplay': 9.3, 'usedPercent': 75}
    assert incident['acceptedIssue23RawArtifactsRemoved'] is False
    assert incident['portableClaimsDependOnRemovedRawArtifacts'] is False
    assert incident['productVerdict'] == 'functional fresh-agent goal loop proven; storage usability requires separate correction'
    assert cost['productionChange']['files'] == production_files
    assert cost['productionChange']['addedLines'] == 52
    assert cost['commonHarnessChangedFiles'] == cost['skillsChangedFiles'] == cost['newGeneralFrameworks'] == 0
    assert cost['freshExecutor']['unpublishedTaskSpecificSolutionReceived'] is False
    print('PASS issue23 evidence: manifest, RED/GREEN/repeat, source, native envelopes, cost')


if __name__ == '__main__':
    main()
