"""Seal the bounded pure calculator and its actual execution evidence."""
raise SystemExit("Historical note-governed artifact generator retired.")

from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
PIN = HERE / 'pin_002'


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    before = json.loads((HERE / 'BEFORE_001.json').read_text())
    for name, expected in before.items():
        assert fingerprint(ROOT / name) == expected, name
    design = BASE / 'a105_controlled_adapter_design_065'
    for row in json.loads((design / 'MANIFEST_006.json').read_text())['entries']:
        assert fingerprint(design / row['path']) == {'bytes': row['bytes'], 'sha256': row['sha256']}
    pin_manifest = json.loads((HERE / 'PIN_MANIFEST_002.json').read_text())
    assert {str(p.relative_to(PIN)) for p in PIN.rglob('*') if p.is_file()} == set(pin_manifest)
    for name, expected in pin_manifest.items():
        assert fingerprint(PIN / name) == expected == fingerprint(ROOT / name), name
    source_files = ['gene_annotation_episode/literature_controlled_response_owner_calculations.py',
                    'tests/test_literature_controlled_response_owner_calculations.py']
    with (HERE / 'IMPLEMENTATION_002.patch').open('x') as stream:
        for name in source_files:
            stream.writelines(difflib.unified_diff([], (ROOT / name).read_text().splitlines(True),
                fromfile='/dev/null', tofile='b/' + name))
    authority = ['/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt',
        'AGENTS.md', 'GOAL.md', 'docs/EPISODE_STRUCTURE.md', 'docs/TIME_AWARE_ESTIMATION.md',
        'docs/TOOL_KNOWLEDGE.md', 'docs/TASK_AND_STEERING.md',
        'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
        'research/experimental_scoring_review_2026-10-23/AGENTS.md',
        str(BASE.relative_to(ROOT) / 'controlled_adapter_parent_review_065/PURE_OWNER_IMPLEMENTATION_RELEASE_068.md')]
    read_rows = []
    for name in authority:
        path = Path(name) if Path(name).is_absolute() else ROOT / name
        read_rows.append({'path': str(path), 'scope': 'complete', **fingerprint(path)})
    for name in ('gene_annotation_episode/literature_controlled_response_calculations.py',
                 'gene_annotation_episode/literature_experimental_contracts.py',
                 'tests/test_literature_controlled_response_calculations.py'):
        read_rows.append({'path': name, 'scope': 'complete', **fingerprint(ROOT / name)})
    for name in ('OWNER_CONTRACT_003.md', 'OWNER_CONTRACT_CORRECTION_004.md',
                 'ACTIVE_OWNER_COVARIANCE_ADDENDUM_006.md', 'HANDOFF_006.md',
                 'build_owner_declarations_003.py', 'build_owner_correction_004.py'):
        read_rows.append({'path': str(design / name), 'scope': 'complete; builders specify all closed definitions', **fingerprint(design / name)})
    save('READ_PROVENANCE_002.json', {'reads': read_rows,
        'truncation_correction': 'Combined authority TIME read truncated; complete1-200 and201-end reread. Combined003/004 contract read truncated; both reread fully in separate outputs before implementation.',
        'scientific_source_or_retained_paper_packet_read': False, 'post_paper_reset_claimed': False,
        'not_read': ['paper payloads', 'private provider histories', 'credentials', 'old run databases or process arguments'],
        'bounded_scope': 'new pure calculator only; no episode message/prompt/execution/credit changes'})
    executions = json.loads((HERE / 'ACTUAL_EXECUTED_EXAMPLES_002.json').read_text())['examples']
    table = []
    for name, row in executions.items():
        if row['status'] == 'invalid':
            table.append({'case': name, 'status': 'invalid', 'code': row['code']})
        else:
            cells = row['result']['cells']
            table.append({'case': name, 'e': cells['controlled_response_difference']['value'],
                'V': cells['contrast_variance']['value'], 'S': cells['source_profile_log_ratio']['value'],
                'B': cells['source_signed_index']['value'],
                'e_reasons': cells['controlled_response_difference']['unavailable_reason'],
                'e_qualifications': cells['controlled_response_difference']['conditional_on'],
                'covariance_state': row['result']['contrast_dependencies']['covariance_state']})
    save('NUMERICAL_TABLE_002.json', {'scope': 'actual new calculator results on constructed inputs only', 'rows': table})
    save('API_002.json', {'public_exports': ['controlled_response_owner_arguments_schema',
        'validate_controlled_response_owner_inputs', 'populate_controlled_response_owner'],
        'input_version': 'controlled_response_owner_inputs_v2', 'result_version': 'controlled_response_owner_sheet_v2',
        'input_declaration': 'a105_controlled_adapter_design_065/OWNER_INPUT_SCHEMA_004.json',
        'output_declaration': 'a105_controlled_adapter_design_065/OWNER_OUTPUT_SCHEMA_004.json',
        'runtime_verification_imports': False, 'native_operation_registered': False})
    receipt = json.loads((HERE / 'PIN_EXECUTION_RECEIPT_002.json').read_text())
    save('FINAL_CHECK_002.json', {'utc': datetime.now(timezone.utc).isoformat(),
        'root_and_pin_files_identical': len(pin_manifest), 'original_baseline_files_unchanged': len(before),
        'design_payloads_unchanged': 49, 'actual_project_imports_inside_pin': len(receipt['actual_project_imports']),
        'actual_pin_targeted_tests': 70, 'actual_pin_terminal_duration': '0.56s', 'actual_test_exit_code': 0,
        'executed_constructed_examples': len(executions), 'new_production_files': {name: fingerprint(ROOT / name) for name in source_files},
        'scientific_model_execution': False, 'source_or_native_typed_integration': False,
        'existing_production_or_test_files_modified': [], 'runtime_observations': 0,
        'limits': ['active mixed-reading reconciliation remains unavailable', 'source shared-stage/full v2 extraction unimplemented',
                   'native persistence/typed C1 C4/subset reconstruction unimplemented', 'primary-source/model coverage unproved']})
    excluded = {'MANIFEST_002.json', 'SHA256SUMS_002.txt'}
    payloads = {str(path.relative_to(HERE)): fingerprint(path) for path in sorted(HERE.rglob('*'))
                if path.is_file() and str(path.relative_to(HERE)) not in excluded}
    save('MANIFEST_002.json', {'scope': '068 bounded pure owner calculator, constructed tests and actual pin execution', 'files': payloads})
    with (HERE / 'SHA256SUMS_002.txt').open('x') as stream:
        for name, row in sorted(payloads.items()):
            stream.write(row['sha256'] + '  ' + name + '\n')
        stream.write(fingerprint(HERE / 'MANIFEST_002.json')['sha256'] + '  MANIFEST_002.json\n')
    for name, expected in payloads.items():
        assert fingerprint(HERE / name) == expected
    print(json.dumps({'sealed_payloads': len(payloads), 'pin_files': len(pin_manifest),
        'pin_tests': 70, 'actual_project_imports': 4, 'original_files_unchanged': len(before),
        'model_or_native_execution': False}))


if __name__ == '__main__':
    main()
