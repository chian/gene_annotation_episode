"""Index retained verification data without parsing native output or regrading."""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent


def artifact(case_directory, reference):
    digest = reference.removeprefix('artifact_')
    assert len(digest) == 64 and all(char in '0123456789abcdef' for char in digest)
    path = case_directory / 'state' / 'artifacts' / digest[:2] / digest
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    return {'artifact_ref': reference, 'path': str(path.relative_to(ROOT)),
        'sha256': digest, 'size_bytes': len(raw)}


def main():
    directory = EVIDENCE / sys.argv[1]
    receipt = json.loads((directory / 'receipt.json').read_text())
    xml = ET.parse(directory / 'tests.xml').getroot()
    suites = list(xml.iter('testsuite'))
    result = {'version': 'infernal_preparation_workflow_modes_evidence_v1',
        'receipt': str((directory / 'receipt.json').relative_to(ROOT)),
        'returncode': receipt['returncode'],
        'pytest': {key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
            for key in ('tests', 'failures', 'errors', 'skipped')},
        'duration_seconds': sum(float(suite.attrib.get('time', 0)) for suite in suites),
        'source_changes_during_run': receipt['source_changes_during_run'], 'cases': []}
    for example_path in sorted((directory / 'temporary' / 'pytest').rglob('NUMERICAL_EXAMPLE.json')):
        case_directory = example_path.parent
        example = json.loads(example_path.read_text())
        saved = json.loads((case_directory / 'CASE.json').read_text())
        body = saved['outcomes'][0]['result']
        prepared = body['prepared']
        row = {key: example[key] for key in ('program', 'mode', 'native_argv', 'returncode',
            'selector', 'typed_return', 'scientific_observation_count')}
        row.update(example_path=str(example_path.relative_to(ROOT)),
            case_path=str((case_directory / 'CASE.json').relative_to(ROOT)),
            numerical_artifacts={name: artifact(case_directory, prepared[name + '_artifact_ref'])
                for name in ('bundle', 'grading', 'sheet', 'calculations')},
            captured_artifacts=[{**occurrence, **artifact(case_directory, occurrence['artifact_ref'])}
                for occurrence in prepared['occurrences']],
            root_gains=saved['root_gains'], failures=example['failures'])
        recalculated = case_directory / 'RECALCULATED_EXAMPLE.json'
        if recalculated.exists():
            row['recalculated_example'] = {'path': str(recalculated.relative_to(ROOT)),
                'sha256': hashlib.sha256(recalculated.read_bytes()).hexdigest()}
        result['cases'].append(row)
    result['cases'].sort(key=lambda row: (row['program'], row['mode']))
    if receipt['returncode'] == 0:
        assert len(result['cases']) == result['pytest']['tests'] == 20
        assert not any(result['pytest'][key] for key in ('failures', 'errors', 'skipped'))
        assert all(row['scientific_observation_count'] == 0 for row in result['cases'])
    output = directory / 'EVIDENCE_INDEX.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# Retained native Workflow examples', '',
        'These links identify actual retained data. Preparation quantities are not annotation-confidence scores.', '',
        '| Native selection | Typed return and diagnostics | Populated sheet | Separate calculations |',
        '| --- | --- | --- | --- |']
    for row in result['cases']:
        def link(path, label):
            return '[' + label + '](' + str(ROOT / path) + ')'
        lines.append('| ' + row['program'] + ' / ' + row['mode'] + ' | ' +
            link(row['example_path'], 'Full typed example') + ' | ' +
            link(row['numerical_artifacts']['sheet']['path'], 'Sheet') + ' | ' +
            link(row['numerical_artifacts']['calculations']['path'], 'Calculations') + ' |')
    (directory / 'EXAMPLES.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'index': str(output), 'cases': len(result['cases']), 'pytest': result['pytest']}))


if __name__ == '__main__':
    main()
