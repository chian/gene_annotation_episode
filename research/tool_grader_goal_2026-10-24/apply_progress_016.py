"""Record verified provider installation and scoped transport/calculator fixes."""
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
original = status_path.read_bytes()
before_hash = hashlib.sha256(original).hexdigest()
prior = json.loads((HERE / 'PROGRESS_UPDATE_015.json').read_text())
assert before_hash == prior['new_status_sha256'] == 'd5cb097e2bc7e151965761b4371b1bdc31b8e08a5cab02f6a1655fc89e3f565e'
assert not (HERE / 'PROGRESS_UPDATE_016.json').exists()
work = json.loads(original); old = deepcopy(work)
base = ROOT / 'verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24'
handoffs = ROOT / 'verification/tool_graders_bvbrc_phylogeny_provider_handoffs_2026-10-24'
correction = ROOT / 'verification/tool_graders_bvbrc_codon_matrix_population_2026-10-24'


def hashed(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def counts(path):
    suite = ET.parse(path).getroot().find('testsuite')
    return {key: int(suite.attrib[key]) for key in ('tests', 'errors', 'failures', 'skipped')}


providers = json.loads((base / 'PRODUCTION_PROVIDER_VERIFICATION_001.json').read_text())
assert providers['tests'] == {'tests': 102, 'errors': 0, 'failures': 0, 'skipped': 0}
assert len(providers['examples']) == 14 and all(row['equal'] for row in providers['examples'])
assert providers['forbidden_access_attempts'] == 0 and providers['inputs_unchanged']
assert counts(handoffs / 'supplied-content-tests-001.xml') == {'tests': 101, 'errors': 0, 'failures': 1, 'skipped': 0}
assert counts(handoffs / 'supplied-content-tests-002.xml') == {'tests': 12, 'errors': 0, 'failures': 0, 'skipped': 0}
assert counts(correction / 'pytest-after.xml') == {'tests': 112, 'errors': 0, 'failures': 0, 'skipped': 0}
saved = json.loads((correction / 'SAVED_RECALCULATION.json').read_text())
assert saved['historical_cases_reproduced'] == 31 and saved['new_cases_reproduced'] == 4
assert saved['historical_components_and_requirements_exactly_equal'] and saved['new_components_and_requirements_exactly_equal']
assert saved['forbidden_access_attempts'] == 0 and saved['inputs_unchanged']
calc = ROOT / 'gene_annotation_episode/bvbrc_codon_tree_calculators.py'
assert hashed(calc)['sha256'] == 'e8eeab6a379af3cf80b0c92089df13a8c06630abf8baabe04593d94aaab87d54'

host_files = [ROOT / 'gene_annotation_episode' / name for name in (
    'bvbrc_appservice_schemas.json', 'bvbrc_appservice_contracts.py',
    'bvbrc_appservice_custody.py', 'bvbrc_appservice_bundle_values.py',
    'bvbrc_appservice_publication.py')]
host_files += [ROOT / 'tests/test_bvbrc_appservice_supplied_contents.py',
               ROOT / 'tests/test_bvbrc_appservice_contracts.py',
               handoffs / 'supplied-content-tests-001.xml', handoffs / 'supplied-content-tests-002.xml']
host_report = {
    'scope': 'Explicit previously received raw-content operands through existing results custody/publication',
    'focused_tests': counts(handoffs / 'supplied-content-tests-002.xml'),
    'earlier_suite': counts(handoffs / 'supplied-content-tests-001.xml'),
    'earlier_failure': 'Test double omitted required validate_parameters and validate_requested_form; production interface was unchanged for this repair.',
    'coverage': ['original optional binding omission versus explicit empty array',
                 'completed parent action and admitted immediate-child possession',
                 'reject present-but-unreceived and post-commission sources',
                 'reject wrong digest, byte count and original source field',
                 'no automatic nested-source discovery',
                 'exact supplied bytes reach the pure consumer with actual task output',
                 'publication and saved replay preserve original selected contents',
                 'replay adds no acquisition, source, action, observation or calculation'],
    'qualifications': ['Controlled native client and test consumer, not a live BV-BRC result.',
                       'No phylogeny scientific projection or complete Workflow path proved.',
                       'The 12 focused tests overlap the earlier 101-test run; counts are not additive.'],
    'files': [hashed(path) for path in host_files],
}
host_report_path = handoffs / 'SUPPLIED_CONTENT_VERIFICATION_001.json'
with host_report_path.open('x') as stream:
    json.dump(host_report, stream, indent=2); stream.write('\n')

entries = [
    {'id': 'PHYLOGENY-SHARED-GENETREE-PROVIDERS-PRODUCTION-102', 'kind': 'component_verification',
     'passed': 102, 'failed': 0,
     'summary': 'Five reviewed shared/GeneTree modules installed. 102 production tests and14 exact full-example replays pass with I/O/native parsing disabled; saved inputs unchanged.',
     'qualification': 'Pure extraction/validation/calculation. Full selected-tool, resource-child, typed parent return and live service paths remain unfinished.',
     'reports': [hashed(base / name) for name in ('PRODUCTION_PROVIDER_INSTALLATION_001.json', 'PRODUCTION_PROVIDER_VERIFICATION_001.json', 'production-common-gene-tests-001.xml')]},
    {'id': 'BVBRC-EXPLICIT-SUPPLIED-CONTENTS-012', 'kind': 'component_verification',
     'passed': 12, 'failed': 0,
     'summary': 'Original selected raw-content operands pass exact custody and reach pure publication consumers; replay performs no new work.',
     'qualification': 'Earlier101-check run retained100passes and1 test-double interface failure; repaired focused12 pass. Controlled transport only, no live or complete phylogeny episode claim.',
     'reports': [hashed(host_report_path)]},
    {'id': 'CODONTREE-DECLARED-MATRIX-POPULATION-112', 'kind': 'component_verification',
     'passed': 112, 'failed': 0,
     'summary': 'Corrected matrix completeness scope without changing formulas. Existing91plus21new cases pass;31historical and4new complete saved examples replay exactly without I/O.',
     'qualification': 'Independent optional/outside-genome memberships stay retained. Explicit contradictory mapped facts still fail. Provider and full episode verification remain separate.',
     'reports': [hashed(correction / name) for name in ('VERIFICATION.json', 'SAVED_RECALCULATION.json', 'pytest-before.xml', 'pytest-after.xml')]},
]
assert not {row['id'] for row in entries} & {row['id'] for row in work['verification_evidence']}
rows = {row['id']: row for row in work['rows']}
bindings = {row['id']: row for row in work['resource_bindings']}
gene = rows['C-L194-GeneTree']
gene['overall'] = 'pure_gene_provider_installed_bundle_library_and_episode_path_unfinished'
gene['numerical_sheet'] = 'complete_gene_tree_and_concatenated_loci_sheets_populated_and_saved_replayed'
gene['metadata_extractor'] = 'shared_and_gene_provider_actual_input_row_locus_function_taxon_and_native_joins_installed_verified'
gene['deterministic_calculator'] = 'gene_dispatch_to_eight_shared_calculations_installed_offline_replayed'
gene['numerical_verification'] = '102_production_provider_tests_and14_complete_saved_replays_pass_prior_shared_checks_retained'
gene['evidence_ids'].extend(row['id'] for row in entries[:2])
gene['note'] += (' Update016: shared/GeneTree provider modules installed unchanged from reviewed handoffs;102tests and14complete-example offline replays pass. '
    'Both retained native XML examples preserve17tips and14support observations of unknown method. Explicit supplied-file custody/publication tests pass12focused cases. '
    'Bundle adapters, static registration/tool information, typed episode communication and live verification remain unfinished.')
codon = rows['C-L193-CodonTree']
codon['overall'] = 'shared_provider_and_codon_components_installed_codon_provider_review_and_episode_path_unfinished'
codon['metadata_extractor'] = 'shared_provider_installed_codon_stage_and_genome_identity_assembly_under_review'
codon['deterministic_calculator'] = 'shared_dispatch_and_codon_calculations_verified_declared_matrix_scope_corrected'
codon['numerical_verification'] = '112_codon_calculator_tests_31historical_and4new_replays_plus102_shared_gene_provider_tests_pass'
codon['evidence_ids'].extend(row['id'] for row in entries)
codon['note'] += (' Update016: shared provider installed and corrected Codon calculator honors explicit selected genome populations;112tests and31historical+4new saved replays pass. '
    'All historical numerical outputs remain equal; zero-size selected populations retain zero counts and null fractions. Codon provider is staged and under final association review; '
    'shared-container source evidence must not be mistaken for an exact member-to-genome identity. Its production installation, bundle/library/typed-return integration and live run remain unfinished.')
for row in (gene, codon):
    bindings[row['id'] + '::api']['evidence_ids'] = deepcopy(row['evidence_ids'])
work['verification_evidence'].extend(entries)
assert len(work['rows']) == len(old['rows']) == 308
assert len(work['resource_bindings']) == len(old['resource_bindings']) == 288
assert work['complete_scientific_tools_claimed'] == old['complete_scientific_tools_claimed'] == 0
changes = []
for group in ('rows', 'resource_bindings'):
    original_rows = {row['id']: row for row in old[group]}
    assert set(original_rows) == {row['id'] for row in work[group]}
    for row in work[group]:
        if row != original_rows[row['id']]:
            changes.append({'group': group, 'id': row['id'], 'before': original_rows[row['id']], 'after': deepcopy(row)})
updated = (json.dumps(work, indent=2) + '\n').encode()
update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-24',
          'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
          'previous_status_sha256': before_hash, 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
          'previous_goal_turn_classification': 'no progress: the bug explanation restated verified existing behavior; this continuation installed providers and verified transport/calculator corrections',
          'changes': changes, 'added_evidence': entries, 'scope_changes': False,
          'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_016.json').open('x') as stream:
    json.dump(update, stream, indent=2); stream.write('\n')
status_path.write_bytes(updated)
print(json.dumps({'checkpoint': 16, 'changes': len(changes), 'added_evidence': len(entries),
                  'scope_rows': 308, 'resource_bindings': 288,
                  'new_status_sha256': update['new_status_sha256'], 'complete_scientific_tools_claimed': 0}))
