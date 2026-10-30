"""Verify the declared frozen metadata generation using synthetic bytes only."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import runpy
import sys

import pytest


pin = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(pin))

from gene_annotation_episode.literature_episodes import _population_catalog, LiteratureEpisodes
from gene_annotation_episode.literature_partner_native_inputs import partner_source_population_schema
from gene_annotation_episode.literature_partner_operand_information import partner_source_population_schema_with_information
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episode_contract_information import operation_contract_information
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE, CONTRACT_ARGUMENT_TRANSPORT


def save(name, value):
    (destination / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


helper = runpy.run_path(str(pin / 'tests/test_literature_partner_operand_information.py'))
bare = partner_source_population_schema()
informed = partner_source_population_schema_with_information()
helper['assert_only_description_additions'](bare, informed)
assert helper['strip_descriptions'](bare) == helper['strip_descriptions'](informed)
save('bare_partner_schema_004.json', bare)
save('annotated_partner_schema_004.json', informed)

catalog = _population_catalog()
original = json.loads((destination / 'baseline_catalog.json').read_text())
changed = [left['name'] for left, right in zip(original, catalog) if left != right]
assert len(catalog) == len(original) == 19 and changed == ['literature.partner.source.populate']
selected = next(row for row in catalog if row['name'] == changed[0])
assert selected['input_schema'] == informed
assert {k: v for k, v in selected.items() if k != 'input_schema'} == {
    k: v for k, v in next(row for row in original if row['name'] == selected['name']).items() if k != 'input_schema'}
facts = LiteratureEpisodes(None, rate_population=True).fact_sources('literature')
assert facts == json.loads((destination / 'baseline_returns.json').read_text()) and len(facts) == 18
save('catalog_and_return_preservation_004.json', {
    'operation_count': len(catalog), 'return_count': len(facts), 'changed_catalog_entries': changed,
    'all_return_contracts_exactly_unchanged': True, 'other_18_catalog_entries_exactly_unchanged': True,
    'description_only_additions': True,
    'note': 'Bare schema already has105 inherited REF descriptions; all existing values remain exact.'})

args, source, _witness, _text = helper['fixture']()
before = deepcopy(args)
first = helper['checked_read'](args, source, bare)
second = helper['checked_read'](args, source, informed)
assert first == second and args == before
save('synthetic_success_arguments_004.json', args)
save('synthetic_success_extraction_004.json', second)
failures = []
for case, expected in helper['FAILURES']:
    args, source = helper['failure_fixture'](case)
    attempts = []
    for schema in (bare, informed):
        try:
            helper['checked_read'](args, source, schema)
        except ExperimentalContractError as error:
            attempts.append({'code': error.code, 'field': error.field, 'detail': error.detail})
        else:
            raise AssertionError(case + ' was accepted')
    assert attempts[0] == attempts[1] and attempts[0]['code'] == expected
    failures.append({'case': case, 'expected_code': expected, 'bare': attempts[0], 'annotated': attempts[1]})
save('actual_synthetic_failure_results_004.json', failures)

information = operation_contract_information(catalog=catalog, operation=selected['name'])
for profile in (False, True):
    state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
        'goal': {'objective': 'Evaluate a synthetic partner experiment.'}, 'scope': {},
        'literature_assignment': {'requested_partner_components': ['partner_loss']},
        'tools': [selected], 'last_local_outcome': {'status': 'invalid', 'feedback': {
            'category': 'arguments_or_reference', 'code': 'defined_unit_endpoint_mismatch',
            'field': 'defined_unit.definition.endpoint'}}}
    if profile:
        state['contract_information_profile'] = CONTRACT_INFORMATION_PROFILE
        state['tools'] = [{**selected, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT}]
    (destination / ('contract_information_prompt_004.txt' if profile else 'ordinary_prompt_004.txt')).write_text(
        render_literature_experimental_prompt(state, 'Synthetic recurring assignment.',
            lookup_results=[information] if profile else ()))

tests = sorted((pin / 'tests').glob('test_*.py'))
status = pytest.main(['-q', '-p', 'no:cacheprovider', '-c', str(pin / 'pytest.ini'), '--import-mode=importlib',
                      *map(str, tests)])
assert status == 0, status
imports = {}
for name, module in sorted(sys.modules.items()):
    if name == 'gene_annotation_episode' or name.startswith('gene_annotation_episode.') or name == 'method_loop' or name.startswith('method_loop.'):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(pin), (name, str(path))
        imports[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
save('frozen_import_proof_004.json', {'pin': str(pin), 'imports': imports,
    'pytest_exit_code': int(status), 'tests': [str(path.relative_to(pin)) for path in tests]})
print('Verified synthetic metadata generation; imported application/method_loop modules:', len(imports))
