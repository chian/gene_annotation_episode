"""Record installed Codon provider and combined production verification."""
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
raw = path.read_bytes(); before = hashlib.sha256(raw).hexdigest()
prior = json.loads((HERE / 'PROGRESS_UPDATE_016.json').read_text())
assert before == prior['new_status_sha256'] == 'f969c9391fbf1998532ea7248c2dedbe4826b124d83c0d29f6f9eafadb2d2757'
assert not (HERE / 'PROGRESS_UPDATE_017.json').exists()
work = json.loads(raw); old = deepcopy(work)
base = ROOT / 'verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24'
replay = json.loads((base / 'PRODUCTION_CODON_PROVIDER_VERIFICATION_001.json').read_text())
assert replay['tests'] == {'tests': 89, 'failures': 0, 'errors': 0, 'skipped': 0}
assert replay['saved_examples_replayed'] == 20 and replay['all_components_exactly_equal']
assert replay['forbidden_access_attempts'] == 0 and replay['inputs_unchanged']
suite_path = base / 'production-provider-combined-tests-001.xml'
suite = ET.parse(suite_path).getroot().find('testsuite')
counts = {key: int(suite.attrib[key]) for key in ('tests', 'errors', 'failures', 'skipped')}
assert counts == {'tests': 621, 'errors': 0, 'failures': 0, 'skipped': 0}


def hashed(file):
    return {'path': str(file.relative_to(ROOT)), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}


modules = ['phylogeny_formats', 'phylogeny_format_contracts', 'phylogeny_calculators',
    'phylogeny_calculation_contracts', 'phylogeny_raxml_inputs', 'bvbrc_codon_tree_native',
    'bvbrc_codon_tree_calculators', 'bvbrc_phylogeny_common_inputs', 'bvbrc_phylogeny_common_contracts',
    'bvbrc_phylogeny_common_grader', 'bvbrc_gene_tree_inputs', 'bvbrc_gene_tree_grader',
    'bvbrc_codon_tree_inputs', 'bvbrc_codon_tree_grader']
tests = ['test_phylogeny_formats', 'test_phylogeny_calculators', 'test_phylogeny_raxml_inputs',
    'test_bvbrc_codon_tree_native', 'test_bvbrc_codon_tree_calculators',
    'test_bvbrc_codon_tree_matrix_population', 'test_bvbrc_phylogeny_common',
    'test_bvbrc_gene_tree_provider', 'test_bvbrc_codon_tree_provider']
receipt = {'scope': 'Fourteen installed shared/native/provider modules across the two phylogeny tools',
    'command': '.venv/bin/python -m pytest ' + ' '.join('tests/' + name + '.py' for name in tests) +
        ' -q --junitxml=' + str(suite_path.relative_to(ROOT)),
    'pytest_passed': 612, 'pytest_subtests_passed': 9, 'junit_counts': counts,
    'deselected': 0, 'exclusions': [], 'receipt': hashed(suite_path),
    'production_modules': [hashed(ROOT / 'gene_annotation_episode' / (name + '.py')) for name in modules],
    'test_files': [hashed(ROOT / 'tests' / (name + '.py')) for name in tests],
    'codon_saved_examples': 20, 'all_saved_components_equal': True, 'forbidden_access_attempts': 0,
    'qualifications': ['Retained official native outputs plus explicitly synthetic adversarial examples.',
        'This verifies pure production parsing/extraction/calculation, not the complete selected-tool episode path.',
        'No new live scientific BV-BRC or HPC run; bundle, library and parent-return integration remain unfinished.']}
receipt_path = base / 'PRODUCTION_PROVIDER_COMBINED_VERIFICATION_001.json'
with receipt_path.open('x') as stream:
    json.dump(receipt, stream, indent=2); stream.write('\n')
identity = 'PHYLOGENY-PROVIDERS-COMBINED-PRODUCTION-612'
assert identity not in {item['id'] for item in work['verification_evidence']}
evidence = {'id': identity, 'kind': 'component_verification', 'passed': 612, 'failed': 0,
    'summary': 'All fourteen installed shared/native/GeneTree/CodonTree modules pass612tests plus9subtests, with no exclusions.20complete saved Codon provider cases replay identically without I/O or parsing.',
    'qualification': 'Component/provider production path only. Full library selection, bundle integration, episode returns and live service proof remain unfinished.',
    'reports': [hashed(base / name) for name in ('PRODUCTION_CODON_PROVIDER_INSTALLATION_001.json',
        'PRODUCTION_CODON_PROVIDER_VERIFICATION_001.json', 'PRODUCTION_PROVIDER_COMBINED_VERIFICATION_001.json',
        'production-provider-combined-tests-001.xml', 'codon-provider-verification/IDENTITY_CLARIFICATION_001.md')]}
rows = {row['id']: row for row in work['rows']}
bindings = {row['id']: row for row in work['resource_bindings']}
codon = rows['C-L193-CodonTree']
codon['overall'] = 'pure_codon_provider_installed_bundle_library_and_episode_path_unfinished'
codon['numerical_sheet'] = 'complete_codon_sheet_with_exact_genome_family_model_stages_populated_and_saved_replayed'
codon['metadata_extractor'] = 'shared_and_codon_provider_exact_source_member_genome_family_model_associations_installed_verified'
codon['deterministic_calculator'] = 'codon_dispatch_to_shared_and_three_codon_functions_installed_offline_replayed'
codon['note'] += (' Update017: installed reviewed Codon provider after exact-member identity correction;89production tests pass. '
    '20complete saved provider examples reproduce exactly using installed code with I/O and parsers disabled. '
    'Unrelated shared-container evidence neither establishes identity nor contradicts exact inline IDs; unsupported associations stay unknown with a requirement. '
    'Combined fourteen-module suite passes612tests plus9subtests with no exclusions. Bundle/library/parent-return and live integration remain unfinished.')
for key in ('C-L193-CodonTree', 'C-L194-GeneTree'):
    row = rows[key]
    row['numerical_verification'] = '612_production_tests_plus9_subtests_no_exclusions_14common_gene_and20codon_saved_replays'
    row['evidence_ids'].append(identity)
    bindings[key + '::api']['evidence_ids'] = deepcopy(row['evidence_ids'])
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
update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-24',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before, 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'previous_goal_turn_classification': 'no progress: the preceding explanation restated existing behavior; this continuation installed and verified both providers',
    'changes': changes, 'added_evidence': [evidence], 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_017.json').open('x') as stream:
    json.dump(update, stream, indent=2); stream.write('\n')
path.write_bytes(updated)
print(json.dumps({'checkpoint': 17, 'changes': len(changes), 'added_evidence': 1,
    'scope_rows': 308, 'resource_bindings': 288, 'new_status_sha256': update['new_status_sha256']}))
