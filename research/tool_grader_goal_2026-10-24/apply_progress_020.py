"""Record verified original-input parsing and explicitly unfinished next work."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
status_path = HERE/'WORK_STATUS.json'
raw = status_path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == '4d29d7cf1d7299a2da5be22ef75415c54b277efb75029d6a8ea96dc9e0fb0ce9'
assert not (HERE/'PROGRESS_UPDATE_020.json').exists()
work = json.loads(raw)
old = deepcopy(work)
input_dir = ROOT/'verification/tool_graders_bvbrc_metacats_input_2026-10-25'
implementation = ROOT/'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25'
workflow = ROOT/'verification/tool_graders_bvbrc_phylogeny_workflow_2026-10-25'


def hashed(path):
    return {'path':str(path.relative_to(ROOT)), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


tests = json.loads((input_dir/'INPUT_TEST_RESULT_002.json').read_text())
assert tests['returncode'] == 0 and tests['source_stable']
assert tests['source_before'] == tests['source_after']
for path, digest in tests['source_after'].items():
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
suite = ET.parse(input_dir/'input-and-format-tests-002.xml').getroot().find('testsuite')
# pytest's JUnit suite count includes nine subtests; its testcase nodes retain
# the 127 top-level tests. Preserve both, without counting 136 new test cases.
assert int(suite.attrib['tests']) == 136
assert len(suite.findall('testcase')) == 127
assert all(int(suite.attrib[key]) == 0 for key in ('failures','errors','skipped'))
examples = json.loads((input_dir/'INPUT_READER_VERIFICATION_003.json').read_text())
assert examples['tests_passed'] == 127 and examples['new_input_tests'] == 25
assert len(examples['examples']) == 8
for example in examples['examples']:
    assert example['no_io_parse_and_roundtrip_passed']
    assert hashed(ROOT/example['path'])['sha256'] == example['sha256']
collision = json.loads((implementation/'NATIVE_COUNT_IDENTITY_COLLISION_004.json').read_text())
assert collision['same_table_id'] and collision['different_counts']
phylogeny = json.loads((workflow/'VERIFICATION_RESULTS_001.json').read_text())
assert phylogeny['original_workflow_executions'] == 3
assert phylogeny['original_pytest_failed'] == 1
assert phylogeny['corrected_saved_numeric_check_passed']
assert not phylogeny['live_native_execution'] and not phylogeny['w05_verified']
for case in phylogeny['cases']:
    assert case['saved_replay_without_new_work'] and case['source_manifests_equal']
    assert case['counts']['runtime_actions'] == case['counts']['runtime_observations'] == 12
    assert case['measurements'] == {'cells':16,'gap_fraction':.125,'missing':[],'tips':4}

evidence_id = 'METACATS-ORIGINAL-INPUT-AND-NEXT-CONTRACTS-020'
evidence = {'id':evidence_id, 'kind':'production_input_parser_and_accepted_independent_contracts',
    'summary':'MetaCATS original FASTA parser preserves literal hash symbols and exact rows/locations; 25 new tests, 127 combined checks plus9subtests pass; eight complete saved examples roundtrip without I/O. Native count-identity collision is reproduced and assigned for correction. Biological math and full XMFA reader are separately scoped fresh coding workloads.',
    'qualification':'Parser checks do not prove provider assembly, tool-library or child-return wiring. Count-ID correction and biological/XMFA implementations are still under way at this checkpoint. No new service/aligner/HPC run, evidence-axis or W05 work.',
    'reports':[hashed(p) for p in [input_dir/'INPUT_READER_VERIFICATION_003.json',
        input_dir/'INPUT_TEST_RESULT_002.json', input_dir/'INITIAL_TEST_RESULT_001.json',
        implementation/'NATIVE_COUNT_IDENTITY_COLLISION_004.json',
        implementation/'METACATS_INPUT_READER_CONTRACT_005.md',
        implementation/'ACCEPTED_MATH_WORKLOAD_006.json',
        implementation/'MATH_CLARIFICATIONS_007.md',
        implementation/'ACCEPTED_XMFA_BOUNDARY_008.json',
        implementation/'XMFA_DIAGNOSTIC_CLARIFICATION_009.md',
        workflow/'REPORT_001.md', workflow/'VERIFICATION_RESULTS_001.json']]}
assert evidence_id not in {row['id'] for row in work['verification_evidence']}
rows = {row['id']:row for row in work['rows']}
meta = rows['C-L205-MetaCATS']
meta['native_parser'] = 'five_native_tables_plus_original_hash_preserving_fasta_reader_verified'
meta['metadata_extractor'] = 'original_rows_hash_symbols_metadata_and_matrix_tokens_preserved_group_association_still_unfinished'
meta['numerical_verification'] = 'prior212pure_checks_and317native_statistics_plus127input_format_checks_with9subtests_and8saved_input_examples'
meta['deterministic_calculator'] = 'native_statistics_installed_biological_path_and_confirmed_count_identity_collision_correction_in_progress'
meta['note'] += (' Update020: added separate original-input FASTA parser retaining # distinctly from -; '
    '25 new checks pass within127combined input/format tests plus9subtests. Seven native-component '
    'input examples and one synthetic hash/dash example roundtrip with I/O disabled. Initial five '
    'new fixture assertions confused one variable site with four input columns; originals inspected '
    'and test assertions corrected, failure/source retained, production parser unchanged. A separate '
    'native count-ID collision was reproduced: changed memberships yield [[6,0],[0,6]] versus '
    '[[3,3],[3,3]] under the same old identity. Future assignment-aware v2 IDs and independent '
    'biological math have exact accepted fresh-workload boundaries; they are not marked implemented '
    'or verified here. Full provider/library/episode integration remains unfinished.')
msa = rows['C-L204-MSA']
msa['note'] += (' Update020: full Mauve1 XMFA format/source/coordinate/statistical contracts accepted '
    'after retained native examination; a fresh coder owns only new reader/validator files. '
    'No XMFA implementation test or complete MSA binding is claimed at this checkpoint. '
    'First-block AFA remains explicitly distinct from full multi-block XMFA.')
for identity in ('C-L193-CodonTree','C-L194-GeneTree'):
    rows[identity]['note'] += (' Update020: final controlled Workflow report and machine-readable '
        'results received and inspected. They preserve the original GeneTree assertion failure '
        'and corrected saved-run result, all three closed runs, and synthetic transport/controlled '
        'scientific/root continuation plus zero credit projection. No new execution or additional '
        'live/W05 verification is inferred from final report publication.')
for identity in ('C-L193-CodonTree','C-L194-GeneTree','C-L204-MSA','C-L205-MetaCATS'):
    rows[identity]['evidence_ids'].append(evidence_id)
    binding = next(row for row in work['resource_bindings'] if row['id'] == identity+'::api')
    binding['evidence_ids'] = deepcopy(rows[identity]['evidence_ids'])
work['verification_evidence'].append(evidence)
assert len(work['rows']) == len(old['rows']) == 308
assert len(work['resource_bindings']) == len(old['resource_bindings']) == 288
assert work['complete_scientific_tools_claimed'] == old['complete_scientific_tools_claimed'] == 0
changes=[]
for group in ('rows','resource_bindings'):
    original={row['id']:row for row in old[group]}
    assert set(original)=={row['id'] for row in work[group]}
    changes.extend({'group':group,'id':row['id'],'before':original[row['id']],'after':deepcopy(row)}
        for row in work[group] if row!=original[row['id']])
updated=(json.dumps(work,indent=2)+'\n').encode()
update={'schema':'tool_grader_progress_update_v1','date':'2026-10-25',
    'recorded_at':datetime.now(timezone.utc).isoformat(),'author':'root',
    'previous_status_sha256':before,'new_status_sha256':hashlib.sha256(updated).hexdigest(),
    'previous_goal_turn_classification':'progress: checkpoint019 installed and verified nine new pure MSA/MetaCATS modules and recorded completed controlled Workflow evidence.',
    'intervening_user_question_turn_classification':'no progress: rechecked and explained the already-fixed API-binding action-order bug, with no implementation edits.',
    'current_continuation_progress':'Installed verified MetaCATS original-input parser; reproduced distinct count identity defect; froze exact independent math and XMFA coding contracts and assigned fresh workers; final phylogeny report inspected.',
    'changes':changes,'added_evidence':[evidence],'scope_changes':False,
    'specific_pending_NCBI_job_verification_included':False,'complete_scientific_tools_claimed':0}
with (HERE/'PROGRESS_UPDATE_020.json').open('x') as stream:
    json.dump(update,stream,indent=2);stream.write('\n')
status_path.write_bytes(updated)
print(json.dumps({'checkpoint':20,'changes':len(changes),'scope_rows':308,
    'resource_bindings':288,'new_status_sha256':update['new_status_sha256']}))
