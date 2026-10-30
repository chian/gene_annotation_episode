"""Reconcile actual original outcomes with subsequent targeted evidence.

This does not rerun or invent tests, timings or a full final-suite execution.
"""
from pathlib import Path
import hashlib,json,re
import xml.etree.ElementTree as ET

BASE=Path(__file__).resolve().parent
lines=(BASE/'COLLECTION_FINAL_001.txt').read_text().splitlines()
collected=[line for line in lines if line.startswith('tests/') and '::' in line]
new_nodes={
    'tests/test_literature_context_native_observations.py::test_distinct_source_contexts_can_share_one_reported_setting',
    'tests/test_literature_context_native_observations.py::test_not_extracted_basis_cannot_carry_an_extracted_numeric_value'}
original=[node for node in collected if node not in new_nodes]
assert len(collected)==325 and len(set(collected))==325 and len(original)==323 and new_nodes<=set(collected)
log=(BASE/'TEST_JOINED_001.txt').read_text()
failed=[line.removeprefix('FAILED ').split(' - ',1)[0] for line in log.splitlines() if line.startswith('FAILED ')]
assert len(failed)==14 and set(failed)<=set(original)
assert '14 failed, 309 passed in 327.48s' in log
selected_prefixes=[
 'tests/test_literature_context_native_observations.py::'+name for name in (
 'test_points_statistics_identities_and_sampling_meanings',
 'test_missing_values_and_nominal_setting_not_hidden_by_missing_meaning',
 'test_independent_exact_subset_forwarding_and_first_readonly_replay',
 'test_positions_fail_structurally',
 'test_exact_micro_to_milli_conversion_and_source_token_retention',
 'test_same_physical_number_survives_recipe_and_excerpt_changes',
 'test_distinct_source_contexts_can_share_one_reported_setting')]
repair=[n for n in collected if any(n==p or n.startswith(p+'[') for p in selected_prefixes)
    or n.startswith('tests/test_literature_context_native_integration.py::')
    or n.startswith('tests/test_literature_context_native_primary_126.py::')
    or n in {
        'tests/test_literature_context_integration.py::test_actual_selected_return_and_saved_only_reconstruction[primary]',
        'tests/test_literature_context_integration.py::test_ordinary_child_parent_delivery_has_one_own_observation_per_action[primary]'}]
assert len(repair)==17 and set(failed)<=set(repair)
assert '17 passed in 83.91s' in (BASE/'TEST_REPAIR_001.txt').read_text()
assert '3 passed in 15.76s' in (BASE/'TEST_FINAL_SEMANTICS_001.txt').read_text()
assert '2 passed in 10.63s' in (BASE/'TEST_PRIMARY_PORTABLE_001.txt').read_text()
profile=json.loads((BASE/'contract_profile_run_001/proof.json').read_text());assert profile['status']=='passed'
primary=json.loads((BASE/'primary_run_005/summary.json').read_text());assert all(c['status']=='passed' for c in primary['cases'])
records=[]
for node in original:
    failure=None
    if node in failed:
        failure=('isolated_retained_fixture_missing' if node.startswith('tests/test_literature_context_integration.py::')
            else 'new_native_context_variable_shadowing')
    records.append(dict(nodeid=node,original_outcome='failed' if failure else 'passed',original_failure_attribution=failure,
        repair_evidence='TEST_REPAIR_001.txt' if failure else None,
        reconciled_outcome='passed',verification_basis='targeted actual repair pass' if failure else 'original actual pass; not repeated'))
audit=dict(kind='Reconciled node-level evidence; not a claimed full-suite rerun',original_run=dict(nodes=323,passed=309,failed=14,elapsed_seconds=327.48,
    stdout='TEST_JOINED_001.txt',stderr='TEST_JOINED_001.stderr'),
    original_node_roster_method='Final actual 325-node collection minus the two explicitly added guards; existing node names retained. No per-node durations were recorded or inferred.',
    repaired_original_failures=14,targeted_repair=dict(nodes=repair,passed=17,elapsed_seconds=83.91,stdout='TEST_REPAIR_001.txt'),
    final_changed_semantics=dict(passed=3,elapsed_seconds=15.76,stdout='TEST_FINAL_SEMANTICS_001.txt'),
    primary_test_portability=dict(passed=2,elapsed_seconds=10.63,stdout='TEST_PRIMARY_PORTABLE_001.txt'),
    new_guard_nodes=sorted(new_nodes),profile_proof='contract_profile_run_001/proof.json',primary_ordinary_proof='primary_run_005/summary.json',
    records=records,full_final_323_node_rerun_performed=False,individual_test_durations_invented=False)
(BASE/'ORIGINAL_323_COVERAGE_001.json').write_text(json.dumps(audit,indent=2))
xml=ET.Element('testsuites',dict(name='126 reconciled evidence, no final full-suite rerun'))
def properties(parent,values):
    target=ET.SubElement(parent,'properties')
    for name,value in values.items():ET.SubElement(target,'property',name=name,value=str(value))
# Raw original suite preserves actual original failures.
raw=ET.SubElement(xml,'testsuite',name='original_actual_run_323',tests='323',failures='14',errors='0',time='327.48')
properties(raw,dict(evidence='TEST_JOINED_001.txt',node_roster='COLLECTION_FINAL_001.txt minus two documented new guards',per_case_times='not recorded'))
for row in records:
    case=ET.SubElement(raw,'testcase',classname=row['nodeid'].split('::')[0],name=row['nodeid'].split('::',1)[1])
    if row['original_outcome']=='failed':
        ET.SubElement(case,'failure',type=row['original_failure_attribution'],message='Actual initial failure; subsequently passed in TEST_REPAIR_001.txt').text=(
            'Missing retained huc XML fixture in the isolated checkout; copied verbatim before targeted pass.'
            if row['original_failure_attribution']=='isolated_retained_fixture_missing' else
            'KeyError(setting_kind): selected numeric witness shadowed the enclosing context variable. Fixed in exact approved production patch002.')
# Exact targeted run, kept separate so it is not confused with a full rerun.
rep=ET.SubElement(xml,'testsuite',name='actual_targeted_repair_17',tests='17',failures='0',errors='0',time='83.91')
properties(rep,dict(evidence='TEST_REPAIR_001.txt',repaired_original_failures=14,other_affected_or_new_cases=3))
for node in repair:ET.SubElement(rep,'testcase',classname=node.split('::')[0],name=node.split('::',1)[1])
rec=ET.SubElement(xml,'testsuite',name='reconciled_original_323_coverage',tests='323',failures='0',errors='0')
properties(rec,dict(single_run='false',original_passes_reused=309,actual_failed_nodes_repaired=14,full_final_suite_rerun='not performed',evidence='ORIGINAL_323_COVERAGE_001.json'))
for row in records:
    case=ET.SubElement(rec,'testcase',classname=row['nodeid'].split('::')[0],name=row['nodeid'].split('::',1)[1])
    properties(case,dict(original_outcome=row['original_outcome'],verification_basis=row['verification_basis'],
        original_failure_attribution=row['original_failure_attribution'] or '',repair_evidence=row['repair_evidence'] or ''))
guards=ET.SubElement(xml,'testsuite',name='new_guards_separate',tests='2',failures='0',errors='0')
for node in sorted(new_nodes):
    case=ET.SubElement(guards,'testcase',classname=node.split('::')[0],name=node.split('::',1)[1])
    properties(case,dict(evidence='TEST_REPAIR_001.txt' if 'distinct_source_contexts' in node else 'TEST_FINAL_SEMANTICS_001.txt'))
info=ET.SubElement(xml,'testsuite',name='existing_opt_in_profile_constructed_workflow',tests='1',failures='0',errors='0')
case=ET.SubElement(info,'testcase',classname='engineering_script',name='complete operation and native return contracts, recurring TASK, bounded presentation')
properties(case,{k:profile[k] for k in ('configuration_profile','selected_information_lookups','actual_actions','actual_own_runtime_observations','maximum_task_chars','maximum_prompt_chars')})
properties(info,dict(evidence='contract_profile_run_001/proof.json',pytest_test='false; actual script assertions'))
prim=ET.SubElement(xml,'testsuite',name='retained_primary_ordinary_boundary',tests='2',failures='0',errors='0')
for item in primary['cases']:
    case=ET.SubElement(prim,'testcase',classname='engineering_script',name=item['case']);properties(case,item)
# Preserve actual raw runs separately; the final coverage document has one
# entry per original node and does not double-count raw and reconciled cases.
history=ET.Element('testsuites',dict(name='Actual original and targeted run history; distinct runs'))
xml.remove(raw);xml.remove(rep);history.append(raw);history.append(rep)
ET.indent(history,space='  ')
ET.ElementTree(history).write(BASE/'ACTUAL_RUN_HISTORY_001.xml',encoding='utf-8',xml_declaration=True)
ET.indent(xml,space='  ')
ET.ElementTree(xml).write(BASE/'ORIGINAL_323_RECONCILIATION_001.xml',encoding='utf-8',xml_declaration=True)
print(json.dumps(dict(original_nodes=len(original),original_passed=309,original_failed=14,repaired_original_failures=14,actual_targeted_passes=17,
    reconciled_original_coverage=323,new_guards=2,profile_scripts=1,primary_ordinary_cases=2,full_final_suite_rerun=False)))
