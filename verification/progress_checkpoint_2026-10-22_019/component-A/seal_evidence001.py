"""Seal only this owner's closed synthetic component evidence, without SQL."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import xml.etree.ElementTree as ET

ROOT = Path('/tmp/direct-hmmer-operation-ports-A-20261022-001-btxj3p5g')
CODE = Path('/tmp/gene-annotation-configured-caller-20261022-008')
SOURCE_SHA = '6093fc9932d5e4b1cff360a4b9ba770ecb1e3b4acd0dad6f91c4bf2c1de31263'
TEST_SHA = 'c2b79f821355960821cc5e3363be0f949d4223637c44dbb972402e422cf77a7a'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for data in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def save(name, value):
    path = ROOT / name
    data = canonical(value) + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data); handle.flush(); os.fsync(handle.fileno())
    return {'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def inventory():
    files, directories, aliases = [], [], []
    def visit(parent):
        with os.scandir(parent) as handle:
            entries = sorted(handle, key=lambda item: item.name)
        for entry in entries:
            path = Path(entry.path); relative = path.relative_to(ROOT).as_posix()
            s = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(s.st_mode):
                target = os.readlink(path)
                normalized = Path(os.path.normpath(str(path.parent / target)))
                internal = normalized.is_relative_to(ROOT)
                aliases.append({'path': relative, 'target': target,
                    'target_member': normalized.relative_to(ROOT).as_posix() if internal else None,
                    'known_internal': internal, 'external_target_not_followed': not internal})
            elif stat.S_ISDIR(s.st_mode):
                directories.append({'path': relative, 'mode': format(stat.S_IMODE(s.st_mode), '04o')})
                visit(path)
            elif stat.S_ISREG(s.st_mode):
                files.append({'path': relative, 'sha256': digest(path), 'bytes': s.st_size,
                              'mode': format(stat.S_IMODE(s.st_mode), '04o')})
            else:
                raise ValueError('Unexpected special node preserved without opening: ' + relative)
    visit(ROOT)
    return files, directories, aliases


def main():
    assert digest(CODE / 'gene_annotation_episode/public_search_operations.py') == SOURCE_SHA
    assert digest(CODE / 'tests/test_direct_hmmer_operation_ports.py') == TEST_SHA
    runs = []
    for number, expected in ((1, (109, 0)), (2, (2, 3)), (3, (114, 0))):
        directory = ROOT / f'invocation{number:03d}'
        result = json.loads((directory / 'RESULT001.json').read_bytes())
        before = json.loads((directory / 'INPUTS_BEFORE001.json').read_bytes())
        after = json.loads((directory / 'INPUTS_AFTER001.json').read_bytes())
        assert before == after and result['selected_guards_unchanged'] is True
        xml = ET.parse(directory / 'pytest.xml')
        cases = xml.findall('.//testcase')
        failures = sum(case.find('failure') is not None or case.find('error') is not None for case in cases)
        skipped = sum(case.find('skipped') is not None for case in cases)
        assert (len(cases) - failures - skipped, failures) == expected and skipped == 0
        assert result['exit_code'] == (1 if failures else 0)
        suites = xml.findall('.//testsuite')
        runs.append({'invocation': number, 'passed': expected[0], 'failed': failures,
            'skipped': skipped, 'exit_code': result['exit_code'],
            'pytest_suite_seconds': [suite.attrib['time'] for suite in suites],
            'source_sha256': before['gene_annotation_episode/public_search_operations.py']['sha256'],
            'test_sha256': before['tests/test_direct_hmmer_operation_ports.py']['sha256'],
            'selected_guards_unchanged': True,
            'xml': {'path': f'invocation{number:03d}/pytest.xml', 'sha256': digest(directory / 'pytest.xml')},
            'nodeids_preserving_multiplicity': [case.attrib.get('classname', '') + '.' + case.attrib['name'] for case in cases]})
    assert runs[-1]['source_sha256'] == SOURCE_SHA and runs[-1]['test_sha256'] == TEST_SHA
    implementation = hashlib.sha256()
    runtime_paths = sorted(path for package in ('gene_annotation_episode', 'method_loop')
                           for path in (CODE / package).rglob('*.py'))
    for path in runtime_paths:
        implementation.update(path.relative_to(CODE).as_posix().encode() + b'\0')
        implementation.update(bytes.fromhex(digest(path)))
    save('RESULTS_FINAL001.json', {
        'version': 'direct_hmmer_operations_A_component_results_v1', 'status': 'final_owned_module_passed',
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'checkout': str(CODE),
        'owned_source_sha256': SOURCE_SHA, 'owned_test_sha256': TEST_SHA,
        'invocations': runs, 'final_invocation': 3, 'final_counts': {'passed': 114, 'failed': 0, 'skipped': 0},
        'do_not_sum_overlapping_historical_counts': True,
        'runtime_pin_at_sealing_only': {'sha256': implementation.hexdigest(), 'files': len(runtime_paths)},
        'scope': 'Actual Store and ProviderJobOperations with isolated synthetic stores/scripted fixture clients. No live/public/model/native/scientific workspace.',
        'first_failures': 'invocation002 retains raw NaN/Infinity cached-result custody rejection and empty-link wrong-code failures; invocation001 remains historical109pass.',
        'correction': {'path': 'correction002.patch', 'sha256': digest(ROOT / 'correction002.patch'),
            'meaning': 'Raw provider body parsing matches existing protocol; empty linked receipt is invalid shape. No downstream scientific success inferred from nonfinite raw bytes.'},
        'limits': ['Component tests, not configured science or numerical/model evidence.',
            'The source pin at sealing is a point-in-time inventory, not a whole-source before/after test guard.',
            'Root owns connected receipt/credit/forecast and detached fixed-case worker proofs.',
            'Legacy fallback classification means no currently committed O/S/C/R/B; wholly erased history remains observationally indistinguishable.',
            'Origin is factual scheduling/import/replay only; it is not HTTP-send, duration or physical-attempt support.',
            'Fixture thread gates and their timeouts are test controls, not runtime stopping/polling policy.']})
    files, directories, aliases = inventory()
    save('PRESEAL_MODES001.json', {'version': 'direct_hmmer_A_evidence_preseal_modes_v1',
        'root_mode': format(stat.S_IMODE(ROOT.lstat().st_mode), '04o'),
        'regular_members': files, 'directories': directories, 'aliases': aliases,
        'policy': 'Only remove write bits in this temporary evidence tree. No checkout source/test mode or bytes are changed.'})
    for path in sorted(ROOT.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if not path.is_symlink():
            os.chmod(path, stat.S_IMODE(path.lstat().st_mode) & ~0o222)
    files, directories, aliases = inventory()
    known = {row['path'] for row in files} | {row['path'] for row in directories}
    for alias in aliases:
        if alias['known_internal']:
            assert alias['target_member'] in known
    manifest = {'version': 'sealed_direct_hmmer_A_component_evidence_manifest_v1',
        'root': str(ROOT), 'root_mode': format(stat.S_IMODE(ROOT.lstat().st_mode) & ~0o222, '04o'),
        'regular_members': files, 'regular_member_count': len(files),
        'regular_member_bytes': sum(row['bytes'] for row in files), 'directories': directories,
        'aliases': aliases, 'alias_count': len(aliases),
        'external_alias_count': sum(not row['known_internal'] for row in aliases),
        'self_excluded': 'MANIFEST_FINAL001.json', 'owned_source_sha256': SOURCE_SHA,
        'owned_test_sha256': TEST_SHA, 'final_counts': {'passed': 114, 'failed': 0, 'skipped': 0}}
    row = save('MANIFEST_FINAL001.json', manifest)
    os.chmod(ROOT, stat.S_IMODE(ROOT.lstat().st_mode) & ~0o222)
    after_files, after_directories, after_aliases = inventory()
    assert {item['path'] for item in after_files} == {item['path'] for item in files} | {'MANIFEST_FINAL001.json'}
    assert [item for item in after_files if item['path'] != 'MANIFEST_FINAL001.json'] == files
    assert after_directories == directories and after_aliases == aliases
    print(json.dumps({'root': str(ROOT), 'manifest': row, 'members_excluding_manifest': len(files),
        'member_bytes_excluding_manifest': manifest['regular_member_bytes'], 'aliases': len(aliases),
        'final_counts': manifest['final_counts'], 'runtime_pin_at_seal': implementation.hexdigest()}, sort_keys=True))


if __name__ == '__main__':
    main()
