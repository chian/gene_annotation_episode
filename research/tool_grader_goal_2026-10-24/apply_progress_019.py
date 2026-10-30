"""Record completed controlled Workflow and pure MSA/MetaCATS verification.

This checkpoint preserves every fixed scope/binding identity. Component checks
do not declare a full scientific tool or live resource complete.
"""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
status_path = HERE / 'WORK_STATUS.json'
raw = status_path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == '518253458eb05f99ca0a5c985e4a99db1a6405221c8e82fb5e7c17ea099a9fd1'
assert not (HERE / 'PROGRESS_UPDATE_019.json').exists()
work = json.loads(raw)
old = deepcopy(work)
pure = ROOT / 'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25'
workflow = ROOT / 'verification/tool_graders_bvbrc_phylogeny_workflow_2026-10-25'
host = ROOT / 'verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24'
msa = ROOT / 'verification/tool_graders_bvbrc_msa_pure_2026-10-25'
meta = ROOT / 'verification/tool_graders_bvbrc_metacats_formats_2026-10-25'
native = ROOT / 'verification/tool_graders_bvbrc_metacats_native_execution_2026-10-25'


def hashed(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def suite(path, expected):
    s = ET.parse(path).getroot().find('testsuite')
    counts = {key: int(s.attrib[key]) for key in ('tests', 'errors', 'failures', 'skipped')}
    assert counts == {'tests': expected, 'errors': 0, 'failures': 0, 'skipped': 0}
    return {**hashed(path), 'counts': counts, 'seconds': float(s.attrib['time'])}


host_check = suite(host / 'host-integration-tests-002.xml', 5)
pure_check = suite(pure / 'combined-pure-001.xml', 212)
combined = json.loads((pure / 'COMBINED_VERIFICATION_001.json').read_text())
assert combined['returncode'] == 0 and combined['source_unchanged']
source_before = json.loads((pure / 'COMBINED_SOURCE_BEFORE_001.json').read_text())
source_after = json.loads((pure / 'COMBINED_SOURCE_AFTER_001.json').read_text())
assert source_before == source_after
for item in source_after:
    assert hashed(ROOT / item['path'])['sha256'] == item['sha256']
saved = json.loads((pure / 'SAVED_REPLAY_FINAL_003.json').read_text())
assert saved['all_passed'] and len(saved['cases']) == 7
for item in saved['source_files']:
    assert hashlib.sha256((ROOT / item['raw_artifact_ref']).read_bytes()).hexdigest() == item['sha256']
correction = json.loads((pure / 'EXAMPLES_002/CORRECTION_002.json').read_text())
assert correction['numerical_statistics_unchanged'] and correction['saved_no_io_replay_equal']
examples = json.loads((pure / 'EXAMPLES_001/manifest.json').read_text())
assert sum(item['native_variable_tests_compared'] for item in examples['cases']) == 317
assert len(json.loads((native / 'NATIVE_RUNS_001.json').read_text())) == 7

mode_checks = []
for mode in ('gene_tree', 'concatenated_sequence_loci', 'core_genome_codon_protein'):
    runs = list((workflow / 'runs').glob(mode + '-*'))
    assert len(runs) == 1
    run = runs[0]
    provenance = json.loads((run / 'PROVENANCE.json').read_text())
    replay = json.loads((run / 'saved-replay-verification.json').read_text())
    assert provenance['status'] == 'workflow_closed'
    assert provenance['returned_measurements'] == {'cells': 16, 'gap_fraction': .125, 'tips': 4}
    assert replay['counts_before'] == replay['counts_after']
    assert replay['counts_after']['runtime_actions'] == replay['counts_after']['runtime_observations'] == 12
    assert replay['native_calls_added'] == 0 and replay['typed_read_and_admission_without_calculation']
    assert replay['saved_recalculation_equal'] and replay['changed_pair_recalculation_without_parsing']
    initial = json.loads((run / 'SOURCE_PROVENANCE.json').read_text())
    final = json.loads((run / 'SOURCE_PROVENANCE_AFTER.json').read_text())
    assert initial == final
    mode_checks.append({'mode': mode, 'run_directory': str(run.relative_to(ROOT)),
        'returned_measurements': provenance['returned_measurements'],
        'counts': replay['counts_after'], 'replay': hashed(run / 'saved-replay-verification.json'),
        'provenance': hashed(run / 'PROVENANCE.json'), 'source_before_after_equal': True,
        'test_result': '3 passed; original wrong count-denominator assertion failed; separate corrected retained check passed'
            if mode == 'gene_tree' else '4 passed',
        'fixture_overrides': ['controlled decisions', 'controlled scientific/root continuation',
            'scientific/root project_credit=lambda *_: 0', 'synthetic NativeClient transport']})
gene = next((workflow / 'runs').glob('gene_tree-*'))
corrected_gene = json.loads((gene / 'corrected-numeric-retained-verification.json').read_text())
assert corrected_gene

receipt = {
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'completed_host_checks': host_check, 'controlled_workflow_modes': mode_checks,
    'corrected_gene_numeric_check': hashed(gene / 'corrected-numeric-retained-verification.json'),
    'combined_pure_check': pure_check,
    'pure_source_before_after_equal_and_still_current': True,
    'pure_tests_by_module': dict(Counter(case.attrib['classname'] for case in
        ET.parse(pure / 'combined-pure-001.xml').getroot().find('testsuite').findall('testcase'))),
    'native_component_cases': 7, 'native_variable_tests_compared_by_production_calculator': 317,
    'effective_saved_meta_examples': 7,
    'saved_no_io_replay': hashed(pure / 'SAVED_REPLAY_FINAL_003.json'),
    'example_provenance_correction': hashed(pure / 'EXAMPLES_002/CORRECTION_002.json'),
    'msa_examples': hashed(msa / 'FILLED_EXAMPLES.json'),
    'msa_saved_no_io_replay': hashed(msa / 'SAVED_REPLAY_RESULT.json'),
    'meta_native_parser_examples': hashed(meta / 'VERIFICATION_001.json'),
    'scope_and_limits': [
        'The five host tests manually journal the selected actions; three separate composed Workflow runs verify actual method_loop execution.',
        'The composed runs use controlled decisions, scientific/root continuation and zero scientific/root projected credit; native transport is synthetic. Practical operation credit and endpoint estimation use production paths.',
        'The original GeneTree suite remains 3 passed and 1 incorrect test-assertion failure; the correction is verified separately against its saved run, not relabeled as a green original suite.',
        'No configured model, live BV-BRC, deployed application version, native full phylogeny program, HPC or W05 annotation-credit correctness is established.',
        'New MSA and MetaCATS scientific parsing/calculation components are installed; provider sheets, source associations, tool information, application binding and requested episode returns remain unfinished.',
        'Biological group counts must be calculable from known memberships without R-column evidence; the new independent biological-count/standard-statistics contract is being defined. Existing implemented source-reproduction calculations remain distinct.',
        'MSA XMFA multi-block coordinates, source/definition prealigned mismatch, transformation maps and actual resource execution remain explicit work.',
        'The initial twelve-group saved numerical example used unpadded matrix tokens in R-column fields. The original remains recorded; EXAMPLES_002 supplies exact observed padded tokens and evidence. All numerical statistics are unchanged.',
        'Nine new pure modules do not mean nine completed tools. All 308 fixed rows and 288 resource bindings remain tracked; zero complete scientific tools are claimed.',
    ],
}
receipt_path = pure / 'PRODUCTION_PURE_AND_WORKFLOW_CHECKPOINT_019.json'
with receipt_path.open('x') as stream:
    json.dump(receipt, stream, indent=2); stream.write('\n')
identity = 'PHYLOGENY-WORKFLOW-AND-MSA-METACATS-PURE-019'
evidence = {'id': identity, 'kind': 'production_components_and_controlled_episode_verification',
    'summary': 'Five authenticated host tests pass. All three controlled phylogeny Workflow modes close and replay; original GeneTree assertion failure is preserved with separate corrected saved-run evidence. Nine new MSA/MetaCATS pure modules pass212combined tests;317native variable tests match and7effective saved examples replay without I/O.',
    'qualification': 'Native source components, synthetic service Workflow tests and live-resource verification remain separate. MSA/MetaCATS production provider/return paths are unfinished; no completed scientific tool or W05 claim.',
    'reports': [hashed(p) for p in (receipt_path, pure / 'COMBINED_VERIFICATION_001.json',
        pure / 'SAVED_REPLAY_FINAL_003.json', msa / 'HANDOFF.md', meta / 'VERIFICATION_001.json',
        native / 'NUMERICAL_VERIFICATION_001.json')]}
assert identity not in {item['id'] for item in work['verification_evidence']}
rows = {row['id']: row for row in work['rows']}
bindings = {row['id']: row for row in work['resource_bindings']}
for key in ('C-L193-CodonTree', 'C-L194-GeneTree'):
    row = rows[key]
    row['overall'] = 'provider_library_and_controlled_full_workflow_verified_live_resource_unfinished'
    row['production_result_binding'] = 'registered_adapter_requested_returns_and_two_parent_composed_workflow_verified_with_synthetic_transport'
    row['integration_verification'] = ('five_host_tests_and_all_controlled_workflow_modes_closed_with_saved_no_regrade_replay_gene_assertion_correction_separately_recorded')
    row['note'] += (' Update019: all five actual-publication/two-parent host checks passed. Three separate '
        'composed Workflow runs closed with12actions/12observations and4returns each, forwarding4tips,16cells '
        'andgapfraction0.125. CodonTree and concatenated-loci each pass4tests. GeneTree retains3passes/1incorrect '
        'test-assertion failure, plus its corrected full numeric check on the same saved run; its saved replay '
        'also passes. No new native calls/observations occur during replay. Controls include decisions, '
        'scientific/root continuation and zero scientific/root credit projection, plus synthetic transport. '
        'No configured model/live resource/W05 or scientific annotation-credit claim.')
for key in ('C-L204-MSA', 'C-L205-MetaCATS'):
    row = rows[key]
    row['overall'] = 'pure_native_parsers_and_numerical_calculators_installed_provider_and_episode_binding_unfinished'
    row['source_presence'] = 'retained_complete_native_sources_and_outputs_with_installed_tool_specific_pure_modules'
    row['numerical_sheet'] = 'native_documents_and_populated_numerical_component_records_verified_full_provider_sheet_pending'
    row['numerical_verification'] = '212_combined_new_module_tests_and_saved_no_io_replay_pass_native_and_synthetic_cases_distinguished'
    if key.endswith('-MSA'):
        row['native_parser'] = 'dna_protein_frequency_tables_with_and_without_reference_native_formats_verified'
        row['deterministic_calculator'] = 'literal_entropy_and_staged_original_reference_differences_installed_and_verified'
        row['metadata_extractor'] = 'supplied_reference_and_original_coordinate_relationships_validated_provider_associations_unfinished'
        detail = 'All13native sites reproduce Scores;2native reference-table branches ran successfully; full saved examples replay with I/O/parsers disabled.'
    else:
        row['native_parser'] = 'five_native_table_metadata_matrix_parsers_verified_on42retained_artifacts_plus_legacy_example'
        row['deterministic_calculator'] = 'source_reproduction_counts_statistics_effects_multiplicity_installed317native_tests_match_biological_group_path_pending'
        row['metadata_extractor'] = 'ordered_metadata_and_matrix_tokens_preserved_original_input_and_group_column_association_unfinished'
        detail = 'Seven complete numerical examples replay without I/O;317native variable-site statistics match. Exact padded Rtoken correction is additive. Independent biological grouping/standard statistics still needs its accepted implementation.'
    row['note'] += (' Update019: nine combined new MSA/MetaCATS pure modules pass212tests with unchanged '
        'source hashes across the run. ' + detail + ' This is component verification, not a complete '
        'application/tool-library/episode binding. Provider schemas and source associations are being '
        'defined; native MSA XMFA coverage and explicit unfinished resource variants remain on scope.')
for key in ('C-L193-CodonTree', 'C-L194-GeneTree', 'C-L204-MSA', 'C-L205-MetaCATS'):
    row = rows[key]
    row['evidence_ids'].append(identity)
    binding = bindings[key + '::api']
    for field in ('invocation_contract', 'production_result_binding', 'integration_verification'):
        binding[field] = row[field]
    binding['evidence_ids'] = deepcopy(row['evidence_ids'])
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
    'previous_goal_turn_classification': 'no progress: the immediately preceding user-question turn rechecked and explained the already-fixed ordering defect; it made no implementation change. This continuation revalidated current work and implemented/verified the next independent pure workloads.',
    'changes': changes, 'added_evidence': [evidence], 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_019.json').open('x') as stream:
    json.dump(update, stream, indent=2); stream.write('\n')
status_path.write_bytes(updated)
print(json.dumps({'checkpoint': 19, 'changes': len(changes), 'scope_rows': 308,
    'resource_bindings': 288, 'new_status_sha256': update['new_status_sha256']}))
