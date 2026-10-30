"""Record native Mauve components without claiming an integrated BV-BRC tool."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / 'WORK_STATUS.json'
raw = path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == '0be0337bba69688e011124366d0af35b943cd6af667ba9b604774c9a11a26901'
assert not (HERE / 'PROGRESS_UPDATE_024.json').exists()
work = json.loads(raw)
old = deepcopy(work)


def hashed(relative):
    return {'path': relative, 'sha256': hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()}


combined_path = 'verification/tool_graders_bvbrc_genome_alignment_inputs_2026-10-25/COMBINED_TEST_002.json'
combined = json.loads((ROOT / combined_path).read_text())
assert combined['returncode'] == 0 and combined['source_unchanged']
assert combined['counts'] == dict(tests=289, errors=0, failures=0, skipped=0)
for source, digest in combined['source_after'].items():
    assert hashed(source)['sha256'] == digest, source
xml_path = 'verification/tool_graders_bvbrc_genome_alignment_inputs_2026-10-25/combined-002.xml'
suite = ET.parse(ROOT / xml_path).getroot().find('testsuite')
assert len(suite.findall('testcase')) == 289
assert all(int(suite.attrib[k]) == 0 for k in ('errors', 'failures', 'skipped'))

v4_path = 'verification/tool_graders_mauve_v4_2026-10-25/VERIFICATION_001.json'
v4 = json.loads((ROOT / v4_path).read_text())
for item in v4['owned_source_hashes'] + v4['artifacts'] + [v4['official_native']]:
    assert hashed(item['path'])['sha256'] == item['sha256']
assert v4['official_example']['known_union_bases'] == [690, 2000]
assert v4['official_example']['native_lengths'] == [693, 2000]
sidecars_path = 'verification/tool_graders_mauve_sidecars_2026-10-25/FILLED_EXAMPLES_001.json'
sidecars = json.loads((ROOT / sidecars_path).read_text())
assert [r['raw_line'] for r in sidecars['backbone_document']['rows']] == [
    '-19\t-50\t1\t31\t0\t0', '-1\t-18\t32\t49\t-1\t-19']

evidence_id = 'GENOME-ALIGNMENT-NATIVE-COMPONENTS-024'
evidence = {
    'id': evidence_id,
    'kind': 'native_format_parsers_calculators_and_closed_input_relationships',
    'summary': 'Implemented legacy Mauve v4 parser/calculator, coordinate-backbone and BBCols parsers/calculators, and closed GenomeAlignment input/association validators. Combined suite passed289 tests:78 v4,161 sidecar and50 input-contract tests. Current source hashes match the run. Earlier128/211 component-suite counts overlap and are not added.',
    'qualification': 'These are component implementations, not the complete BV-BRC GenomeAlignment capability. Provider metadata extraction with actual task/input custody, provider sheet/calculation request binding, bundle integration, tool information, typed returns and full episode verification remain unfinished. Actual retained native format examples are distinguished from synthetic task/source/interval joins. No live BV-BRC job or new native execution is established. Root read all four v4 production modules and checked three additional dependent-denominator cases; full sidecar source review remains pending.',
    'filled_examples': {
        'official_mauve_v4': v4['official_example'],
        'synthetic_v4': v4['synthetic_example'],
        'sidecars': 'Official backbone has native signed coordinate rows [-19,-50,1,31,0,0] and [-1,-18,32,49,-1,-19]. Official BBCols rows are retained separately. Synthetic same-run source/interval joins enable the stated staged-input and block-denominator calculations; those joins are not live service evidence.',
    },
    'reports': [hashed(p) for p in (
        combined_path, xml_path,
        'verification/tool_graders_bvbrc_genome_alignment_inputs_2026-10-25/combined-002.log',
        v4_path, sidecars_path,
        'verification/tool_graders_mauve_v4_2026-10-25/ROOT_DENOMINATOR_REVIEW_003.json',
        'verification/tool_graders_mauve_sidecars_2026-10-25/HANDOFF_001.md',
        'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/IMPLEMENTATION_OWNERSHIP_003.md',
        'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/INPUT_RELATIONSHIPS_004.md',
        'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/HASH_CORRECTION_005.md',
    )],
}
assert evidence_id not in {r['id'] for r in work['verification_evidence']}
for row in work['rows']:
    if row['id'] == 'C-L202-GenomeAlignment':
        row.update(
            overall='native_component_implementation_provider_and_episode_binding_unfinished',
            numerical_sheet='v4_and_sidecar_numerical_components_implemented_provider_sheet_unfinished',
            native_parser='v4_backbone_bbcols_tested_with_retained_native_bytes_neutral_XMFA_available',
            metadata_extractor='closed_input_relationship_validators_implemented_actual_record_extraction_unfinished',
            deterministic_calculator='v4_and_sidecar_calculators_tested_provider_calculation_plan_unfinished',
            numerical_verification='289_component_tests_passed_native_and_synthetic_filled_examples_retained',
            integration_verification='A_B_C_component_interfaces_tested_no_application_episode_path')
        row['evidence_ids'].append(evidence_id)
        row['note'] += (' Update024:289 combined component checks passed with unchanged source hashes; retained official v4 and sidecar outputs have numerical examples. '
                        'Same-run input and interval joins in these examples are synthetic. Provider extraction, calculation-plan/sheet integration, tool information, typed-return binding and complete episode/live-resource verification remain unfinished. '
                        'Root checked the v4 native-versus-staged denominator distinction: source conflicts withhold staged fractions while retaining independently valid native fractions. No complete scientific tool is claimed.')
for row in work['resource_bindings']:
    if row['id'] == 'C-L202-GenomeAlignment::api':
        row.update(native_format_observed='official_native_v4_backbone_bbcols_and_XMFA_examples_not_live_BV_BRC_job',
                   integration_verification='289_pure_component_interface_checks_no_application_episode_path')
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
record = {
    'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before, 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'previous_goal_turn_classification': 'no progress: answered the user\'s binding-versus-method_loop question with existing evidence; no implementation change in that question turn.',
    'current_continuation_progress': 'Polled actual session30167 to terminal success; verified289 checks and current source hashes, reviewed v4 modules, exercised three denominator-independence cases and updated fixed accounting. Existing full Workflow009 confirmed live by its owner without restart.',
    'changes': changes, 'added_evidence': [evidence], 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': 0,
}
with (HERE / 'PROGRESS_UPDATE_024.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
path.write_bytes(updated)
print(json.dumps({'checkpoint': 24, 'changed_rows_and_bindings': len(changes),
                  'scope_rows': 308, 'resource_bindings': 288,
                  'status_sha256': record['new_status_sha256']}))
