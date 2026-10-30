"""Index final retained examples without executing or regrading native work."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def relative(path):
    return str(path.relative_to(ROOT))


def retained(case_directory, reference):
    digest = reference.removeprefix('artifact_')
    path = case_directory / 'state/artifacts' / digest[:2] / digest
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    return {'artifact_ref': reference, 'path': relative(path), 'size_bytes': len(raw)}


def checks(name, expected_count):
    directory = HERE / name
    receipt = json.loads((directory / 'receipt.json').read_text())
    assert receipt['returncode'] == 0
    suite, = ET.parse(directory / 'junit.xml').getroot()
    assert int(suite.attrib['tests']) == expected_count
    assert int(suite.attrib['failures']) == int(suite.attrib['errors']) == int(suite.attrib['skipped']) == 0
    return {'check': name, 'tests_passed': expected_count, 'seconds': float(suite.attrib['time']),
        'receipt': relative(directory / 'receipt.json'), 'junit': relative(directory / 'junit.xml'),
        'changed_sources': receipt['changed_sources'], 'sources_unchanged': receipt['sources_unchanged']}


def case_records(name):
    result = []
    for path in sorted((HERE / name / 'temporary').glob('*/CASE.json')):
        if path.parent.is_symlink():
            continue
        case = json.loads(path.read_text())
        outcomes = case.get('outcomes', [case.get('result')])
        bodies = [outcome['result'] for outcome in outcomes]
        row = {'program': case['program'], 'mode': case['mode'], 'case': relative(path),
            'native_identity': case['native_plan']['identity'], 'results': []}
        for body in bodies:
            prepared = body['prepared']
            result_row = {'source_ref': body['source_ref'], 'complete': body['complete'],
                'failures': body['failures'], 'retained': {}}
            if prepared is not None:
                for key in ('bundle_artifact_ref', 'grading_artifact_ref', 'sheet_artifact_ref',
                            'calculations_artifact_ref'):
                    if prepared.get(key) is not None:
                        result_row['retained'][key] = retained(path.parent, prepared[key])
            row['results'].append(result_row)
        example = path.parent / 'NUMERICAL_EXAMPLE.json'
        if example.exists():
            row['numerical_example'] = relative(example)
        result.append(row)
    return result


if __name__ == '__main__':
    runs = [checks('check009', 36), checks('check010', 76)]
    workflow, nested = case_records('check009'), case_records('check010')
    assert len(workflow) == 36 and len(nested) == 16
    examples = [row for row in workflow if 'numerical_example' in row]
    assert len(examples) == len({(row['program'], row['mode']) for row in examples}) == 26
    assert len({row['program'] for row in examples}) == 10
    selected_nested = [row for row in nested if not Path(row['case']).parent.name.startswith('test_')]
    assert len(selected_nested) == len({row['program'] for row in selected_nested}) == 10
    index = {'version': 'hmmer_preparation_w1_evidence_v1', 'runs': runs,
        'tests_passed': 112, 'native_attempts': len(workflow) + len(nested),
        'native_modes': 26, 'slotted_native_programs': 10,
        'scope': 'Scripted engineering decisions; real bounded native execution and shared episode boundaries.',
        'workflow_cases': workflow, 'nested_cases': nested}
    (HERE / 'EVIDENCE_INDEX.json').write_text(json.dumps(index, indent=2) + '\n')
    print(json.dumps({key: index[key] for key in ('tests_passed', 'native_attempts', 'native_modes',
        'slotted_native_programs', 'runs')}, indent=2))
