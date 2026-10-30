"""Apply the reviewed local Infernal progress evidence; never execute scientific work.

Prepared by workload 233, not executed by that workload. Root applies this only
after reviewing the pinned 226/231 evidence. Existing accounting and evidence
must match their preparation hashes before any write occurs.
"""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
RECORD = HERE / 'PROGRESS_UPDATE_051.json'
AUDIT = ROOT / 'verification/tool_graders_infernal_accounting_2026-10-26_233/EVIDENCE_AUDIT_001.json'
AUDIT_SHA256 = '1ddfc6288770382d99688d81d0536b706def5866163d34de9f5b5631c68f621b'
BEFORE_SHA256 = '8e954c650412201a085dbbddeca09a7316f101601336aed84fe96ee0171c4121'
AUTHORITY_SHA256 = '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
TOOL_IDS = ('A-L067-cmsearch', 'A-L067-cmscan', 'A-L067-cmalign')
LOCAL_IDS = tuple(name + '::local' for name in TOOL_IDS)


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def resolved(name):
    value = Path(name)
    return value if value.is_absolute() else ROOT / value


def numerical_progress_rows(work):
    # Reproduce the carried-forward progress tally, not a completion criterion.
    # Operational-only rows and the two broad partly implemented service wrappers
    # were not part of the prior 68. Source/reported evidence qualifications stay
    # in their existing rows; no earlier row is promoted by this calculation.
    excluded = {
        'not_assessed', 'not_applicable_excluded_or_not_required',
        'typed_native_operational_quantities_no_independent_annotation_confidence',
        'MinHash_and_Homology_native_quantities_and_components_other_applications_unfinished',
    }
    return {row['id'] for row in work['rows'] if row['numerical_sheet'] not in excluded}


def main():
    check(not RECORD.exists(), 'checkpoint051_already_exists')
    check(sha(AUDIT) == AUDIT_SHA256, 'preparation_audit_hash_mismatch')
    audit = read(AUDIT)
    check(audit['schema'] == 'infernal_accounting_preparation_evidence_v1', 'wrong_preparation_schema')
    check(audit['authority_sha256'] == AUTHORITY_SHA256, 'wrong_authority')
    mismatches = []
    for name, expected in audit['file_sha256'].items():
        path = resolved(name)
        if not path.is_file() or sha(path) != expected:
            mismatches.append(name)
    check(not mismatches, 'source_or_evidence_hash_mismatch: ' + ', '.join(mismatches))
    raw = STATUS.read_bytes()
    check(hashlib.sha256(raw).hexdigest() == BEFORE_SHA256 == audit['previous_status_sha256'], 'checkpoint050_status_mismatch')
    original = json.loads(raw)
    work = deepcopy(original)
    scope_path = HERE / work['scope_file']
    scope, scope_hash = read(scope_path), sha(scope_path)
    aliases = read(HERE / 'SOURCE_ALIASES.json')
    check(work['authority_sha256'] == scope['authority']['sha256'] == aliases['authority_sha256'] == AUTHORITY_SHA256, 'accounting_authority_mismatch')
    check(len(aliases['rows']) == 622, 'alias_scope_changed')
    check(work['complete_scientific_tools_claimed'] == 0, 'unexpected_whole_tool_completion_claim')
    check(work['verified_bound_local_tool_mode_rows'] == 22, 'local_progress_tally_changed')
    check(audit['episode_unique_passing_nodes'] == 42 and audit['frame_unique_passing_nodes'] == 64, 'final_verification_not_ready')
    check(audit['frame_new_passing_nodes'] == 16 and audit['frame_shared_passing_nodes'] == 48, 'frame_counts_changed')
    check(len(audit['unresolved_existing_shared_failures']) == 4, 'baseline_qualification_missing')
    check(audit['checked_current_226_source_hashes'] == 55 and audit['checked_current_231_production_hashes'] == 9, 'final_source_audit_missing')

    def reports(*names):
        result = []
        for name in names:
            check(name in audit['file_sha256'], 'unpinned_report: ' + name)
            result.append(dict(path=name, sha256=audit['file_sha256'][name]))
        return result

    prefix = 'verification/tool_graders_infernal_'
    pure = dict(
        id='INFERNAL-NATIVE-NUMERICAL-051',
        kind='separate_native_sheets_readers_calculators_and_local_artifact_publication_verified',
        summary='cmsearch and cmscan retain native hit and sequence/strand span sheets; cmalign retains '
            'sequence, column and pair quantities with separate calculators. Complete native artifacts, '
            'actual operand identities and full numerical results remain retained. Search54 cases passed '
            'again inside root228 shared151. Cmalign has54 dedicated passes at its earlier checkpoint '
            'and a final196-case five-module receipt with current source hashes. Native producer43, '
            'capture99 distinct (96+4 with1 overlap), worker43 and publication27 pass; its4 follow-up '
            'cases overlap those27. Producer222 executed three successes and one real native failure. '
            'Saved-sheet recalculation and custody replay require no scientific rerun or acquisition.',
        qualification='These counts describe different, sometimes overlapping verification layers and '
            'are not summed. No standalone55-pass cmalign receipt exists. The original219 search-reader '
            'hash predates the --oskip completeness correction; root228 rechecked all54 cases on the '
            'current reader. Search spans are not residue correspondence, native posterior bins are '
            'intervals, local rendered gaps are not proven deletions, and population rows invent no '
            'single subject. Capture completeness does not turn native failure into scientific success. '
            'The retained native examples are small synthetic-input local jobs; API/HPC, Rfam and '
            'the seven separate Infernal preparation utilities are not completed by these reports.',
        numerical_examples=[
            dict(program='cmsearch', family='search_hit', bitscore=71.4, evalue=3.6e-22,
                 model_span=[72, 72], sequence_span=[72, 72]),
            dict(program='cmscan', family='search_hit', bitscore=71.4, evalue=1e-22),
            dict(program='cmsearch', family='search_sequence', hit_count=1, union_numerator=72, union_denominator=72),
            dict(program='cmalign', family='alignment_sequence', native_bit_score=60.03,
                 native_avg_pp=1.0, posterior_mean_bounds=[0.95, 1.0], deleted_model_positions=None),
            dict(program='cmalign', family='alignment_column', occupancy_numerator=10, occupancy_denominator=10,
                 subject_ref=None, observation_ref=None),
            dict(program='cmalign', family='alignment_pair', canonical_pairs=10, unambiguous_pair_denominator=10,
                 subject_ref=None, observation_ref=None),
        ],
        reports=reports(
            prefix+'search_2026-10-26_219/HANDOFF.md',
            prefix+'search_2026-10-26_219/EXAMPLE_RESULTS.json',
            prefix+'alignment_2026-10-26_220/HANDOFF_001.md',
            prefix+'alignment_2026-10-26_220/VERIFICATION_RECEIPT.json',
            prefix+'alignment_2026-10-26_220/SAVED_RECALCULATION_PROOF.json',
            prefix+'native_execution_2026-10-26_222/TEST_RECEIPT_001.json',
            prefix+'native_execution_2026-10-26_222/REPORT_001.md',
            prefix+'acquisition_2026-10-26_223/VERIFICATION_001.md',
            prefix+'worker_2026-10-26_224/REPORT_001.md',
            prefix+'worker_2026-10-26_224/TEST_RECEIPT_004.json',
            prefix+'publication_2026-10-26_225/HANDOFF_001.md',
            prefix+'publication_2026-10-26_225/VERIFICATION_RECEIPT.json'))
    integration = dict(
        id='INFERNAL-LOCAL-EPISODE-051',
        kind='actual_selected_local_native_jobs_and_authenticated_typed_episode_communication_verified',
        summary='Configured four-field tool information and exact local request contracts reach launch '
            'and its local child, original native outputs, complete capture, five-family numerical '
            'publication and both actual typed receiving boundaries. Binding47, authenticated returns43 '
            'and42 unique episode test IDs have verified retained receipts. All55 final226 source hashes '
            'and the actual JUnit identities match. Its15 retained CASE records have equal selected-action '
            'and controller-observation counts. Successful result future expectations are exact zero; '
            'stable main-case launch/local archives retain final actual gains3/7 and one own action each '
            'with exact-zero future expectation. Native jobs total12 cmsearch,1 cmscan,2 cmalign across '
            'all retained226 runs, including the intentional nonzero cmalign attempt.',
        qualification='The42 passing identities are30 from stable run004,8 from qualified run006 and4 '
            'from stable run007; no single clean42-test run is claimed. Run004 exited1 on the real full '
            'observation leak and run005 reproduced it. Run006 had concurrent edits to four presentation '
            'modules; native capture/worker/publication/results/returns stayed unchanged. Binding47 '
            'changed only the unconsumed admission method as qualified in228/229. Shared151 had a '
            'concurrent native-results edit outside its consumed cases, and is not a frozen-all-source '
            'claim. Scientific choices, horizons and root credit are engineering fixtures. The root '
            'reference-only gain10 counts received observation references, not ten numerical returns, '
            'annotation support or W05. Partial fault closure uses a disclosed fixture estimate and '
            'never a fabricated completion proof. Generic role TASK/STEERING and selected resource '
            'instruction transfer remain unfinished, as for the existing HMMER rows. No live scientific '
            'model, API/HPC deployment, annotation-scoring or whole-tool completion is claimed.',
        reports=reports(
            prefix+'episode_2026-10-26_226/FINAL_VERIFICATION_001.json',
            prefix+'episode_2026-10-26_226/EVIDENCE_001.md',
            prefix+'episode_2026-10-26_226/passing-test-nodes.tsv',
            prefix+'returns_2026-10-26_227/VERIFICATION_001.json',
            prefix+'returns_2026-10-26_227/REPORT_001.md',
            prefix+'root_2026-10-26_228/shared_regression_001/receipt.json',
            prefix+'root_2026-10-26_228/BINDING_TEST_SOURCE_CHANGE_001.json',
            prefix+'binding_2026-10-26_229/REPORT_001.md',
            prefix+'binding_2026-10-26_229/SOURCE_QUALIFICATION_001.json'))
    presentation = dict(
        id='INFERNAL-REQUESTED-PRESENTATION-051',
        kind='receiver_projection_frames_provider_text_and_interrupted_decision_restore_verified',
        summary='The pure receiver projection22 cases pass. Final231 verifies64 unique passing identities '
            '(16 new receiving-boundary cases and48 shared), including two final restored-pending cases '
            'with the actual exchange schema and an actual prior-input history answer. Actual provider '
            'text and framed snapshots expose only requested typed quantities while full saved '
            'observations remain intact. The first retained request shows bitscore71.4; a later request '
            'adds E-value3.6e-22. Reference-only returns expose no numerical expansion. Explicit own '
            'outcomes and requested lookup replies survive. Restoration adds no action or observation.',
        qualification='The64 cases combine overlapping runs, not their pass-count sum. Four existing '
            'shared root-tool/history tests fail identically with Infernal projection and with the '
            'no-op baseline; actual JUnit failure attributes and saved tool/feedback sequences match. '
            'Those failures remain unresolved, with no root tool restoration or altered shared '
            'expectations. All9 current production and6 test/fixture/runner hashes match; each231 run '
            'had unchanged before/after sources. Root variants and pending-journal setup are synthetic; '
            'RPC responses are controlled. Restoration reaches a selected response, not action execution. '
            'This correction does not finish general TASK/STEERING work or establish model-driven '
            'scientific investigation, continuation mathematics, literature grading or W05.',
        reports=reports(
            prefix+'presentation_2026-10-26_230/CONTRACT_001.md',
            prefix+'presentation_2026-10-26_230/tests_001/verification-receipt.json',
            prefix+'presentation_2026-10-26_231/FINAL_EVIDENCE.json',
            prefix+'presentation_2026-10-26_231/HANDOFF.md',
            prefix+'presentation_2026-10-26_231/baseline_comparison.json'))
    evidence = [pure, integration, presentation]
    ids = [entry['id'] for entry in evidence]
    check(not set(ids) & {row['id'] for row in work['verification_evidence']}, 'duplicate_evidence_id')
    work['verification_evidence'].extend(evidence)
    note = (' Update051: Separate Infernal native sheets, readers, metadata joins and calculators; '
        'real small local launch/capture/publication and five typed result families now verified. '
        'Complete native/scientific artifacts remain retained; receivers obtain only their requested '
        'projection. Episode226 has42 unique passing nodes across qualified runs; presentation231 '
        'has64 unique passes and four unchanged baseline-reproduced shared failures. All actual '
        'CASE actions equal observations; validated practical/result future expectations become '
        'exact zero with final actual gains preserved. Choices and scientific credit are scripted '
        'engineering fixtures. General role TASK/STEERING and selected resource-instruction prompt '
        'work remain unfinished. No API/HPC binding, configured-model investigation, Rfam/preparation '
        'utility completion, W05, annotation-score or full-goal completion is claimed. See the three '
        'new evidence records for actual numerical examples, overlaps and source qualifications.')
    for row in work['rows']:
        if row['id'] not in TOOL_IDS:
            continue
        check(row['overall'] == 'not_assessed' and row['evidence_ids'] == [], 'infernal_row_changed_before_application')
        row.update(
            overall='local_numerical_episode_path_verified_prompt_work_remaining',
            source_presence='source_present',
            tool_information='configured_real_four_field_contracts_present',
            invocation_contract='explicit_bound_native_program_mode_software_resource_contract',
            numerical_sheet='verified_filled_native_examples',
            native_parser=('verified_Stockholm_sfile_ifile_optional_elfile_and_partial_invalid_siblings'
                if row['id'].endswith('cmalign') else 'verified_native_tblout_formats_roles_coordinates_and_partial_invalid_siblings'),
            metadata_extractor=('verified_actual_operand_identity_sequence_model_length_coordinate_and_inheritance_joins'
                if row['id'].endswith('cmalign') else 'verified_actual_operand_identity_sequence_model_length_and_coordinate_joins'),
            deterministic_calculator='verified_saved_sheet_recalculation_without_acquisition',
            production_result_binding='local_native_numerical_publication_and_typed_parent_admission_verified',
            numerical_verification=('54_dedicated_checkpoint_and_final196_overlapping_five_module_receipt_current_sources'
                if row['id'].endswith('cmalign') else '54_pure_search_cases_rechecked_in151_shared_suite_retained_native_examples'),
            integration_verification='42_unique_native_Workflow_nodes_64_presentation_nodes_qualified_shared_failures_preserved',
            live_resource_verification='actual_tiny_bounded_local_Infernal_1_1_5_jobs_and_saved_numerical_results',
            evidence_ids=ids.copy(), note=row['note'] + note)
    for row in work['resource_bindings']:
        if row['id'] not in LOCAL_IDS:
            continue
        check(row['invocation_contract'] == 'not_assessed' and row['evidence_ids'] == [], 'infernal_binding_changed_before_application')
        row.update(
            invocation_contract='explicit_pinned_native_program_mode_software_binding_verified',
            production_result_binding='complete_native_artifact_sheet_calculator_and_selected_typed_return_verified',
            integration_verification='actual_selected_local_job_shared_Workflow_typed_receivers_replay_and_projection_verified_with_recorded_qualifications',
            live_resource_verification='actual_tiny_native_Infernal_1_1_5_jobs_under20GiB_4GiB_no_wall',
            prerequisites_present='actual_pinned_native_executable_and_tiny_explicit_inputs',
            native_format_observed=('actual_complete_Stockholm_sfile_ifile_optional_elfile_retained_partial_native_failure'
                if row['id'].startswith('A-L067-cmalign') else 'actual_Infernal_1_1_5_tblout_formats_and_complete_native_streams'),
            evidence_ids=ids.copy())
    work['verified_bound_local_tool_mode_rows'] = 25

    changes = []
    for group, count, expected_ids in (('rows', 308, TOOL_IDS), ('resource_bindings', 288, LOCAL_IDS)):
        check(len(work[group]) == len(original[group]) == len(scope[group]) == count, 'fixed_row_count_changed')
        check([r['id'] for r in work[group]] == [r['id'] for r in original[group]] == [r['id'] for r in scope[group]], 'fixed_row_identities_changed')
        group_changes = [dict(group=group, id=before['id'], before=before, after=after)
            for before, after in zip(original[group], work[group]) if before != after]
        check({entry['id'] for entry in group_changes} == set(expected_ids), 'unexpected_row_change')
        changes.extend(group_changes)
    check(len(changes) == 6, 'expected_exactly_six_row_diffs')
    top = {key for key in original.keys() | work.keys() if original.get(key) != work.get(key)}
    check(top == {'rows', 'resource_bindings', 'verification_evidence', 'verified_bound_local_tool_mode_rows'}, 'unexpected_top_level_change')
    before_tally, after_tally = numerical_progress_rows(original), numerical_progress_rows(work)
    check(len(before_tally) == 68 and len(after_tally) == 71 and after_tally - before_tally == set(TOOL_IDS), 'numerical_progress_tally_changed_meaning')
    check(sha(scope_path) == scope_hash, 'scope_mutated')
    updated = (json.dumps(work, indent=2) + '\n').encode()
    record = dict(schema='tool_grader_progress_update_v1', date='2026-10-26',
        recorded_at=datetime.now(timezone.utc).isoformat(), author='root',
        previous_status_sha256=BEFORE_SHA256, new_status_sha256=hashlib.sha256(updated).hexdigest(),
        scope_sha256_unchanged=scope_hash, scope_changes=False, changes=changes, added_evidence=evidence,
        count_change={'verified_bound_local_tool_mode_rows': dict(before=22, after=25,
            meaning='Fixed required local-binding rows, not unique algorithms or all-goal completion')},
        numerical_grader_progress_tally=dict(before=68, after=71, added_row_ids=list(TOOL_IDS),
            meaning='Carried-forward implemented numerical-grader progress tally; no new completion definition, unique-algorithm count or promotion of earlier source/report-only qualifications'),
        preparation=dict(path=str(AUDIT.relative_to(ROOT)), sha256=AUDIT_SHA256),
        source_evidence_sha256=audit['file_sha256'],
        completed_work=['Separate native sheets, deterministic readers/metadata joins and calculators',
            'Real bounded local production execution, complete capture and numerical publication',
            'Five requested typed return families, authenticated receiving boundaries and saved replay',
            'Receiver projection, model frames, provider text and interrupted-decision restoration'],
        unfinished_work=['General role TASK/STEERING and selected resource-instruction prompt work',
            'Native Infernal API/HPC bindings and unverified native versions',
            'Separate Rfam batch-scanning row and seven Infernal preparation/inspection utility rows',
            'Four unchanged baseline-reproduced shared root-tool/history test failures',
            'Configured-model scientific investigation and full original-goal completion'],
        excluded_claims=['W05 or annotation-scoring implementation', 'Literature-grader implementation',
            'Reference-only receipt counts as numerical exposure or annotation support',
            'A single clean42-case episode run or a standalone55-case cmalign pass'],
        inventory_maintenance_counted_as_implementation_progress=False,
        accounting_executed_scientific_tools=False, accounting_executed_tests=False,
        specific_pending_NCBI_job_verification_included=False, complete_scientific_tools_claimed=0)
    # All comparisons and evidence reads precede the two authorized accounting writes.
    check(sha(STATUS) == BEFORE_SHA256, 'status_changed_during_preflight')
    with RECORD.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    STATUS.write_bytes(updated)
    print(json.dumps(dict(checkpoint=51, changed_tool_rows=list(TOOL_IDS), changed_local_bindings=list(LOCAL_IDS),
        numerical_grader_progress_tally=71, verified_bound_local_tool_mode_rows=25,
        complete_scientific_tools_claimed=0, unresolved_existing_shared_failures=4,
        status_sha256=record['new_status_sha256'])))


if __name__ == '__main__':
    main()
