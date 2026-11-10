"""Prospective root ownership and intradecision metadata, without live models.

Real sequence derivation, Store, typed forms and method_loop are exercised.
The support entry and controllers are explicit engineering fixtures, not adopted
scientific content, production stopping rules or annotation demonstrations.
"""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import runtime
from gene_annotation_episode.composition_information import (
    ROOT_BOUNDARY_VERSION, child_options, lookup_schema, metadata_catalog)
from gene_annotation_episode.episode_contract_information import validate_saved_fact_form
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController
from test_runtime_decision_exchanges import ConversationProvider
from test_scientific_process_library import independent_source


def zero(*args, **kwargs):
    return 0.


def controller(path, initial):
    return FixtureController(str(path), initial, 2)


def one_action_controller(path, initial):
    return FixtureController(str(path), initial, 1)


def reason_payload(**changes):
    value = {name: [] for name in ('structural_proposals', 'terms', 'source_subjects',
        'observations', 'hypotheses', 'assessments', 'annotation_updates')}
    value.update(changes)
    return value


def select(selection, report=None):
    return {'response': {'response_type': 'select_action',
        'selection': selection, 'report_update': report or {}}}


def lookup(query):
    return {'response': {'response_type': 'request_context', 'lookup': query}}


def table_count(store, name):
    return store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0]


def test_root_rejects_tools_at_schema_dispatch_and_metadata_surface(tmp_path):
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna')['subject_refs']
        tools = ToolRegistry(store)
        workflow = runtime.Workflow(store, tools, object(), tmp_path/'run', 'root-boundary',
            controller, zero, episode_binding_factories=(), decision_protocol='decision_exchange_v1')
        root = workflow.build('annotation', 'root', 'Synthetic root annotation', {'subject_refs': [target]})
        assert workflow.catalog(root.source.scope, source=root.source) == []
        kinds = {choice['properties']['kind']['const'] for choice in
            workflow.action_schema(root.source)['properties']['selection']['anyOf']}
        assert 'tool' not in kinds and {'reason', 'child', 'wait', 'redeliver_report'} <= kinds
        action = {'kind': 'tool', 'tool': 'sequence.translate', 'arguments': {
            'subject_ref': target, 'code': 11, 'start': 0, 'end': 9,
            'strand': '+', 'frame': 0, 'cds': True}}
        with pytest.raises(ValueError, match='action_not_available_to_episode'):
            workflow.selected(root.source, action, 0)
        blocked = asyncio.run(workflow.execute(root.source, action['tool'], action['arguments'],
            decision_index=0, operation_key='blocked'))
        assert blocked['status'] == 'invalid'
        forbidden = asyncio.run(workflow.execute(root.source, 'state.query', {},
            decision_index=0, operation_key='no-hidden-read', _composition_lookup=True))
        assert forbidden['feedback']['code'] == 'composition_operation_not_available'
        invalid_lookup = {'view': 'composition_information', 'operation': 'result.blast.hsp',
            'arguments': {'observation_ref': target, 'column_offset': 0, 'column_limit': 10}}
        assert not Draft202012Validator(lookup_schema(workflow, root.source)).is_valid(invalid_lookup)
        names = {item['name'] for item in metadata_catalog(workflow, root.source)}
        assert 'launch.instructions.search' in names
        assert not any(name.startswith(('public.', 'source.', 'state.', 'result.')) for name in names)
        assert table_count(store, 'runtime_actions') == table_count(store, 'runtime_observations') == 0
        assert 'sequence.translate' in tools.catalog()


def test_combined_root_child_form_comes_from_declared_facts(tmp_path):
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna')['subject_refs']
        workflow = runtime.Workflow(store, ToolRegistry(store), object(), tmp_path/'run',
            'root-form', controller, zero, episode_binding_factories=(),
            decision_protocol='decision_exchange_v1')
        root = workflow.build('annotation', 'root', 'Synthetic root annotation',
            {'subject_refs': [target]})
        sources = ('scientific_process_results', 'committed_record_refs')
        owner = SimpleNamespace(
            required_return_sources=lambda _parent, _role: sources,
            child_assignment_schema=lambda _parent, _role: {'type': 'object',
                'properties': {}, 'required': [], 'additionalProperties': False})
        workflow.project_credit = SimpleNamespace(task_credit=True)
        workflow.annotation_child_roles = ('scientific_process',)
        workflow.episode_bindings = SimpleNamespace(roles={'scientific_process'},
            for_role=lambda _role: owner, entry_roles=('scientific_process',))
        workflow.scientific_process_binding = owner

        choices = workflow.action_schema(root.source)['properties']['selection']['anyOf']
        child = next(choice for choice in choices
            if choice['properties']['kind']['const'] == 'episode_child')
        assert 'schema_json' not in child['properties']
        assert 'initial_report_json' not in child['properties']
        assert {'goal', 'scope', 'purpose', 'role', 'assignment'} <= set(child['required'])

        selected = {'kind': 'episode_child', 'role': 'scientific_process'}
        form_text = workflow.child_form_input(root.source, selected, 'scientific_process')
        assert workflow.child_initial_report_input(root.source, selected, 'scientific_process') == '{}'
        form = json.loads(form_text)
        assert form['type'] == 'object' and form['additionalProperties'] is False
        assert form['required'] == list(sources)
        assert set(form['properties']) == set(sources)
        assert all(form['properties'][name] == {'$ref': 'episode-fact:' + name}
            for name in sources)
        facts = runtime.common_fact_sources()
        facts['scientific_process_results'] = {'type': 'array', 'meaning': 'Axis results',
            'report_schema': {'type': 'array', 'items': {'type': 'string',
                'format': 'reference'}, 'x-source': 'scientific_process_results'}}
        workflow.contract_information_profile = lambda _source: 'operation_contract_information_v1'
        workflow.pending_contract_information = lambda _source, _index: ({}, {
            'fact_sources_by_role': {'scientific_process': facts},
            'permitted_child_roles': ['scientific_process']})
        compiled, declaration = workflow.expanded_contract_form(root.source, selected, 0,
            'scientific_process', original_child=False)
        assert {node['x-source'] for node in compiled['properties'].values()} == set(sources)
        validate_saved_fact_form(child_role='scientific_process', submitted_schema_json=form_text,
            expanded_schema=compiled, declaration=declaration)
        original = '{"type":"object","properties":{},"required":[],"additionalProperties":false}'
        assert workflow.child_form_input(root.source, {**selected, 'schema_json': original},
            'scientific_process') == original


def test_metadata_then_real_child_translation_typed_return_and_root_reason(tmp_path):
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna')['subject_refs']
        tools = ToolRegistry(store)
        source, run_dir = tmp_path/'fixture-source', tmp_path/'run'
        independent_source(source)
        descriptor = prepare_scientific_binding(run_directory=run_dir, source_directory=source,
            tool_catalog=tools.catalog(), child_roles=('scientific_process',))
        library = ScientificProcessLibrary(run_dir/'scientific-process-library')
        scope = {'subject_refs': [target]}
        form = {'type': 'object', 'additionalProperties': False,
            'required': ['products', 'observations'], 'properties': {
                'products': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
                    'x-reference-namespace': 'product'}},
                'observations': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
                    'x-reference-namespace': 'observation'}}}}
        commission = {'kind': 'episode_child', 'role': 'scientific_process',
            'goal': 'Derive the assigned synthetic coding sequence and inspect its molecular mapping',
            'scope': scope, 'purpose': 'Return only the derived protein and mapping observation',
            'schema_json': json.dumps(form), 'initial_report_json': '{"products":[],"observations":[]}',
            'assignment': {'selection': {'version': 'scientific_process_selection_v3',
                'evidence_axis': library.reference('A01'), 'thought_pattern': library.reference('P01'),
                'child_tool_info': [{'name': 'sequence.translate', 'resources': 'local'}]}, 'evidence_refs': [target],
                'constraints': {}, 'context': {}}}
        received = {}

        def before_action(context):
            assert table_count(store, 'runtime_actions') == table_count(store, 'runtime_observations') == 0
            assert context['kind'] == 'decision_lookup_result'
            return lookup({'view': 'composition_information', 'operation': 'launch.instructions.search',
                'arguments': {'query': '', 'offset': 0, 'limit': 1}})

        def commission_after_metadata(context):
            assert table_count(store, 'runtime_actions') == table_count(store, 'runtime_observations') == 0
            assert context['result']['status'] == 'completed'
            return select(commission)

        def child_reports_derived_records(context):
            outcome = context['fields']['last_local_outcome']
            record = outcome['result']['records'][0]
            received.update(products=[record['product_ref']], observations=[record['observation_ref']])
            return select({'kind': 'reason', 'commit': reason_payload(hypotheses=[{
                'alias': 'derived_molecule', 'subject_refs': received['products'],
                'predicate': 'molecule_type', 'value': {'type': 'enum', 'value': 'protein'},
                'context_refs': []}])}, received)

        def parent_interprets(context):
            assert context['fields']['child_reports'] == [received]
            assert {tool['name'] for tool in provider.contexts[0]['fields']['tools']} == {
                'shared.request_information','shared.publish_information','shared.resolve_information_need',
                'shared.read_information','shared.list_information'}
            product = store.get(received['products'][0])
            assert store.get_artifact(product['sequence_ref']) == b'MK'
            return select({'kind': 'reason', 'commit': reason_payload(hypotheses=[{
                'alias': 'translated_molecule', 'subject_refs': received['products'],
                'predicate': 'molecule_type', 'value': {'type': 'enum', 'value': 'protein'},
                'context_refs': []}])})

        provider = ConversationProvider([
            lookup({'view': 'child_options', 'role': 'scientific_process'}), before_action,
            commission_after_metadata,
            select({'kind': 'tool', 'tool': 'sequence.translate', 'arguments': {
                'subject_ref': target, 'code': 11, 'start': 0, 'end': 9,
                'strand': '+', 'frame': 0, 'cds': True}}, {'products': [], 'observations': []}),
            child_reports_derived_records, parent_interprets])
        result = asyncio.run(runtime.run_workflow(store, tools, provider=provider, run_dir=run_dir,
            controller_factory=controller, project_credit=zero,
            episode_binding_descriptors=[descriptor], annotation_child_roles=('scientific_process',),
            episode_record_receipts=True, initial_known_record_refs=[],
            goal='Synthetic root annotation', decision_protocol='decision_exchange_v1'))
        assert result['completed_actions'] == 2
        root_row = store.db.execute('SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=1').fetchone()
        root_actions = [json.loads(row[0]) for row in store.db.execute(
            'SELECT action FROM runtime_actions WHERE episode_id=? ORDER BY decision_index', (root_row[0],))]
        assert [row['kind'] for row in root_actions] == ['episode_child', 'reason']
        assert table_count(store, 'runtime_actions') == table_count(store, 'runtime_observations') == 4
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type='hypothesis'").fetchone()[0] == 1
        saved = json.loads((run_dir/'run.json').read_text())
        assert saved['root_action_boundary'] == ROOT_BOUNDARY_VERSION
        reconstruction = runtime.assemble_workflow(store, tools, object(), run_dir, saved['run_id'], saved,
            controller_factory=controller, project_credit=zero,
            episode_binding_descriptors=saved['episode_bindings'],
            annotation_child_roles=('scientific_process',), episode_record_receipts=True,
            initial_known_record_refs=[])
        restored_root = reconstruction.build('annotation', 'root', saved['goal'], scope)
        assert {tool['name'] for tool in reconstruction.catalog(scope, source=restored_root.source)} == {
            'shared.request_information','shared.publish_information','shared.resolve_information_need',
            'shared.read_information','shared.list_information'}
        with pytest.raises(ValueError, match='action_not_available_to_episode'):
            reconstruction.selected(restored_root.source,
                {'kind': 'tool', 'tool': 'sequence.translate', 'arguments': {}}, 99)
        legacy = deepcopy(saved)
        legacy.pop('root_action_boundary')
        restored_legacy = runtime.assemble_workflow(store, tools, object(), run_dir, saved['run_id'], legacy,
            controller_factory=controller, project_credit=zero,
            episode_binding_descriptors=saved['episode_bindings'],
            annotation_child_roles=('scientific_process',), episode_record_receipts=True,
            initial_known_record_refs=[])
        legacy_root = restored_legacy.build('annotation', 'root', saved['goal'], scope)
        assert 'sequence.translate' in {row['name'] for row in restored_legacy.catalog(scope, source=legacy_root.source)}


def test_parent_can_discover_child_return_facts(tmp_path):
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MK', molecule='protein')['subject_refs']
        tools = ToolRegistry(store)
        factory = ExecutionServiceFactory({'uniprot': {'kind': 'api', 'service': 'uniprot'}}, {}, 1, 1, 1)
        workflow = runtime.Workflow(store, tools, object(), tmp_path/'run', 'child-contracts',
            controller, zero, episode_service_factory=factory,
            episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1',
            annotation_child_roles=('launch', 'monitor', 'results'))
        root = workflow.build('annotation', 'root', 'Synthetic root annotation', {'subject_refs': [target]})
        assert 'execution_handoff_refs' not in workflow.extra_report_sources(root.source)
        details = child_options(workflow, root.source, 'launch')['text']
        assert 'execution_handoff_refs' in details and 'execution_completed' in details
        assert 'assignment.requests.uniprot' in details
        assert table_count(store, 'runtime_actions') == table_count(store, 'runtime_observations') == 0


def test_recovery_reuses_metadata_reply_without_an_action_or_duplicate_lookup(tmp_path, monkeypatch):
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna')['subject_refs']
        tools, run_dir = ToolRegistry(store), tmp_path/'run'
        lookups = []
        original = runtime.child_option_information

        def counted(workflow, source, role=None):
            if role is not None:
                lookups.append(role)
            return original(workflow, source, role)

        monkeypatch.setattr(runtime, 'child_option_information', counted)
        options = dict(run_dir=run_dir, controller_factory=one_action_controller,
            project_credit=zero, episode_binding_factories=(),
            goal='Synthetic recovery', decision_protocol='decision_exchange_v1')
        first = ConversationProvider([lookup({'view': 'child_options', 'role': 'improvement'}),
            RuntimeError('fixture interrupted transport')])
        with pytest.raises(RuntimeError, match='fixture interrupted transport'):
            asyncio.run(runtime.run_workflow(store, tools, provider=first, **options))
        assert lookups == ['improvement']
        assert table_count(store, 'runtime_actions') == table_count(store, 'runtime_observations') == 0

        def restored(context):
            assert context['kind'] == 'decision_bootstrap'
            prior = context['restored_public_exchanges']
            assert prior[0]['lookup_result']['status'] == 'completed'
            assert 'improvement' in prior[0]['lookup_result']['text']
            return select({'kind': 'reason', 'commit': reason_payload(hypotheses=[{
                'alias': 'input_molecule', 'subject_refs': [target], 'predicate': 'molecule_type',
                'value': {'type': 'enum', 'value': 'dna'}, 'context_refs': []}])})

        result = asyncio.run(runtime.run_workflow(store, tools,
            provider=ConversationProvider([restored]), resume=True, **options))
        assert result['completed_actions'] == 1 and lookups == ['improvement']
        assert table_count(store, 'runtime_actions') == table_count(store, 'runtime_observations') == 1
        assert table_count(store, 'runtime_model_calls') == 1
