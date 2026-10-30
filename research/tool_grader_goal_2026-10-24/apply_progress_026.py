"""Record the closed run, corrected saved return/presentation and replay defect."""
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
assert before == 'f077fe26d4ffc7f3971e911d06eae1f34c9386df7f57d1e16c00a8dbca483464'
assert not (HERE / 'PROGRESS_UPDATE_026.json').exists()
work = json.loads(raw)
old = deepcopy(work)


def read(name):
    return json.loads((ROOT / name).read_text())


def hashed(name):
    return {'path': name, 'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}


flow = 'verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/'
prompt = 'verification/tool_graders_scientific_result_presentation_2026-10-25/'
terminal = read(flow + 'RUN_TERMINAL_023.json')
assert terminal['pytest_exit_code'] == 1 and terminal['changed_original_paths'] == {}
reader = read(flow + 'wired-saved-reader-027.json')
assert reader['status'] == 'wired_reads_equal_original_frozen_facts'
assert reader['counts_before'] == reader['counts_after']
assert reader['original_files_before'] == reader['original_files_after']
assert read(flow + 'source-guard-028.json')['status'] == 'all_guard_checks_passed'
assert read(flow + 'recorded-prompt-030.json')['original_run_unchanged']
suite = ET.parse(ROOT / prompt / 'tests-002.xml').getroot()
assert sum(int(s.get('tests', 0)) for s in suite.iter('testsuite')) == 24
assert all(int(s.get(k, 0)) == 0 for s in suite.iter('testsuite') for k in ('failures', 'errors', 'skipped'))
assert len(read(prompt + 'RETAINED_CONTEXT_002.json')['checked']) == 6

alignment_id = 'ALIGNMENT-SAVED-RETURN-PRESENTATION-026'
alignment = {'id': alignment_id, 'kind': 'actual_closed_workflow_saved_read_and_presentation_correction',
    'summary': 'Workflow009 closed all five MSA episodes with25actions/25observations/26model calls, then failed its fixture source-set guard before final test bodies. All349original paths were unchanged;15new paths caused the guard failure. Wired newest-result reading now performs one full publication authentication per own read and preserves exact original numerical facts at both parent boundaries. Prompt correction passed24focused tests and rerendered all six affected contexts; independent verification covered all nine contexts. The source guard now protects actually used modules/assets and records unrelated additions separately.',
    'qualification': 'Controlled loopback native artifacts and scripted choices; no live BV-BRC deployment or configured-model scientific investigation. The full three-case Workflow suite has not passed. New full execution waits for the actual shared native-validation dependency repair. Runtime counts, original run files, original forecasts and stored typed forms are unchanged.',
    'filled_examples': {'member_count': 4, 'cell_count': 28, 'gap_numerator': 6,
        'gap_denominator': 28, 'entropy_bits': 0.9182958340544896, 'native_score': 92,
        'native_score_unit': 'hundredths_of_bit'},
    'reports': [hashed(name) for name in (flow + 'RUN_TERMINAL_023.json',
        flow + 'wired-saved-reader-027.json', flow + 'source-guard-028.json',
        flow + 'recorded-prompt-030.json', flow + 'WIRED_READER_AND_SOURCE_GUARD_029.md',
        prompt + 'HANDOFF_003.md', prompt + 'tests-002.xml', prompt + 'RETAINED_CONTEXT_002.json',
        prompt + 'ATTEMPT_001.json')]}
genome_id = 'GENOME-ALIGNMENT-SHEET-REPLAY-DEFECT-026'
genome = {'id': genome_id, 'kind': 'implemented_ordered_numerical_sheet_and_verified_saved_replay_defect',
    'summary': 'D delivered all seven calculation families, complete ordered request outcomes and numerical sheets; its owned suite reports117passes. E and F actual consumers exposed additional scientific arithmetic hidden inside native validation: unions, lengths, multiplicity, complements, ratios, count aggregation and entropy. Strict saved projection is therefore not verified. A precise separate structural-validation correction is recorded; full producer numerical validation must remain.',
    'qualification': 'D117tests used retained native bytes and explicitly synthetic custody/mapping witnesses. Their public-entry-point replay barrier did not catch the internal arithmetic. E/F implementation and shared host/library/episode integration remain unfinished; no complete scientific tool or live service is claimed.',
    'filled_examples': {'v4_native_coverage': [690, 693], 'backbone_k2_unions': [50,49,19],
        'backbone_k3_unions': [18,18,19], 'bbcols_union': 52, 'xmfa_identity': [40,48]},
    'reports': [hashed(name) for name in (
        'verification/tool_graders_bvbrc_genome_alignment_sheet_2026-10-25/HANDOFF.md',
        'verification/tool_graders_bvbrc_genome_alignment_sheet_2026-10-25/pytest_final_007.xml',
        'verification/tool_graders_bvbrc_genome_alignment_sheet_2026-10-25/SOURCE_HASHES_FINAL.json',
        'verification/tool_graders_bvbrc_genome_alignment_bundle_2026-10-25/REPLAY_UNION_BARRIER_001.txt',
        'verification/tool_graders_bvbrc_genome_alignment_bundle_2026-10-25/REPLAY_ARITHMETIC_TRACE_002.json',
        'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/011_RETURN_IMPLEMENTATION.md',
        'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/BUNDLE_NATIVE_EDGE_CASES_012.md',
        'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/SAVED_VALIDATION_BOUNDARY_013.md')]}
for evidence in (alignment, genome):
    assert evidence['id'] not in {r['id'] for r in work['verification_evidence']}
    work['verification_evidence'].append(evidence)
for row in work['rows']:
    if row['id'] in ('C-L204-MSA', 'C-L205-MetaCATS'):
        row['integration_verification'] = 'closed_controlled_MSA_run_final_assertions_not_run_saved_reader_and_prompt_verified_full_suite_pending'
        row['evidence_ids'].append(alignment_id)
        row['note'] += ' Update026:Workflow009 is terminal, not running. Its MSA episode tree closed but the fixture failed before final assertions; the whole-suite completion claim remains unproved. One-authentication saved reading and presentation correction are verified on immutable original records. The next full run waits for shared native validation repair, which changes its actual implementation pin.'
    if row['id'] == 'C-L202-GenomeAlignment':
        row.update(overall='ordered_numerical_sheet_implemented_strict_saved_replay_and_host_integration_unfinished',
            numerical_sheet='D_v2_sheet_seven_families_and_stable_missing_request_outcomes_implemented',
            deterministic_calculator='seven_native_dispatch_families_and_explicit_saved_data_recalculation_implemented',
            numerical_verification='D_reports117_passing_checks_E_F_reproduce_internal_arithmetic_on_saved_read',
            integration_verification='E_F_components_under_verification_strict_saved_replay_defect_host_episode_path_unfinished')
        row['evidence_ids'].append(genome_id)
        row['note'] += ' Update026:D delivered numerical sheets and seven-family calculation dispatch with117reported checks. Strict E/F replay exposed scientific arithmetic inside native validators, so prior replay checks were insufficient. Separate structure-only validation is explicitly scoped; full numerical producer checks remain. Native version/symbol cases now have additive exact contracts; F original-publication return custody is being implemented. Root host/tool-library wiring and full Workflow/live verification remain unfinished.'
for row in work['resource_bindings']:
    if row['id'] in ('C-L204-MSA::api', 'C-L205-MetaCATS::api'):
        row['integration_verification'] = 'controlled_MSA_closed_final_assertions_not_run_saved_reader_prompt_verified_full_suite_pending'
        row['evidence_ids'].append(alignment_id)
    if row['id'] == 'C-L202-GenomeAlignment::api':
        row['integration_verification'] = 'D_sheet_E_F_components_strict_replay_defect_actual_host_episode_path_unfinished'
        row['evidence_ids'].append(genome_id)
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
    'previous_intervening_question_turn': 'no implementation progress; answered binding-vs-method_loop from current source and retained terminal evidence',
    'current_continuation_progress': 'Corrected production scientific result presentation, passed24checks and retained-context reproduction; verified wired saved reads and source guard; accepted fresh F implementation and explicit shared numerical-validation repair after real E/F failure evidence.',
    'changes': changes, 'added_evidence': [alignment, genome], 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_026.json').open('x') as stream:
    json.dump(record, stream, indent=2); stream.write('\n')
path.write_bytes(updated)
print(json.dumps({'checkpoint':26,'changed_rows_and_bindings':len(changes),
    'scope_rows':308,'resource_bindings':288,'status_sha256':record['new_status_sha256']}))
