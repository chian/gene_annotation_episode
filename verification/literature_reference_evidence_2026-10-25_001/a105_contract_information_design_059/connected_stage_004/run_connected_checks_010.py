"""Pinned actual boundary tests and complete synthetic request measurements."""
import ast
import asyncio
from copy import deepcopy
from functools import partial
import hashlib
import json
from pathlib import Path
import sys

PIN = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(PIN), str(PIN / 'tests')]
TESTS = ['test_schema_information_text.py', 'test_episode_contract_information.py',
    'test_contract_information_runtime_059.py', 'test_contract_information_custody_059.py',
    'test_contract_information_worker_059.py']


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write('\n')


def text(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(value)


def main():
    manifest = json.loads((PIN / 'PIN_MANIFEST.json').read_bytes())
    def verify():
        for name, row in manifest.items():
            assert fingerprint(PIN / name) == row, name
    verify()
    import pytest
    code = pytest.main(['-q', *(str(PIN / 'tests' / name) for name in TESTS), '--tb=short',
        '-p', 'no:cacheprovider', '--basetemp', str(OUT / 'pytest_work')])
    save('PYTEST_RESULT_004.json', {'exit_code': int(code), 'test_files': TESTS})
    assert code == 0
    from gene_annotation_episode import runtime
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE as PROFILE
    from gene_annotation_episode.episode_contract_information import (
        operation_contract_information, return_contract_information, expand_fact_form, validate_saved_fact_form)
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
    from gene_annotation_episode.schema_information_text import parse_schema_information, schema_fingerprint
    from gene_annotation_episode.domain import obj
    from gene_annotation_episode.tools import ToolRegistry
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from test_contract_information_runtime_059 import PresentedProvider, information, run_child
    from test_literature_kinetic_storage import setup
    from test_literature_experimental_prompt_delivery import LiteratureWire
    from test_runtime import FixtureController
    operations = _population_catalog()
    facts = LiteratureEpisodes(None, rate_population=True)._rate_fact_sources()
    examples, forms = [], []
    for row in operations:
        outcome = operation_contract_information(catalog=operations, operation=row['name'])
        assert schema_fingerprint(parse_schema_information(outcome['result']['text'])) == schema_fingerprint(row['input_schema'])
        examples.append(outcome)
    for source, row in facts.items():
        outcome = return_contract_information(facts_by_role={'literature': facts}, permitted_child_roles=['literature'], role='literature', source=source)
        assert schema_fingerprint(parse_schema_information(outcome['result']['text'])) == schema_fingerprint(row['report_schema'])
        examples.append(outcome)
        submitted = json.dumps(obj({'selected_' + source: {'$ref': 'episode-fact:' + source}}))
        result = expand_fact_form(submitted, child_role='literature', facts_by_role={'literature': facts}, permitted_child_roles=['literature'])
        assert validate_saved_fact_form(child_role='literature', submitted_schema_json=submitted,
            expanded_schema=result['expanded_schema'], declaration=result['declaration']) == result['expanded_schema']
        forms.append({'source': source, **result})
    save('ACTUAL_37_CONTRACTS_004.json', examples)
    save('ACTUAL_18_FACT_FORMS_004.json', forms)
    # Compare existing substantive TASK constants against the exact captured
    # pre-change files. Current entire TASKs are recorded below, every call.
    science_constants = {}
    for name in ('literature_experimental_prompt.py', 'literature_reference_parent_prompt.py'):
        def constants(path):
            tree = ast.parse(path.read_text())
            return {node.targets[0].id: node.value.value for node in tree.body
                if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id.endswith('_TASK') and isinstance(node.value, ast.Constant)}
        old = constants(PIN / 'baseline/gene_annotation_episode' / name)
        current = constants(PIN / 'gene_annotation_episode' / name)
        science_constants[name] = {key: {'unchanged': old[key] == current.get(key),
            'bytes': len(old[key].encode()), 'sha256': hashlib.sha256(old[key].encode()).hexdigest()} for key in old}
        assert all(row['unchanged'] for row in science_constants[name].values())
    save('SCIENTIFIC_TASK_EQUALITY_004.json', science_constants)
    # Original legacy generator functions are compiled from the frozen baseline
    # only for equality checks; the actual application imports all come from PIN.
    baseline_tree = ast.parse((PIN / 'baseline/gene_annotation_episode/runtime.py').read_text())
    names = {'_action_generation_schema', '_json_tool_arguments'}
    namespace = dict(runtime.__dict__)
    exec(compile(ast.Module(body=[node for node in baseline_tree.body if isinstance(node, ast.FunctionDef)
        and node.name in names], type_ignores=[]), '<captured-legacy-generator>', 'exec'), namespace)
    measurements = []
    for role, fact in [('child', 'literature_kinetic_cells'), ('child', 'literature_binding_interaction_cells'), ('parent', None)]:
        for profile in (None, PROFILE):
            label = role + '_' + (fact or 'evidence') + ('_legacy' if profile is None else '_information')
            directory = OUT / 'measurements' / label
            directory.mkdir(parents=True, exist_ok=False)
            store, seed, args = setup(directory / 'state')
            provider = PresentedProvider([])
            scorer = ScientificFindingProgress(FindingProgressPolicy(1))
            value = runtime.Workflow(store, ToolRegistry(store), provider, directory / 'run', 'measurement-run',
                lambda path, initial: FixtureController(str(path), initial, 1), scorer,
                initial_known_record_refs=list(seed.received_record_refs),
                episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                    contract_information_profile=profile, reference_parent_sources=[args['source_ref']]),), decision_protocol='decision_exchange_v1')
            root = value.build('annotation', 'root', 'Evaluate the supplied synthetic experimental source; preserve actual measured meanings and limitations', plain(seed.scope))
            episode = root
            if role == 'child':
                form = obj({'selected_experimental_cells': facts[fact]['report_schema']})
                episode = value.build('literature', 'child', 'Determine the source experimental numerical evidence for the assigned question', plain(seed.scope),
                    parent=root.goal, parent_path=root.source.path,
                    contract=runtime.TypedReportContract('Return only selected saved experimental components, preserving nulls and limitations', form, lambda *_: True),
                    initial={}, episode_assignment=plain(seed.assignment))
            provider.script = iter([OSError('Fixture captures original complete request; no action selected')])
            try:
                with pytest.raises(OSError):
                    if role == 'child': run_child(episode, value)
                    else: asyncio.run(root.run_async(value.context))
                logical = json.loads(value.journal.row('runtime_model_calls', episode.source.episode_id, 0)['request'])
                host = deepcopy(logical)
                physical = value.decision_exchanges.rows(episode.source.episode_id, 0)[0]['request']
                wire = LiteratureWire(directory / 'wire')
                asyncio.run(wire.complete(episode.source.episode_id, 'REASONING', physical['instructions'], physical['context'], physical['output_schema']))
                turn = wire.turns_sent()[0]
                rendered = turn['input'][0]['text']
                task, steering = rendered.split('\n\nSTEERING\n', 1)
                population_names = [row['name'] for row in (logical['context']['tools'] if role == 'child'
                    else logical['context']['reference_evidence_parent']['child_population_operations']) if row['name'].startswith('literature.')]
                assert len(population_names) == 19 and set(population_names) == {row['name'] for row in operations}
                for row in operations:
                    assert row['name'] in task and row['description'] in task
                if profile is None:
                    assert namespace['_action_generation_schema'](episode.source.exchange_schema(value.action_schema(episode.source))) == physical['output_schema']
                assert host == logical
                assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
                assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
                save('measurements/' + label + '/ORIGINAL_LOGICAL_REQUEST.json', logical)
                save('measurements/' + label + '/ORIGINAL_PHYSICAL_REQUEST.json', physical)
                save('measurements/' + label + '/ACTUAL_TURN_START.json', turn)
                text('measurements/' + label + '/TASK.txt', task)
                text('measurements/' + label + '/STEERING.txt', steering)
                row = {'case': label, 'role': role, 'profile': profile,
                    'rendered_text_bytes': len(rendered.encode()), 'task_bytes': len(task.encode()), 'steering_bytes': len(steering.encode()),
                    'provider_output_schema_bytes': len(json.dumps(turn['outputSchema'], separators=(',', ':'), ensure_ascii=False).encode()),
                    'complete_turn_start_bytes': len(json.dumps(turn, separators=(',', ':'), ensure_ascii=False).encode()),
                    'developer_instructions_bytes': len(wire.sent[0][1]['developerInstructions'].encode()),
                    'original_logical_request_bytes': len(json.dumps(logical, separators=(',', ':'), ensure_ascii=False).encode()),
                    'actual_population_capabilities': len(population_names), 'actions': 0, 'observations': 0}
                measurements.append(row)
            finally:
                store.close()
    save('COMPLETE_REQUEST_MEASUREMENTS_004.json', measurements)
    imports = {}
    for name, module in tuple(sys.modules.items()):
        if name.startswith(('gene_annotation_episode', 'method_loop', 'test_')) and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(PIN), (name, str(path))
            imports[name] = str(path.relative_to(PIN))
    verify()
    save('WORKER_RECEIPT_004.json', {'pytest_exit_code': int(code), 'verified_pin_entries': len(manifest),
        'manifest_sha256': fingerprint(PIN / 'PIN_MANIFEST.json')['sha256'], 'verified_imports': imports,
        'scientific_TASK_constants_exact': True, 'actual_contracts': len(examples), 'actual_forms': len(forms),
        'complete_request_cases': len(measurements), 'actual_model_calls': 0,
        'scope': 'Synthetic fixture choices and controlled RPC only; no paper/source science or configured-model execution'})
    print(json.dumps({'passed': True, 'pin_entries': len(manifest), 'actual_contracts': len(examples),
        'actual_forms': len(forms), 'complete_requests': measurements}))


if __name__ == '__main__':
    main()
