"""Record verified pure implementations without claiming provider completion."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
status_path = HERE / 'WORK_STATUS.json'
raw = status_path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == '8f6eebf761f2e2421071321b372e189d9bfd0ff6eea72d7ad14485c3c9c9037e'
assert not (HERE / 'PROGRESS_UPDATE_021.json').exists()
work = json.loads(raw)
old = deepcopy(work)
implementation = ROOT / 'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25'
math = ROOT / 'verification/tool_graders_bvbrc_metacats_biological_2026-10-25'
source = ROOT / 'verification/tool_graders_bvbrc_xmfa_sources_2026-10-25'
parser = ROOT / 'verification/tool_graders_bvbrc_xmfa_formats_2026-10-25'


def hashed(path):
    return {'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


math_tests = json.loads((math / 'TEST_RESULTS_002.json').read_text())
assert math_tests['returncode'] == 0 and math_tests['source_unchanged_during_run']
for row in math_tests['source_hashes']:
    assert hashed(ROOT / row['path'])['sha256'] == row['sha256']
source_tests = json.loads((source / 'TEST_RESULT_002.json').read_text())
assert source_tests['returncode'] == 0 and source_tests['unchanged']
for path, digest in source_tests['source_after'].items():
    assert hashed(ROOT / path)['sha256'] == digest
for path, count in ((math / 'combined-pure-002.xml', 360),
                    (source / 'source-and-formats-002.xml', 257)):
    suite = ET.parse(path).getroot().find('testsuite')
    assert len(suite.findall('testcase')) == count
    assert all(int(suite.attrib[k]) == 0 for k in ('failures', 'errors', 'skipped'))
replay = json.loads((source / 'SOURCE_REPLAY_003.json').read_text())
assert replay['case_count'] == len(replay['cases']) == 10
assert replay['source_unchanged'] and replay['retained_native_inputs_unchanged']
for case in replay['cases']:
    assert case['exact_no_io_saved_replay']
    for artifact in case['artifacts']:
        assert hashed(ROOT / artifact['path']) == artifact
review = json.loads((implementation / 'ROOT_MATH_REVIEW_020.json').read_text())
assert review['terminal_tests'] == 360 and review['collision_repair_confirmed']
assert review['old_results_not_rewritten'] and review['replay_cases_each'] == 7
assert review['complete_example_artifact_hashes_checked'] == 35

evidence_id = 'METACATS-BIOLOGICAL-MATH-XMFA-PARSER-SOURCE-021'
evidence = {
    'id': evidence_id,
    'kind': 'verified_pure_native_parsing_source_association_and_numerical_calculations',
    'summary': 'Independent MetaCATS biological counts/statistics/effects and expected-count adequacy are implemented; assignment-aware future native count identities fix the reproduced collision while old saved results replay unchanged. The combined pure suite has360 tests. Full Mauve1 XMFA parsing and source matching have257 tests and10 complete no-I/O saved replay cases.',
    'qualification': 'These are pure component checks with retained native data and explicit synthetic operands. Association142, coordinate/calculator143, MetaCATS provider144 and root MSA provider work remain unfinished at this checkpoint. No tool-library, complete provider/episode return, new live service, native program, HPC, evidence-axis or W05 completion is inferred.',
    'reports': [hashed(p) for p in (
        math / 'HANDOFF_001.md', math / 'TEST_RESULTS_002.json',
        math / 'FINAL_REPLAY_002.json', math / 'NATIVE_REKEY_MAPPINGS_001.json',
        implementation / 'ROOT_MATH_REVIEW_020.json',
        parser / 'FROZEN_HANDOFF.json', parser / 'HANDOFF.md',
        source / 'TEST_RESULT_002.json', source / 'SOURCE_REPLAY_003.json',
        source / 'INITIAL_REVIEW_001.json', source / 'HANDOFF_004.md',
        implementation / 'ACCEPTED_PROVIDER_WORKLOADS_019.json')],
}
assert evidence_id not in {row['id'] for row in work['verification_evidence']}
rows = {row['id']: row for row in work['rows']}
meta = rows['C-L205-MetaCATS']
meta['deterministic_calculator'] = 'native_and_biological_counts_statistics_effects_adequacy_and_multiplicity_verified_future_assignment_aware_native_ids'
meta['numerical_verification'] = '360_combined_pure_tests_7_native_7_biological_7_changed_epsilon_replays_provider_and_episode_checks_pending'
meta['note'] += (' Update021: biological counts/statistics/effects, expected-count adequacy and shared contingency kernels are implemented and verified. '
    'The360-test combined suite includes earlier tests; it is not360new tests. Seven historical native results, seven biological results and seven changed-epsilon results replay exactly without I/O. '
    'Future count-v2 identities distinguish actual group assignments; historical results remain unchanged. Root inspected complete math sources, execution receipts,35saved artifact hashes and the collision fix. '
    'Association extraction and full provider/library/episode integration are still unfinished.')
msa = rows['C-L204-MSA']
msa['native_parser'] = 'dna_protein_frequency_tables_and_full_mauve1_xmfa_reader_verified'
msa['metadata_extractor'] = 'xmfa_explicit_file_entry_invocation_source_binding_verified_provider_byte_authentication_and_general_associations_unfinished'
msa['numerical_verification'] = 'prior_msa_pure_checks_plus218_xmfa_parser_and39_source_checks_10_no_io_source_replays_full_provider_pending'
msa['note'] += (' Update021: full Mauve1 XMFA reader and detached validator pass218tests; source matching and saved relationship validation pass39tests,257combined. '
    'Two actual saved-validator defects involving contradictory Entry/Format metadata were reproduced and fixed; the original37-pass/2-fail review is preserved. '
    'Ten complete source binding examples replay exactly with file/network/subprocess/parser access disabled. Combined native source lengths are50/41/49. '
    'Invocation metadata in these examples is explicitly supplied fixture evidence, not live task proof. Provider byte authentication and full sheet/component assembly remain unfinished; separate XMFA coordinate/calculator work is in progress. '
    'Full first-block and multiblock distinctions remain intact; no complete MSA resource binding or episode return is claimed.')
for identity in ('C-L204-MSA', 'C-L205-MetaCATS'):
    rows[identity]['evidence_ids'].append(evidence_id)
    binding = next(row for row in work['resource_bindings'] if row['id'] == identity + '::api')
    binding['evidence_ids'] = deepcopy(rows[identity]['evidence_ids'])
work['verification_evidence'].append(evidence)
assert len(work['rows']) == len(old['rows']) == 308
assert len(work['resource_bindings']) == len(old['resource_bindings']) == 288
assert work['complete_scientific_tools_claimed'] == old['complete_scientific_tools_claimed'] == 0
changes = []
for group in ('rows', 'resource_bindings'):
    original = {row['id']: row for row in old[group]}
    assert set(original) == {row['id'] for row in work[group]}
    changes.extend({'group': group, 'id': row['id'], 'before': original[row['id']], 'after': deepcopy(row)}
                   for row in work[group] if row != original[row['id']])
updated = (json.dumps(work, indent=2) + '\n').encode()
update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before, 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'previous_goal_turn_classification': 'progress: completed and reviewed biological math/XMFA parsing/source association, fixed two actual saved-validator defects, and froze exact provider boundaries with fresh parallel coders.',
    'intervening_user_question_turn_classification': 'no progress: rechecked and explained the already-fixed action-order binding bug; no implementation edit.',
    'current_continuation_progress': 'Revalidated terminal receipts against current source and saved examples; updated the unchanged fixed scope to distinguish verified pure components from unfinished integration; continuing MSA source-byte authentication.',
    'changes': changes, 'added_evidence': [evidence], 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_021.json').open('x') as stream:
    json.dump(update, stream, indent=2)
    stream.write('\n')
status_path.write_bytes(updated)
print(json.dumps({'checkpoint': 21, 'changes': len(changes), 'scope_rows': 308,
                  'resource_bindings': 288, 'new_status_sha256': update['new_status_sha256']}))
