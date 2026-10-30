"""Record installed phylogeny bundle, tool information and return bindings.

Only completed checks enter the evidence below. The live host-return and full
Workflow test processes are explicitly pending and supply no passing count.
"""
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
prior = json.loads((HERE / 'PROGRESS_UPDATE_017.json').read_text())
assert before == prior['new_status_sha256'] == 'f1472e896f9bbf9291f2a8500d329300991056aed7d2b75775a3fdeeba2ecae6'
assert not (HERE / 'PROGRESS_UPDATE_018.json').exists()
work = json.loads(raw)
old = deepcopy(work)
base = ROOT / 'verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24'
bundle = ROOT / 'verification/tool_graders_bvbrc_phylogeny_bundle_2026-10-24'
returns = ROOT / 'verification/tool_graders_bvbrc_phylogeny_returns_2026-10-24'
info = ROOT / 'verification/tool_graders_bvbrc_phylogeny_tool_info_2026-10-24'


def hashed(path):
    return {'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def suite(path, expected):
    record = ET.parse(path).getroot().find('testsuite')
    counts = {key: int(record.attrib[key]) for key in ('tests', 'errors', 'failures', 'skipped')}
    assert counts == {'tests': expected, 'errors': 0, 'failures': 0, 'skipped': 0}
    return {**hashed(path), 'counts': counts, 'seconds': float(record.attrib['time'])}


assert '147 passed' in (bundle / 'PYTEST_003.txt').read_text()
assert '67 passed' in (info / 'pytest-final.txt').read_text()
return_runs = json.loads((returns / 'TEST_RUNS_001.json').read_text())
for filename, expected in return_runs['final_sources_sha256'].items():
    assert hashed(ROOT / filename)['sha256'] == expected
for item in json.loads((info / 'MANIFEST.json').read_text())['owned_files']:
    assert hashed(ROOT / item['path'])['sha256'] == item['sha256']
checks = {
    'existing_host_and_homology': suite(base / 'host-hook-tests-001.xml', 25),
    'actual_library_binding': suite(base / 'library-binding-tests-001.xml', 5),
    'saved_returns_before_last_narrow_change': suite(returns / 'pytest-final-006.xml', 172),
    'saved_returns_final_changed_path': suite(returns / 'pytest-family-final-008.xml', 13),
}
modules = ['bvbrc_phylogeny_bundle_contracts', 'bvbrc_phylogeny_bundle_resolution',
    'bvbrc_phylogeny_bundle_projection', 'bvbrc_gene_tree_bundle_adapter',
    'bvbrc_codon_tree_bundle_adapter', 'bvbrc_phylogeny_returns', 'bvbrc_phylogeny_tool_info',
    'bvbrc_appservice_adapters', 'api_service_execution', 'bvbrc_appservice_host', 'execution_episodes']
receipt = {
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'scope': 'Installed GeneTree/CodonTree pure bundle, requested return, information library and existing host hooks',
    'provider_modes': ['gene_tree', 'concatenated_sequence_loci', 'core_genome_codon_protein'],
    'component_results': {
        'pure_bundle_tests': 147, 'tool_information_tests': 67,
        'saved_return_broad_tests_before_final_change': 172,
        'saved_return_final_focused_tests': 13,
        'focused_return_overlap_with_broad': 12,
        'complete_final_173_case_return_suite_run': False,
        'host_compatibility_tests': 25, 'actual_library_binding_tests': 5,
        'counts_are_not_added_as_independent_coverage': True,
    },
    'completed_junit_checks': checks,
    'pure_bundle_log': hashed(bundle / 'PYTEST_003.txt'),
    'tool_information_log': hashed(info / 'pytest-final.txt'),
    'saved_return_run_details': hashed(returns / 'TEST_RUNS_001.json'),
    'full_bundle_examples': hashed(bundle / 'EXAMPLES_001/manifest.json'),
    'full_tool_information_examples': hashed(info / 'FILLED_EXAMPLES.json'),
    'ten_bundle_saved_examples_replay_exactly_without_parsing_or_io': True,
    'production_sources_at_receipt': [hashed(ROOT / 'gene_annotation_episode' / (name + '.py'))
                                      for name in modules],
    'new_root_tests_at_receipt': [hashed(ROOT / 'tests' / name) for name in (
        'test_bvbrc_phylogeny_host_integration.py', 'test_bvbrc_phylogeny_library_binding.py')],
    'pending_checks_not_counted': [
        'Corrected actual publication and two-parent host test: running session 51766; numerical partial facts must survive both admissions.',
        'Full shared Workflow selection/publication/parent returns: independently running in fresh worker 133.',
    ],
    'retained_failed_check': {
        'path': str((base / 'host-integration-tests-001.xml').relative_to(ROOT)),
        'tests': 5, 'passed': 2, 'failed': 3,
        'cause': 'Test incorrectly expected no missing support/replicate fields in requested branch rows. Original synthetic data contains lengths but no such support/counts. Test corrected; production behavior unchanged.',
    },
    'qualifications': [
        'Native source examples and synthetic service responses remain distinguished from live service execution.',
        'Configured library selection and exact child commission routes are verified; full Workflow is still pending.',
        'Requested facts and full sheets are separate; return consumers perform no recalculation or acquisition.',
        'No live BV-BRC task, deployed version, authentication, or original producer-byte guarantee is established.',
        'No method_loop, credit, continuation, prompt template, W05 or literature change belongs to this integration.',
        'Source hashes here describe files at receipt time; they do not retroactively claim a before/after execution snapshot for older tests.',
    ],
}
receipt_path = base / 'BUNDLE_LIBRARY_HOST_REGISTRATION_VERIFICATION_001.json'
with receipt_path.open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')

identity = 'PHYLOGENY-BUNDLE-LIBRARY-RETURN-HOST-REGISTRATION-018'
assert identity not in {item['id'] for item in work['verification_evidence']}
evidence = {
    'id': identity, 'kind': 'component_and_binding_verification',
    'summary': 'Installed bundle adapters (147 passing tests), information entries (67), saved returns (172 before final narrow correction; 13 focused afterward), existing host hooks (25) and actual library routes (5). Counts overlap and are not summed.',
    'qualification': 'All three modes have bound launch/results information and host hooks. Actual authenticated two-parent host tests and shared Workflow tests remain pending; no live resource verification.',
    'reports': [hashed(path) for path in (receipt_path, bundle / 'VERIFICATION_001.md',
        bundle / 'EXAMPLES_001/manifest.json', returns / 'HANDOFF.md',
        returns / 'TEST_RUNS_001.json', info / 'HANDOFF.md', info / 'MANIFEST.json')],
}
rows = {row['id']: row for row in work['rows']}
bindings = {row['id']: row for row in work['resource_bindings']}
for key in ('C-L193-CodonTree', 'C-L194-GeneTree'):
    row = rows[key]
    row['overall'] = 'bundle_library_and_requested_return_hooks_installed_full_workflow_and_live_verification_unfinished'
    row['tool_information'] = 'actual_bound_api_name_description_resources_instructions_and_launch_results_contracts_verified'
    row['invocation_contract'] = 'explicit_provider_pin_and_resource_specific_existing_child_commissions_bound_library_verified'
    row['production_result_binding'] = 'pure_bundle_adapter_and_requested_returns_registered_in_existing_host_full_workflow_pending'
    row['numerical_verification'] = 'prior_612_tests_plus9_subtests_and_provider_replays_retained_147_bundle_tests_10_saved_bundle_replays'
    row['integration_verification'] = '5_actual_library_binding_tests_25_host_compatibility_tests_pass_full_host_and_workflow_pending'
    row['note'] += (' Update018: all three combined provider modes now have real resource-bound library contracts, '
        'static pure adapters and existing requested-return hooks. The bundle tests pass 147 cases and ten complete saved examples '
        'recalculate identically without parsing or I/O. Information tests pass 67; actual library bindings pass five; existing '
        'host/Homology checks pass 25. Saved-return verification is 172 before the last narrow identity correction and 13 focused '
        'afterward, with overlap explicitly retained. Authenticated two-parent host and full shared Workflow tests are running '
        'and are not counted as completed. No live service, method_loop, credit, W05 or literature change is claimed.')
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
    originals = {row['id']: row for row in old[group]}
    assert set(originals) == {row['id'] for row in work[group]}
    changes += [{'group': group, 'id': row['id'], 'before': originals[row['id']], 'after': deepcopy(row)}
                for row in work[group] if row != originals[row['id']]]
updated = (json.dumps(work, indent=2) + '\n').encode()
update = {
    'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before, 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'previous_goal_turn_classification': 'verified wait: session 51766 was polled live and returned one passing case; bug explanation itself added no implementation. Library run terminal evidence was recovered without restarting it.',
    'changes': changes, 'added_evidence': [evidence], 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': 0,
}
with (HERE / 'PROGRESS_UPDATE_018.json').open('x') as stream:
    json.dump(update, stream, indent=2)
    stream.write('\n')
status_path.write_bytes(updated)
print(json.dumps({'checkpoint': 18, 'changes': len(changes), 'scope_rows': 308,
    'resource_bindings': 288, 'new_status_sha256': update['new_status_sha256']}))
