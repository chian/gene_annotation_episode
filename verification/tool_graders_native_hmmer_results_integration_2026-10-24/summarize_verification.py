"""Derive compact examples from the retained final Workflow case records."""
from collections import Counter
import json
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent


def main():
    verification = json.loads((DIRECTORY / 'VERIFICATION.json').read_text())
    assert verification['returncode'] == 0 and verification['production_unchanged']
    assert verification['tests_unchanged']
    cases = []
    for path in sorted((DIRECTORY / 'final-pytest').glob('*/CASE.json')):
        if path.parent.is_symlink():
            continue
        case = json.loads(path.read_text())
        case['case_path'] = str(path.relative_to(DIRECTORY))
        cases.append(case)
    modes = []
    for case in cases:
        if not Path(case['case_path']).parts[1].startswith('test_selected_native_results'):
            continue
        rows = case['returned_forms'][0]['rows']
        example = next(row for row in rows if row['status'] == 'published')
        if case['label'] == 'hmmalign_align_trim':
            example = next(row for row in rows if any(item['name'] == 'original_length'
                and item['value'] == 26 for item in row['measurements']))
        modes.append({'label': case['label'], 'case_path': case['case_path'],
            'row_status_counts': dict(Counter(row['status'] for row in rows)),
            'example_returned_row': example,
            'reverse_rows': [row for row in rows if row['strand'] == 'minus'],
            'iteration_counts': dict(Counter(str(row['iteration']) for row in rows)),
            'parent_gains': case['parent_gains'],
            'results_gains': case['results'][0]['gains'],
            'results_future_expectation': case['results'][0]['future_expectation'],
            'selected_actions': case['selected_actions'],
            'controller_observations': case['controller_observations'],
            'scripted_decision_calls': case['scripted_decision_calls'],
            'source_sheet_artifacts': {key: value for key, value in case['results'][0]['prepared'].items()
                if key.endswith('_artifact_ref')}})
    assert len(modes) == 11, len(modes)
    fault_cases = [{key: case[key] for key in ('case_path', 'label', 'partial_result_fixture_estimator',
        'parent_gains', 'selected_actions', 'controller_observations', 'scripted_decision_calls',
        'returned_forms', 'results')} for case in cases
        if not Path(case['case_path']).parts[1].startswith('test_selected_native_results')]
    result = {'verification': 'VERIFICATION.json', 'mode_examples': modes, 'other_workflow_cases': fault_cases}
    (DIRECTORY / 'NUMERICAL_EXAMPLES.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'nonempty_mode_count': len(modes), 'total_workflow_cases': len(cases),
        'actions': sum(case['selected_actions'] for case in cases),
        'controller_observations': sum(case['controller_observations'] for case in cases),
        'scripted_decision_calls': sum(case['scripted_decision_calls'] for case in cases)}))
    for mode in modes:
        print(mode['label'], mode['row_status_counts'],
              {item['name']: item['value'] for item in mode['example_returned_row']['measurements']},
              'results_gain=', mode['results_gains'])


if __name__ == '__main__':
    main()
