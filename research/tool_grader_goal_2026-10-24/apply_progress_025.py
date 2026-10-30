"""Record C receipt extraction/association tests without claiming an integrated tool."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / 'WORK_STATUS.json'
raw = path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == '95663fe1d5e7de1c95b8b7e1e7e763893738205484c0642effd09564fcb2a451'
assert not (HERE / 'PROGRESS_UPDATE_025.json').exists()
work = json.loads(raw)
old = deepcopy(work)


def hashed(relative):
    return {'path': relative, 'sha256': hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()}


base = 'verification/tool_graders_bvbrc_genome_alignment_associations_2026-10-25/'
combined = json.loads((ROOT / base / 'COMBINED_TEST_002.json').read_text())
assert combined['returncode'] == 0 and combined['source_unchanged']
assert combined['counts'] == dict(tests=209, errors=0, failures=0, skipped=0)
for source, expected in combined['source_after'].items():
    assert hashed(source)['sha256'] == expected, source
examples = json.loads((ROOT / base / 'EXAMPLES_001.json').read_text())
v4 = examples['examples'][0]
assert [(r['known_union_bases']['value'], r['denominator_bases']['value'])
        for r in v4['native_declared_denominator']['coverage']] == [(690, 693), (2000, 2000)]
assert all(r['coverage_fraction']['value'] is None for r in v4['original_input_denominator']['coverage'])
evidence_id = 'GENOME-ALIGNMENT-RETAINED-EXTRACTION-025'
evidence = {
    'id': evidence_id,
    'kind': 'pure_actual_receipt_shape_extraction_and_native_artifact_association',
    'summary': 'Implemented C1 original request/log/FASTA extraction and C2 native artifact association against real retained receipt schemas and supplied bytes. Combined suite passed209 tests:129 C1,30 C2 and50 unchanged C value validators. Exact source hashes remained unchanged. These counts overlap the previous50 validator checks and are not added to the earlier289 count as unique tests.',
    'qualification': 'Native alignment files are retained upstream examples; original task, receipt and custody relationships are explicitly synthetic. Authenticated host receipt collection, provider sheet/bundle/return integration, actual tool information and complete Workflow/live-resource verification remain unfinished. Original staged bytes, genome census and interval export witnesses remain unknown. Root fully reviewed A/B and C2 plus shared receipt checks; complete root C1 extractor review remains pending. No complete scientific tool is claimed.',
    'filled_examples': {
        'native_member_counts': [len(r['associations']['value']['native_member_joins']) for r in examples['examples']],
        'native_union_and_declared_length': [[690, 693], [2000, 2000]],
        'coverage_requiring_original_inputs': [None, None],
        'task_and_custody': 'synthetic',
    },
    'reports': [hashed(p) for p in (
        base + 'COMBINED_TEST_002.json', base + 'combined-002.xml', base + 'combined-002.log',
        base + 'EXAMPLES_001.json', base + 'HANDOFF_001.md',
        'verification/tool_graders_bvbrc_genome_alignment_extraction_2026-10-25/VERIFICATION_RESULTS_001.json',
        'verification/tool_graders_bvbrc_genome_alignment_extraction_2026-10-25/OWNED_SOURCE_HASHES_001.json',
        'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/EXTRACTION_IMPLEMENTATION_006.md',
        'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/EXTRACTION_SHARED_HELPERS_007.md',
        'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/SHEET_IMPLEMENTATION_008.md',
        'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/BUNDLE_IMPLEMENTATION_009.md',
    )],
}
assert evidence_id not in {r['id'] for r in work['verification_evidence']}
for row in work['rows']:
    if row['id'] == 'C-L202-GenomeAlignment':
        row.update(overall='native_components_and_receipt_extractors_tested_provider_episode_binding_unfinished',
            metadata_extractor='C1_C2_receipt_bytes_request_log_FASTA_and_artifact_association_tested_host_collection_unfinished',
            numerical_verification='209_C_extraction_association_contract_tests_passed_separate_from_previous289_components',
            integration_verification='pure_C1_C2_native_component_path_tested_no_application_episode_path')
        row['evidence_ids'].append(evidence_id)
        row['note'] += (' Update025:209 combined C1/C2/value-contract tests passed with unchanged source hashes; every native example retains missing original source and interval relationships. '
            'Synthetic task/custody data does not prove live BV-BRC execution. A/B source review is now complete; root full C1 extractor review remains pending. '
            'Accepted D saved-sheet and E bundle interfaces permit independent coding; their provider integration, F typed returns, host collection, tool information and full Workflow/live checks remain unfinished.')
for row in work['resource_bindings']:
    if row['id'] == 'C-L202-GenomeAlignment::api':
        row.update(integration_verification='209_pure_C_extraction_association_checks_synthetic_custody_no_application_episode_path')
        row['evidence_ids'].append(evidence_id)
work['verification_evidence'].append(evidence)
assert len(work['rows']) == len(old['rows']) == 308
assert len(work['resource_bindings']) == len(old['resource_bindings']) == 288
assert work['complete_scientific_tools_claimed'] == old['complete_scientific_tools_claimed'] == 0
changes = []
for group in ('rows', 'resource_bindings'):
    original = {r['id']: r for r in old[group]}
    assert set(original) == {r['id'] for r in work[group]}
    changes.extend({'group': group, 'id': r['id'], 'before': original[r['id']], 'after': deepcopy(r)}
                   for r in work[group] if r != original[r['id']])
updated = (json.dumps(work, indent=2) + '\n').encode()
record = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before, 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'current_continuation_progress': 'Implemented C2; verified final C1/C2 with209 passing checks; retained four native examples and additive D/E ownership contracts. Answered binding-versus-method_loop question from actual code. Left Workflow009 running and all original execution sources unchanged.',
    'changes': changes, 'added_evidence': [evidence], 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_025.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
path.write_bytes(updated)
print(json.dumps({'checkpoint': 25, 'changed_rows_and_bindings': len(changes),
    'scope_rows': 308, 'resource_bindings': 288, 'status_sha256': record['new_status_sha256']}))
