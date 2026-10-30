"""Record verified alignment providers and host bindings; retain unfinished scope."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE/'WORK_STATUS.json'
raw = path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == '9d3a82e2ff5c783fa61abcabc86b001e3f4af6624fff40c77f6d11ccc23b205f'
assert not (HERE/'PROGRESS_UPDATE_022.json').exists()
work = json.loads(raw)
old = deepcopy(work)
prefix = 'verification/tool_graders_bvbrc_'


def read(suffix, filename):
    return json.loads((ROOT/(prefix+suffix+'_2026-10-25')/filename).read_text())


def hashed(relative):
    location = ROOT/relative
    return {'path': relative, 'sha256': hashlib.sha256(location.read_bytes()).hexdigest()}


review = read('msa_metacats_implementation', 'ROOT_ACCEPTED_BINDINGS_031.json')
assert len(review['checked_records']) == 814
assert review['unique_path_count'] == 695 and not review['problems']
for record in review['checked_records']:
    actual = (ROOT/record['path']).read_bytes()
    assert hashlib.sha256(actual).hexdigest() == record['sha256'], record['path']
    if 'byte_count' in record:
        assert len(actual) == record['byte_count']

returns = read('alignment_returns', 'TEST_003.json')
assert returns['returncode'] == 0 and returns['source_unchanged']
assert returns['counts'] == {'tests': 396, 'errors': 0, 'failures': 0, 'skipped': 0}
for source, digest in returns['source_after'].items():
    assert hashed(source)['sha256'] == digest
suite = ET.parse(ROOT/returns['junit']).getroot().find('testsuite')
assert len(suite.findall('testcase')) == 396
assert all(int(suite.attrib[k]) == 0 for k in ('errors', 'failures', 'skipped'))

evidence_id = 'MSA-METACATS-PROVIDERS-SELECTED-RETURNS-022'
reports = {
    'msa_provider': ['FROZEN_HANDOFF_017.json', 'HANDOFF_017.md', 'DEPENDENCY_TEST_015.json'],
    'metacats_provider': ['HANDOFF_001.md', 'SOURCE_HASHES_FINAL_001.json', 'TEST_RESULTS_001.json', 'FINAL_REPLAY_003.json'],
    'msa_source': ['SOURCE_HANDOFF_005.md', 'SOURCE_INPUT_TEST_003.json', 'SOURCE_EXAMPLE_REPLAY_004.json'],
    'associations': ['HANDOFF_001.md', 'SOURCE_HASHES_AFTER_FINAL_TEST_009.json', 'TEST_FINAL_REGRESSION_008.txt'],
    'xmfa': ['HANDOFF.md', 'FROZEN_HANDOFF.json'],
    'bundle': ['HANDOFF_016.md', 'FROZEN_HANDOFF_016.json', 'EXAMPLES_015/RECEIPT.json'],
    'projection': ['HANDOFF_018.md', 'HASHES_019.json', 'SAVED_REPLAY_012.json', 'WORKED_EXAMPLES_017.json'],
    'tool_info': ['HANDOFF_001.md', 'TEST_003.json'],
    'returns': ['HANDOFF_001.md', 'TEST_003.json'],
    'implementation': ['ROOT_ACCEPTED_PROVIDERS_029.json', 'ROOT_ACCEPTED_BINDINGS_031.json', 'TOOL_SCHEMA_REUSE_030.md'],
}
directories = {'msa_provider': 'msa_sheet', 'metacats_provider': 'metacats_provider',
    'msa_source': 'msa_provider', 'associations': 'alignment_associations',
    'xmfa': 'xmfa_calculators', 'bundle': 'alignment_bundle',
    'projection': 'alignment_projection', 'tool_info': 'alignment_tool_info',
    'returns': 'alignment_returns', 'implementation': 'msa_metacats_implementation'}
evidence = {
    'id': evidence_id,
    'kind': 'verified_supplied_data_scientific_providers_and_host_return_binding',
    'summary': 'Complete numerical providers, source-byte authentication, metadata associations, bundle resolution and selected saved-fact projection are implemented for MSA/MetaCATS. Five MSA and three MetaCATS information entries reach configured API commissioning. The stable root suite passed396 checks, including40 alignment-return and119 tool-information checks. Provider examples preserve native measurements separately from recalculation; no-I/O saved replay is verified.',
    'qualification': 'Counts from the separate provider/dependency suites overlap and are not added as new tests. The composed Workflow test is running but has not passed at this checkpoint. No new live BV-BRC job or deployed scientific version is verified. Prealigned work has a results-only route; GenBank/DNAstar source extraction, actual first-block AFA/FastTree output and original whole-genome provenance remain qualified gaps. No complete scientific tool, W05 or literature work is claimed.',
    'reports': [hashed(prefix+directories[group]+'_2026-10-25/'+name)
                for group, names in reports.items() for name in names],
}
assert evidence_id not in {row['id'] for row in work['verification_evidence']}
rows = {row['id']: row for row in work['rows']}
msa, meta = rows['C-L204-MSA'], rows['C-L205-MetaCATS']
for row in (msa, meta):
    row.update(
        overall='supplied_data_grading_and_host_return_binding_verified_full_workflow_and_live_resource_unfinished',
        numerical_sheet='full_native_documents_metadata_associations_and_explicit_numerical_components_installed_and_verified',
        production_result_binding='configured_api_bundle_publication_saved_content_authentication_and_fourteen_typed_fact_families_wired_and_tested',
        integration_verification='396_stable_host_library_communication_checks_passed_complete_composed_Workflow_still_running')
    row['evidence_ids'].append(evidence_id)
msa.update(
    tool_information='five_MSA_operation_variants_with_name_description_resources_instructions_and_actual_contracts_verified',
    invocation_contract='ordinary_segment_concatenated_mauve_API_commission_routes_plus_prealigned_results_only_verified',
    native_parser='retained_DNA_protein_AFA_frequency_consensus_and_full_Mauve_XMFA_formats_verified',
    metadata_extractor='original_occurrences_reference_function_taxon_tree_and_verified_FASTA_raw_XMFA_source_bindings_implemented',
    deterministic_calculator='explicit_entropy_reference_difference_coverage_function_tree_and_full_XMFA_measurements_installed_and_verified',
    numerical_verification='148_provider_checks_in_845_combined_plus9_subtests_37_full_examples_source_verifier59_in316_XMFA125_in382_projection111_shared_host396')
msa['note'] += (
    ' Update022: the source-byte verifier, associations, full XMFA coordinates/calculators, full MSA sheet/provider, bundle resolver, saved projection, configured tool information and host return binding are now implemented. '
    'The148 MSA provider checks are included in845 combined checks plus9 subtests; the59 source-byte checks are included in316, and125 new XMFA coordinate/calculator checks in382. These totals overlap other reports and are not summed. '
    'Thirty-seven MSA saved examples retain95 nonnull numerical records and changed-parameter cases. Native DNA scores92/81 remain separate from entropies0.9182958340544896/0.8112781244591328bits. '
    'Full six-block XMFA retains39 identities plus7 substitutions over46 canonical comparisons; source lengths50/41/49, represented unions50/41/49, multi-member unions48/0/47 and cooccupied unions46/0/46 remain distinct. '
    'The joint final bundle/projection/tool-info suite passed279 with7 earlier-passing native cases deselected; the earlier complete run passed268. Saved projection passed111 checks and21 complete no-I/O examples containing599 selected fields. '
    'Root verified814 manifest records/695 unique current paths and396 stable host/library/communication checks. Complete composed Workflow verification remains running; no live BV-BRC custody is claimed. '
    'GenBank/DNAstar source extraction, actual producer first-block AFA/FastTree observations and original whole-genome provenance remain explicit gaps; the staged FASTA/XMFA route and literal metrics do not erase them.')
meta.update(
    tool_information='three_MetaCATS_files_groups_auto_variants_with_name_description_resources_instructions_and_actual_contracts_verified',
    invocation_contract='configured_files_groups_auto_API_commission_and_result_selector_contracts_verified',
    native_parser='five_native_table_formats_original_FASTA_and_full_native_statistical_tokens_preserved_and_verified',
    metadata_extractor='original_member_occurrence_category_group_and_explicit_fetched_membership_associations_verified',
    deterministic_calculator='separate_native_biological_counts_statistics_effects_expected_adequacy_and_explicit_multiplicity_components_verified',
    numerical_verification='66_distinct_provider_checks_across65_plus1_runs_432_dependency_checks_21_complete_saved_examples_projection111_shared_host396')
meta['note'] += (
    ' Update022: full MetaCATS sheet/provider, original group/category associations, closed calculation dependencies, explicit family denominators, bundle resolution, selected projection and host returns are implemented. '
    'The final provider checks comprise65 in one run and1 additional category check;432 dependency checks are separate and overlap other reports. Twenty-one complete examples retain84 native input files;7 ordinary and7 changed-epsilon saved calculations replay without I/O/native execution. '
    'The two-group example retains counts[[6,0],[0,6]], chi-square8.330556481172943, df1 and p0.0038983714243371837; native p remains a separate recorded measurement. '
    'For a three-group pair, native df4/p0.017381025135296442 and biological df2/p0.00248371298657324 are separately named. Underflow preserves null mathematical p with finite log-p rather than false zero; native raw p1 remains separate. '
    'Library information exposes files/groups/auto with real API contracts. Auto/group provenance is checked by the supplied-data host boundary, not inferred by the pure association extractor. '
    'The stable396-check root suite includes40 alignment-return and119 tool-information checks plus237 shared/existing return checks. Complete Workflow and live-resource verification remain unfinished; mathematical/provenance qualifications are retained.')
for identity in ('C-L204-MSA', 'C-L205-MetaCATS'):
    binding = next(row for row in work['resource_bindings'] if row['id'] == identity+'::api')
    for field in ('invocation_contract', 'production_result_binding', 'integration_verification'):
        binding[field] = rows[identity][field]
    binding['evidence_ids'] = deepcopy(rows[identity]['evidence_ids'])
    binding['prerequisites_present'] = 'explicitly_configured_API_resource_and_scientific_adapter_pin_required_remote_environment_unverified'
    binding['native_format_observed'] = ('retained_native_MSA_and_progressiveMauve_outputs_no_live_BV_BRC_task_custody'
        if identity == 'C-L204-MSA' else 'seven_retained_native_MetaCATS_cases_no_live_BV_BRC_task_custody')
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
updated = (json.dumps(work, indent=2)+'\n').encode()
record = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before, 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'previous_goal_turn_classification': 'progress: repaired outdated forwarding fixtures after rechecking the action-ordering binding fix; all6 focused checks passed. No method_loop change.',
    'current_continuation_progress': 'Accepted the completed pure provider/resolver/projection work with current hashes, verified396 stable host/library/communication checks, repaired measured repeated schema construction with33 checks, and resumed the complete Workflow run. New GenomeAlignment/GenomeComparison contract research is independent and not counted as implementation.',
    'changes': changes, 'added_evidence': [evidence], 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': 0}
with (HERE/'PROGRESS_UPDATE_022.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
path.write_bytes(updated)
print(json.dumps({'checkpoint':22,'changed_rows_and_bindings':len(changes),
    'scope_rows':308,'resource_bindings':288,'new_status_sha256':record['new_status_sha256']}))
